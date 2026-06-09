from django.db import transaction
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from logistica.models import (
    Categoria, DetalleFactura, Documento, Marca, OrdenCompra, Producto, Proveedor, Subcategoria,
    UnidadMedida,
)
from logistica.serializers import (
    CategoriaSerializer,
    DetalleFacturaSerializer,
    DocumentoSerializer,
    MarcaSerializer,
    OrdenCompraCreateSerializer,
    OrdenCompraSerializer,
    OrdenCompraUpdateSerializer,
    ProductoSerializer,
    ProveedorSerializer,
    SubcategoriaSerializer,
    UnidadMedidaSerializer,
)
from logistica.permissions import (
    puede_control_calidad,
    puede_modificar_factura,
    puede_registrar_factura,
    puede_validar_documentacion,
)
from logistica.services.sunat import consultar_ruc_sunat
from seguridad.actores import puede_gestionar_maestros_compras


def _exigir_gestion_maestros(user):
    if not puede_gestionar_maestros_compras(user):
        raise PermissionDenied('Solo el jefe de compras puede gestionar catálogos y proveedores.')


class MaestrosComprasMixin:
    """Escritura restringida a jefe de compras (matriz de actores)."""

    def create(self, request, *args, **kwargs):
        try:
            _exigir_gestion_maestros(request.user)
        except PermissionDenied as exc:
            return Response({'detail': str(exc.detail)}, status=403)
        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        try:
            _exigir_gestion_maestros(request.user)
        except PermissionDenied as exc:
            return Response({'detail': str(exc.detail)}, status=403)
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        try:
            _exigir_gestion_maestros(request.user)
        except PermissionDenied as exc:
            return Response({'detail': str(exc.detail)}, status=403)
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        try:
            _exigir_gestion_maestros(request.user)
        except PermissionDenied as exc:
            return Response({'detail': str(exc.detail)}, status=403)
        return super().destroy(request, *args, **kwargs)


class ProveedorViewSet(MaestrosComprasMixin, viewsets.ModelViewSet):
    queryset = Proveedor.objects.filter(activo=True)
    serializer_class = ProveedorSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'], url_path='consultar-ruc')
    def consultar_ruc(self, request):
        """Consulta datos del RUC en SUNAT vía Decolecta."""
        ruc = request.query_params.get('ruc', '')
        datos = consultar_ruc_sunat(ruc)
        existente = Proveedor.objects.filter(ruc=datos['ruc']).first()
        return Response({
            **datos,
            'ya_registrado': existente is not None,
            'proveedor_id': existente.id if existente else None,
        })

    @action(detail=False, methods=['post'], url_path='desde-sunat')
    def desde_sunat(self, request):
        """Consulta SUNAT y crea o actualiza el proveedor."""
        try:
            _exigir_gestion_maestros(request.user)
        except PermissionDenied as exc:
            return Response({'detail': str(exc.detail)}, status=403)
        ruc = request.data.get('ruc', '')
        datos = consultar_ruc_sunat(ruc)
        proveedor, creado = Proveedor.objects.update_or_create(
            ruc=datos['ruc'],
            defaults={
                'razon_social': datos['razon_social'],
                'direccion': datos['direccion'],
                'telefono': request.data.get('telefono', ''),
                'email': request.data.get('email', ''),
                'contacto': request.data.get('contacto', ''),
                'activo': True,
            },
        )
        return Response(
            {
                'creado': creado,
                'proveedor': ProveedorSerializer(proveedor).data,
                'sunat': {
                    'estado': datos['estado_sunat'],
                    'condicion': datos['condicion_sunat'],
                },
            },
            status=status.HTTP_201_CREATED if creado else status.HTTP_200_OK,
        )

class CategoriaViewSet(MaestrosComprasMixin, viewsets.ModelViewSet):
    queryset = Categoria.objects.filter(activo=True)
    serializer_class = CategoriaSerializer
    permission_classes = [IsAuthenticated]


class SubcategoriaViewSet(MaestrosComprasMixin, viewsets.ModelViewSet):
    queryset = Subcategoria.objects.filter(activo=True).select_related('categoria')
    serializer_class = SubcategoriaSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        categoria_id = self.request.query_params.get('categoria')
        if categoria_id:
            qs = qs.filter(categoria_id=categoria_id)
        return qs.order_by('categoria__nombre', 'nombre')


