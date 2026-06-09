from django.utils import timezone
from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from inventario.models import Inventario, MovimientoInventario
from inventario.permissions import puede_cuadre_fisico, puede_movimiento_inventario
from logistica.models import Proveedor
from logistica.services.sunat import consultar_dni_reniec, consultar_ruc_sunat
from seguridad.actores import puede_modificar_inventario, puede_ver_inventario


class InventarioSerializer(serializers.ModelSerializer):
    producto_codigo = serializers.CharField(source='producto.codigo', read_only=True)
    producto_nombre = serializers.CharField(source='producto.nombre', read_only=True)
    stock_minimo = serializers.DecimalField(
        source='producto.stock_minimo', read_only=True, max_digits=12, decimal_places=2,
    )
    diferencia_cuadre = serializers.SerializerMethodField()

    class Meta:
        model = Inventario
        fields = '__all__'
        read_only_fields = (
            'cuadre_estado', 'cuadre_actualizado_en', 'cuadre_por', 'diferencia_cuadre',
        )

    def get_diferencia_cuadre(self, obj):
        if obj.cantidad_fisica is None:
            return None
        return obj.cantidad_fisica - obj.cantidad


class MovimientoInventarioSerializer(serializers.ModelSerializer):
    producto_codigo = serializers.CharField(source='inventario.producto.codigo', read_only=True)
    producto_nombre = serializers.CharField(source='inventario.producto.nombre', read_only=True)
    producto_laboratorio = serializers.CharField(source='inventario.producto.laboratorio', read_only=True)
    producto_categoria = serializers.CharField(source='inventario.producto.categoria.nombre', read_only=True)
    producto_marca = serializers.SerializerMethodField()
    inventario_lote = serializers.CharField(source='inventario.lote', read_only=True)
    inventario_vencimiento = serializers.DateField(source='inventario.fecha_vencimiento', read_only=True)
    inventario_ubicacion = serializers.CharField(source='inventario.ubicacion', read_only=True)
    unidad_medida = serializers.CharField(source='inventario.producto.unidad_medida', read_only=True)
    registrado_por_nombre = serializers.SerializerMethodField()

    class Meta:
        model = MovimientoInventario
        fields = '__all__'
        read_only_fields = ('registrado_por', 'stock_anterior', 'stock_posterior', 'codigo')

    def get_registrado_por_nombre(self, obj):
        u = obj.registrado_por
        if not u:
            return ''
        return u.get_full_name() or u.username

    def get_producto_marca(self, obj):
        marca = obj.inventario.producto.marca
        return marca.nombre if marca else ''