class ProductoViewSet(MaestrosComprasMixin, viewsets.ModelViewSet):
    queryset = Producto.objects.filter(activo=True).select_related(
        'categoria', 'subcategoria', 'marca', 'unidad',
    )
    serializer_class = ProductoSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'], url_path='siguiente-codigo')
    def siguiente_codigo(self, request):
        """Correlativo por subcategoría (ej. ANALG000001) o categoría si no hay subcategoría."""
        subcategoria_id = request.query_params.get('subcategoria')
        categoria_id = request.query_params.get('categoria')
        if subcategoria_id:
            sub = Subcategoria.objects.select_related('categoria').get(pk=subcategoria_id, activo=True)
            prefijo = sub.codigo.upper()
        elif categoria_id:
            cat = Categoria.objects.get(pk=categoria_id, activo=True)
            prefijo = cat.codigo.upper()
        else:
            return Response({'detail': 'Indique subcategoría o categoría.'}, status=400)
        codigo = Producto.obtener_siguiente_codigo(prefijo)
        return Response({
            'prefijo': prefijo,
            'codigo': codigo,
            'numero': int(codigo[len(prefijo):]),
        })


class MarcaViewSet(MaestrosComprasMixin, viewsets.ModelViewSet):
    queryset = Marca.objects.filter(activo=True)
    serializer_class = MarcaSerializer
    permission_classes = [IsAuthenticated]


class UnidadMedidaViewSet(MaestrosComprasMixin, viewsets.ModelViewSet):
    queryset = UnidadMedida.objects.filter(activo=True)
    serializer_class = UnidadMedidaSerializer
    permission_classes = [IsAuthenticated]


class OrdenCompraViewSet(viewsets.ModelViewSet):
    queryset = OrdenCompra.objects.all()
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = OrdenCompra.objects.select_related(
            'proveedor', 'registrado_por', 'control_calidad_por'
        ).prefetch_related('detalles', 'detalles__producto', 'documentos').order_by('-serie', '-numero')
        estado = self.request.query_params.get('estado')
        if estado:
            qs = qs.filter(estado=estado)
        control = self.request.query_params.get('control_calidad')
        if control == 'pendiente':
            qs = qs.filter(estado=OrdenCompra.Estado.ATENDIDO, control_calidad_estado=OrdenCompra.EstadoCalidad.PENDIENTE)
        return qs

    def create(self, request, *args, **kwargs):
        if not puede_registrar_factura(request.user):
            return Response(
                {'detail': 'Solo el jefe de compras puede registrar facturas.'},
                status=403,
            )
        return super().create(request, *args, **kwargs)

    def get_serializer_class(self):
        if self.action == 'create':
            return OrdenCompraCreateSerializer
        if self.action in ('update', 'partial_update'):
            return OrdenCompraUpdateSerializer
        return OrdenCompraSerializer

    def destroy(self, request, *args, **kwargs):
        orden = self.get_object()
        ok, msg = puede_modificar_factura(request.user, orden)
        if not ok:
            return Response({'detail': msg}, status=403)
        return super().destroy(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        orden = self.get_object()
        ok, msg = puede_modificar_factura(request.user, orden)
        if not ok:
            return Response({'detail': msg}, status=403)
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        orden = self.get_object()
        ok, msg = puede_modificar_factura(request.user, orden)
        if not ok:
            return Response({'detail': msg}, status=403)
        return super().partial_update(request, *args, **kwargs)

    @action(detail=False, methods=['get'], url_path='siguiente-numero')
    def siguiente_numero(self, request):
        from django.conf import settings
        serie = request.query_params.get(
            'serie',
            getattr(settings, 'ORDEN_COMPRA_SERIE_DEFAULT', OrdenCompra.SERIE_DEFAULT),
        )
        numero = OrdenCompra.obtener_siguiente_numero(serie)
        return Response({
            'serie': serie,
            'numero': numero,
            'numero_completo': f'{serie}-{numero:06d}',
        })

    @action(detail=True, methods=['post'], url_path='validar-documentacion')
    def validar_documentacion(self, request, pk=None):
        """UC 01 / FEAT 02 — Jefe de almacén valida documentación P → A."""
        if not puede_validar_documentacion(request.user):
            return Response(
                {'detail': 'Solo el jefe de almacén puede validar documentación.'},
                status=403,
            )
        orden = self.get_object()
        if orden.estado != OrdenCompra.Estado.PENDIENTE:
            return Response({'detail': 'Solo órdenes pendientes (P) pueden validarse.'}, status=400)
        orden.comentarios_validacion = request.data.get('comentarios_validacion', '')
        orden.estado = OrdenCompra.Estado.ATENDIDO
        orden.aprobado_por = request.user
        orden.fecha_aprobacion = timezone.now()
        orden.save()
        from notificaciones.flujos import notificar_documentacion_aprobada
        notificar_documentacion_aprobada(orden, actor=request.user)
        return Response(OrdenCompraSerializer(orden).data)

    @action(detail=True, methods=['post'], url_path='control-calidad')
    def control_calidad(self, request, pk=None):
        """UC 02 / FEAT 04 — Encargado de calidad finaliza control por ítems."""
        if not puede_control_calidad(request.user):
            return Response(
                {'detail': 'Solo control de calidad puede finalizar la inspección.'},
                status=403,
            )
        orden = self.get_object()
        if orden.estado != OrdenCompra.Estado.ATENDIDO:
            return Response({'detail': 'Solo facturas atendidas (A) pueden recibir control de calidad.'}, status=400)
        if orden.control_calidad_estado != OrdenCompra.EstadoCalidad.PENDIENTE:
            return Response({'detail': 'El control de calidad de esta factura ya fue registrado.'}, status=400)

        items = request.data.get('items')
        if items is not None:
            return self._control_calidad_por_items(orden, request.user, items)

        sin_rechazos = request.data.get('sin_productos_rechazados', False)
        if sin_rechazos:
            orden.control_calidad_estado = OrdenCompra.EstadoCalidad.CONFORME
        else:
            rechazos = orden.incidencias_calidad.filter(estado__in=['abierta', 'en_seguimiento']).count()
            orden.control_calidad_estado = (
                OrdenCompra.EstadoCalidad.CONFORME if rechazos == 0
                else OrdenCompra.EstadoCalidad.CON_RECHAZOS
            )
        orden.control_calidad_por = request.user
        orden.fecha_control_calidad = timezone.now()
        orden.save()

        from inventario.services.recepcion import registrar_entrada_desde_factura
        inv_result = registrar_entrada_desde_factura(orden, request.user, items=None)

        from notificaciones.flujos import notificar_control_calidad_finalizado
        rechazos = 0 if sin_rechazos else orden.incidencias_calidad.count()
        notificar_control_calidad_finalizado(orden, rechazos, actor=request.user)

        data = OrdenCompraSerializer(orden).data
        data['inventario_entradas'] = inv_result
        return Response(data)

    def _control_calidad_por_items(self, orden, user, items):
        from calidad.models import IncidenciaCalidad
        from decimal import Decimal, InvalidOperation
        from inventario.services.recepcion import registrar_entrada_desde_factura

        if not isinstance(items, list) or not items:
            return Response({'detail': 'Indique el resultado de cada ítem.'}, status=400)

        detalles = {d.id: d for d in orden.detalles.all()}
        if len(items) != len(detalles):
            return Response(
                {'detail': 'Debe evaluar todos los ítems de la factura.'},
                status=400,
            )

        with transaction.atomic():
            incidencias_creadas = []
            rechazos = 0
            vistos = set()
            for item in items:
                det_id = item.get('detalle_factura')
                if det_id in vistos:
                    return Response({'detail': f'Ítem {det_id} duplicado.'}, status=400)
                vistos.add(det_id)
                det = detalles.get(det_id)
                if not det:
                    return Response({'detail': f'Ítem {det_id} no pertenece a la factura.'}, status=400)

                estado = item.get('estado', 'conforme')
                if estado not in ('conforme', 'rechazado'):
                    return Response({'detail': 'Estado inválido. Use conforme o rechazado.'}, status=400)

                if estado == 'rechazado':
                    motivo = (item.get('motivo') or '').strip()
                    if not motivo:
                        return Response(
                            {'detail': f'Indique motivo para el ítem #{det.numero_item} ({det.descripcion}).'},
                            status=400,
                        )
                    try:
                        cant = item.get('cantidad_rechazada')
                        cant = Decimal(str(cant if cant not in (None, '') else det.cantidad))
                    except (InvalidOperation, TypeError):
                        return Response({'detail': f'Cantidad rechazada inválida en ítem #{det.numero_item}.'}, status=400)
                    if cant <= 0 or cant > det.cantidad:
                        return Response(
                            {'detail': f'Cantidad rechazada fuera de rango en ítem #{det.numero_item}.'},
                            status=400,
                        )
                    inc = IncidenciaCalidad.objects.create(
                        orden=orden,
                        detalle_factura=det,
                        producto=det.producto,
                        cantidad_rechazada=cant,
                        motivo=motivo,
                        comentarios=item.get('comentarios', ''),
                        registrado_por=user,
                    )
                    incidencias_creadas.append({'id': inc.id, 'detalle_factura': det.id})
                    rechazos += 1

            orden.control_calidad_estado = (
                OrdenCompra.EstadoCalidad.CONFORME if rechazos == 0
                else OrdenCompra.EstadoCalidad.CON_RECHAZOS
            )
            orden.control_calidad_por = user
            orden.fecha_control_calidad = timezone.now()
            orden.save()

            inv_result = registrar_entrada_desde_factura(orden, user, items)

            from notificaciones.flujos import notificar_control_calidad_finalizado
            notificar_control_calidad_finalizado(orden, rechazos, actor=user)

        data = OrdenCompraSerializer(orden).data
        data['incidencias_creadas'] = incidencias_creadas
        data['inventario_entradas'] = inv_result
        return Response(data)

    @action(detail=True, methods=['post'])
    def aprobar(self, request, pk=None):
        return self.validar_documentacion(request, pk)

    @action(detail=True, methods=['post'])
    def rechazar(self, request, pk=None):
        if not puede_validar_documentacion(request.user):
            return Response(
                {'detail': 'Solo el jefe de almacén puede rechazar documentación.'},
                status=403,
            )
        orden = self.get_object()
        if orden.estado != OrdenCompra.Estado.PENDIENTE:
            return Response(
                {'detail': 'Solo facturas pendientes (P) pueden rechazarse.'},
                status=400,
            )
        orden.estado = OrdenCompra.Estado.RECHAZADO
        orden.motivo_rechazo = request.data.get('motivo_rechazo', '')
        orden.save()
        from notificaciones.flujos import notificar_documentacion_rechazada
        notificar_documentacion_rechazada(orden, actor=request.user)
        return Response(OrdenCompraSerializer(orden).data)


class DetalleFacturaViewSet(viewsets.ModelViewSet):
    queryset = DetalleFactura.objects.all()
    serializer_class = DetalleFacturaSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = DetalleFactura.objects.select_related('orden', 'producto').order_by('orden', 'numero_item')
        orden_id = self.request.query_params.get('orden')
        if orden_id:
            qs = qs.filter(orden_id=orden_id)
        return qs

    def _exigir_factura_editable(self, orden):
        ok, msg = puede_modificar_factura(self.request.user, orden)
        if not ok:
            raise PermissionDenied(msg)

    def perform_create(self, serializer):
        self._exigir_factura_editable(serializer.validated_data['orden'])
        serializer.save()

    def perform_update(self, serializer):
        self._exigir_factura_editable(serializer.instance.orden)
        serializer.save()

    def perform_destroy(self, instance):
        self._exigir_factura_editable(instance.orden)
        instance.delete()


class DocumentoViewSet(viewsets.ModelViewSet):
    queryset = Documento.objects.select_related('orden')
    serializer_class = DocumentoSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        self._exigir_factura_editable_doc(serializer.validated_data['orden'])
        serializer.save(subido_por=self.request.user)

    def perform_update(self, serializer):
        self._exigir_factura_editable_doc(serializer.instance.orden)
        serializer.save()

    def perform_destroy(self, instance):
        self._exigir_factura_editable_doc(instance.orden)
        instance.delete()

    def _exigir_factura_editable_doc(self, orden):
        ok, msg = puede_modificar_factura(self.request.user, orden)
        if not ok:
            raise PermissionDenied(msg)