class InventarioViewSet(viewsets.ModelViewSet):
    queryset = Inventario.objects.select_related('producto', 'cuadre_por').order_by('producto__nombre')
    serializer_class = InventarioSerializer
    permission_classes = [IsAuthenticated]

    def list(self, request, *args, **kwargs):
        if not puede_ver_inventario(request.user):
            return Response({'detail': 'No tiene permiso para consultar inventario.'}, status=403)
        return super().list(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        if not puede_ver_inventario(request.user):
            return Response({'detail': 'No tiene permiso para consultar inventario.'}, status=403)
        return super().retrieve(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        if not puede_modificar_inventario(request.user):
            return Response({'detail': 'No tiene permiso para registrar inventario.'}, status=403)
        return super().create(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        if not puede_modificar_inventario(request.user):
            return Response({'detail': 'No tiene permiso para eliminar registros de inventario.'}, status=403)
        return super().destroy(request, *args, **kwargs)

    def _aplicar_cuadre(self, inv, user, estado_anterior):
        inv.cuadre_estado = inv.evaluar_cuadre()
        inv.cuadre_actualizado_en = timezone.now()
        inv.cuadre_por = user
        inv.save(update_fields=['cuadre_estado', 'cuadre_actualizado_en', 'cuadre_por'])
        if (
            inv.cuadre_estado == Inventario.CuadreEstado.DISCREPANCIA
            and estado_anterior != Inventario.CuadreEstado.DISCREPANCIA
        ):
            from notificaciones.flujos import notificar_discrepancia_inventario
            notificar_discrepancia_inventario(inv, actor=user)

    def perform_create(self, serializer):
        inv = serializer.save()
        clasificacion_anterior = inv.clasificacion
        inv.clasificacion = inv.calcular_clasificacion()
        inv.save(update_fields=['clasificacion'])
        from notificaciones.flujos import alertar_inventario_actualizado
        alertar_inventario_actualizado(inv, clasificacion_anterior=clasificacion_anterior)

    def perform_update(self, serializer):
        if not puede_modificar_inventario(self.request.user):
            raise PermissionDenied('No tiene permiso para modificar registros de inventario.')
        if 'cantidad_fisica' in serializer.validated_data and not puede_cuadre_fisico(self.request.user):
            raise PermissionDenied('No tiene permiso para registrar el cuadre físico.')
        clasificacion_anterior = serializer.instance.clasificacion
        cuadre_anterior = serializer.instance.cuadre_estado
        cantidad_fisica_anterior = serializer.instance.cantidad_fisica
        inv = serializer.save()
        inv.clasificacion = inv.calcular_clasificacion()
        update_fields = ['clasificacion']
        if 'cantidad_fisica' in serializer.validated_data:
            inv.cuadre_estado = inv.evaluar_cuadre()
            inv.cuadre_actualizado_en = timezone.now()
            inv.cuadre_por = self.request.user
            update_fields += ['cuadre_estado', 'cuadre_actualizado_en', 'cuadre_por']
        inv.save(update_fields=update_fields)
        if 'cantidad_fisica' in serializer.validated_data:
            fisica_cambio = cantidad_fisica_anterior != inv.cantidad_fisica
            nueva_discrepancia = (
                inv.cuadre_estado == Inventario.CuadreEstado.DISCREPANCIA
                and cuadre_anterior != Inventario.CuadreEstado.DISCREPANCIA
            )
            if inv.cuadre_estado == Inventario.CuadreEstado.DISCREPANCIA and (nueva_discrepancia or fisica_cambio):
                from notificaciones.flujos import notificar_discrepancia_inventario
                notificar_discrepancia_inventario(inv, actor=self.request.user)
        from notificaciones.flujos import alertar_inventario_actualizado
        alertar_inventario_actualizado(inv, clasificacion_anterior=clasificacion_anterior)


class MovimientoInventarioViewSet(viewsets.ModelViewSet):
    queryset = MovimientoInventario.objects.select_related(
        'inventario',
        'inventario__producto',
        'inventario__producto__categoria',
        'inventario__producto__marca',
        'inventario__producto__unidad',
        'registrado_por',
    ).order_by('-creado_en')
    serializer_class = MovimientoInventarioSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'post', 'head', 'options']

    def list(self, request, *args, **kwargs):
        if not puede_ver_inventario(request.user):
            return Response({'detail': 'No tiene permiso para consultar movimientos.'}, status=403)
        return super().list(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        if not puede_movimiento_inventario(request.user):
            return Response(
                {'detail': 'No tiene permiso para registrar movimientos de inventario.'},
                status=403,
            )
        return super().create(request, *args, **kwargs)

    @action(detail=False, methods=['get'], url_path='consultar-tercero')
    def consultar_tercero(self, request):
        """Busca razón social (RUC) o nombres (DNI) del cliente para salidas."""
        import re

        if not puede_movimiento_inventario(request.user):
            return Response({'detail': 'No tiene permiso para consultar terceros.'}, status=403)

        documento = re.sub(r'\D', '', request.query_params.get('documento', ''))
        if not documento:
            return Response({'detail': 'Indique el documento del cliente.'}, status=400)

        if len(documento) == 11:
            proveedor = Proveedor.objects.filter(ruc=documento, activo=True).first()
            if proveedor:
                return Response({
                    'documento': proveedor.ruc,
                    'nombre': proveedor.razon_social,
                    'tipo_documento': 'ruc',
                    'fuente': 'proveedor_local',
                })
            try:
                datos = consultar_ruc_sunat(documento)
            except ValidationError as exc:
                return Response(exc.detail, status=400)
            return Response({
                'documento': datos['ruc'],
                'nombre': datos['razon_social'],
                'tipo_documento': 'ruc',
                'fuente': 'sunat',
            })

        if len(documento) == 8:
            try:
                datos = consultar_dni_reniec(documento)
                return Response({
                    'documento': datos['dni'],
                    'nombre': datos['nombre_completo'],
                    'tipo_documento': 'dni',
                    'fuente': 'reniec',
                })
            except ValidationError:
                pass

        movimiento = (
            MovimientoInventario.objects.filter(
                tercero_tipo=MovimientoInventario.TerceroTipo.CLIENTE,
                tercero_documento=documento,
            )
            .exclude(tercero_nombre='')
            .order_by('-creado_en')
            .first()
        )
        if movimiento:
            return Response({
                'documento': movimiento.tercero_documento,
                'nombre': movimiento.tercero_nombre,
                'tipo_documento': 'historial',
                'fuente': 'movimiento_previo',
            })

        return Response(
            {'detail': 'No se encontró información para este documento. Ingrese el nombre manualmente.'},
            status=404,
        )

    def perform_create(self, serializer):
        inv = serializer.validated_data['inventario']
        cantidad = serializer.validated_data['cantidad']
        tipo = serializer.validated_data['tipo']
        stock_anterior = inv.cantidad
        clasificacion_anterior = inv.clasificacion

        if tipo == 'salida':
            stock_posterior = stock_anterior - cantidad
        else:
            stock_posterior = stock_anterior + cantidad

        inv.cantidad = stock_posterior
        inv.cuadre_estado = Inventario.CuadreEstado.PENDIENTE
        inv.clasificacion = inv.calcular_clasificacion()
        inv.save(update_fields=['cantidad', 'clasificacion', 'cuadre_estado'])

        from notificaciones.flujos import alertar_inventario_actualizado
        alertar_inventario_actualizado(inv, clasificacion_anterior=clasificacion_anterior)

        movimiento = serializer.save(
            registrado_por=self.request.user,
            stock_anterior=stock_anterior,
            stock_posterior=stock_posterior,
            codigo=MovimientoInventario.generar_codigo(tipo),
        )
        from notificaciones.flujos import notificar_movimiento_inventario
        notificar_movimiento_inventario(movimiento, actor=self.request.user)
