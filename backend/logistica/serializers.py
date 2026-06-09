from rest_framework import serializers

from logistica.models import (
    Categoria, DetalleFactura, Documento, Marca, OrdenCompra, Producto, Proveedor, Subcategoria,
    UnidadMedida,
)


class ProveedorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Proveedor
        fields = '__all__'


class CategoriaSerializer(serializers.ModelSerializer):
    subcategorias_count = serializers.SerializerMethodField()

    class Meta:
        model = Categoria
        fields = '__all__'

    def get_subcategorias_count(self, obj):
        return obj.subcategorias.filter(activo=True).count()


class SubcategoriaSerializer(serializers.ModelSerializer):
    categoria_nombre = serializers.CharField(source='categoria.nombre', read_only=True)

    class Meta:
        model = Subcategoria
        fields = '__all__'

    def validate(self, data):
        categoria = data.get('categoria') or (self.instance and self.instance.categoria)
        codigo = data.get('codigo') or (self.instance and self.instance.codigo)
        if categoria and codigo:
            qs = Subcategoria.objects.filter(categoria=categoria, codigo=codigo)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError(
                    {'codigo': 'Ya existe esta subcategoría en la categoría seleccionada.'}
                )
        return data


class MarcaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Marca
        fields = '__all__'


class UnidadMedidaSerializer(serializers.ModelSerializer):
    class Meta:
        model = UnidadMedida
        fields = '__all__'


class ProductoSerializer(serializers.ModelSerializer):
    categoria_nombre = serializers.CharField(source='categoria.nombre', read_only=True)
    subcategoria_nombre = serializers.CharField(source='subcategoria.nombre', read_only=True, default=None)
    marca_nombre = serializers.CharField(source='marca.nombre', read_only=True, default=None)
    unidad_codigo = serializers.CharField(source='unidad.codigo', read_only=True, default='UND')
    unidad_medida = serializers.CharField(source='unidad.codigo', read_only=True, default='UND')
    requiere_fecha_vencimiento = serializers.BooleanField(
        source='categoria.requiere_fecha_vencimiento', read_only=True,
    )

    class Meta:
        model = Producto
        fields = '__all__'

    def validate(self, data):
        categoria = data.get('categoria') or (self.instance and self.instance.categoria)
        subcategoria = data.get('subcategoria')
        if subcategoria is None and self.instance and 'subcategoria' not in data:
            subcategoria = self.instance.subcategoria
        if subcategoria and categoria and subcategoria.categoria_id != categoria.id:
            raise serializers.ValidationError(
                {'subcategoria': 'La subcategoría no pertenece a la categoría seleccionada.'}
            )

        if categoria and not self.instance:
            if categoria.subcategorias.filter(activo=True).exists() and not subcategoria:
                raise serializers.ValidationError(
                    {'subcategoria': 'Debe seleccionar una subcategoría para esta categoría.'}
                )

        codigo = data.get('codigo')
        if not self.instance and subcategoria and codigo:
            prefijo = subcategoria.codigo.upper()
            if not codigo.upper().startswith(prefijo):
                raise serializers.ValidationError(
                    {'codigo': f'El código debe iniciar con {prefijo} (código de la subcategoría).'}
                )

        return data

    def create(self, validated_data):
        if not validated_data.get('codigo'):
            subcategoria = validated_data.get('subcategoria')
            categoria = validated_data['categoria']
            prefijo = subcategoria.codigo if subcategoria else categoria.codigo
            validated_data['codigo'] = Producto.obtener_siguiente_codigo(prefijo)
        return super().create(validated_data)


class DocumentoSerializer(serializers.ModelSerializer):
    subido_por_nombre = serializers.CharField(source='subido_por.username', read_only=True)

    class Meta:
        model = Documento
        fields = '__all__'
        read_only_fields = ('subido_por',)


from logistica.permissions import puede_modificar_factura
from logistica.utils.igv import calcular_linea


class DetalleFacturaWriteSerializer(serializers.ModelSerializer):
    """Campos de escritura para ítems de factura (sin id ni totales calculados)."""

    class Meta:
        model = DetalleFactura
        fields = (
            'numero_item', 'producto', 'descripcion', 'laboratorio', 'marca',
            'cantidad', 'unidad_medida', 'precio_unitario', 'igv_incluido',
            'lote', 'fecha_vencimiento',
        )
        extra_kwargs = {
            'producto': {'required': False, 'allow_null': True},
            'numero_item': {'required': False},
            'precio_unitario': {'required': False},
            'igv_incluido': {'required': False},
            'laboratorio': {'required': False},
            'marca': {'required': False},
            'lote': {'required': False},
            'fecha_vencimiento': {'required': False, 'allow_null': True},
        }


class DetalleFacturaSerializer(serializers.ModelSerializer):
    producto_codigo = serializers.CharField(source='producto.codigo', read_only=True, default=None)
    subtotal = serializers.SerializerMethodField()
    igv_monto = serializers.SerializerMethodField()
    importe = serializers.SerializerMethodField()

    class Meta:
        model = DetalleFactura
        fields = (
            'id', 'numero_item', 'producto', 'producto_codigo',
            'descripcion', 'laboratorio', 'marca', 'cantidad', 'unidad_medida',
            'precio_unitario', 'igv_incluido', 'lote', 'fecha_vencimiento',
            'subtotal', 'igv_monto', 'importe',
        )
        extra_kwargs = {
            'producto': {'required': False, 'allow_null': True},
            'precio_unitario': {'required': False},
            'igv_incluido': {'required': False},
            'laboratorio': {'required': False},
            'lote': {'required': False},
            'fecha_vencimiento': {'required': False},
        }

    def _importes(self, obj):
        return calcular_linea(obj.cantidad, obj.precio_unitario, obj.igv_incluido)

    def get_subtotal(self, obj):
        return self._importes(obj)[0]

    def get_igv_monto(self, obj):
        return self._importes(obj)[1]

    def get_importe(self, obj):
        return self._importes(obj)[2]


class OrdenCompraSerializer(serializers.ModelSerializer):
    proveedor_nombre = serializers.CharField(source='proveedor.razon_social', read_only=True)
    proveedor_ruc = serializers.CharField(source='proveedor.ruc', read_only=True)
    registrado_por_nombre = serializers.CharField(source='registrado_por.username', read_only=True)
    numero_completo = serializers.SerializerMethodField()
    detalles = DetalleFacturaSerializer(many=True, read_only=True)
    documentos = DocumentoSerializer(many=True, read_only=True)
    total_items = serializers.SerializerMethodField()
    estado_codigo = serializers.SerializerMethodField()
    subtotal_factura = serializers.SerializerMethodField()
    igv_factura = serializers.SerializerMethodField()
    importe_total_factura = serializers.SerializerMethodField()

    class Meta:
        model = OrdenCompra
        fields = '__all__'
        read_only_fields = (
            'registrado_por', 'numero', 'numero_completo', 'detalles',
            'documentos', 'total_items', 'estado_codigo',
        )

    def get_numero_completo(self, obj):
        return obj.numero_completo

    def get_total_items(self, obj):
        return obj.detalles.count()

    def get_estado_codigo(self, obj):
        return {'pendiente': 'P', 'atendido': 'A', 'rechazado': 'R'}.get(obj.estado, obj.estado)

    def get_subtotal_factura(self, obj):
        return self._totales_factura(obj)[0]

    def get_igv_factura(self, obj):
        return self._totales_factura(obj)[1]

    def get_importe_total_factura(self, obj):
        return self._totales_factura(obj)[2]

    def _totales_factura(self, obj):
        sub = igv = imp = 0
        for d in obj.detalles.all():
            s, i, t = calcular_linea(d.cantidad, d.precio_unitario, d.igv_incluido)
            sub += s
            igv += i
            imp += t
        return sub, igv, imp

    def validate_serie(self, value):
        return value or OrdenCompra.SERIE_DEFAULT


def _producto_id(valor):
    if valor is None or valor == '':
        return None
    if hasattr(valor, 'pk'):
        return valor.pk
    return int(valor)


def _crear_detalles_factura(orden, detalles_data):
    for idx, detalle in enumerate(detalles_data, start=1):
        um = detalle.get('unidad_medida') or 'UND'
        producto_id = _producto_id(detalle.get('producto'))
        if producto_id:
            prod = Producto.objects.filter(pk=producto_id).select_related('unidad').first()
            if prod and prod.unidad:
                um = prod.unidad.codigo
        DetalleFactura.objects.create(
            orden=orden,
            numero_item=detalle.get('numero_item') or idx,
            producto_id=producto_id,
            descripcion=detalle['descripcion'],
            laboratorio=detalle.get('laboratorio', ''),
            marca=detalle.get('marca', ''),
            cantidad=detalle['cantidad'],
            unidad_medida=um,
            precio_unitario=detalle.get('precio_unitario') or 0,
            igv_incluido=bool(detalle.get('igv_incluido', False)),
            lote=detalle.get('lote', ''),
            fecha_vencimiento=detalle.get('fecha_vencimiento'),
        )


class _OrdenCompraConDetallesMixin:
    def validate_detalles(self, value):
        if not value:
            raise serializers.ValidationError('Debe registrar al menos un ítem en la factura.')
        return value

    def validate_serie(self, value):
        return (value or OrdenCompra.SERIE_DEFAULT).strip()


class OrdenCompraCreateSerializer(_OrdenCompraConDetallesMixin, serializers.ModelSerializer):
    detalles = DetalleFacturaWriteSerializer(many=True)

    class Meta:
        model = OrdenCompra
        fields = (
            'serie', 'numero', 'proveedor', 'fecha_orden', 'fecha_esperada',
            'observaciones', 'detalles',
        )

    def validate(self, data):
        serie = (data.get('serie') or OrdenCompra.SERIE_DEFAULT).strip()
        numero = data.get('numero')
        if numero is None:
            raise serializers.ValidationError({'numero': 'Ingrese el número de la factura.'})
        if OrdenCompra.objects.filter(serie=serie, numero=numero).exists():
            raise serializers.ValidationError(
                {'numero': f'Ya existe la factura {serie}-{int(numero):06d}.'}
            )
        data['serie'] = serie
        return data

    def create(self, validated_data):
        detalles_data = validated_data.pop('detalles')
        request = self.context['request']
        orden = OrdenCompra.objects.create(
            registrado_por=request.user,
            **validated_data,
        )
        _crear_detalles_factura(orden, detalles_data)
        from notificaciones.flujos import notificar_factura_registrada
        notificar_factura_registrada(orden, actor=request.user)
        return orden


class OrdenCompraUpdateSerializer(_OrdenCompraConDetallesMixin, serializers.ModelSerializer):
    detalles = DetalleFacturaWriteSerializer(many=True)

    class Meta:
        model = OrdenCompra
        fields = (
            'serie', 'numero', 'proveedor', 'fecha_orden', 'fecha_esperada',
            'observaciones', 'detalles',
        )

    def validate(self, data):
        serie = (data.get('serie') or self.instance.serie or OrdenCompra.SERIE_DEFAULT).strip()
        numero = data.get('numero', self.instance.numero)
        if numero is None:
            raise serializers.ValidationError({'numero': 'Ingrese el número de la factura.'})
        qs = OrdenCompra.objects.filter(serie=serie, numero=numero)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                {'numero': f'Ya existe la factura {serie}-{int(numero):06d}.'}
            )
        data['serie'] = serie
        return data

    def update(self, instance, validated_data):
        request = self.context.get('request')
        ok, msg = puede_modificar_factura(request.user if request else None, instance)
        if not ok:
            raise serializers.ValidationError({'detail': msg})

        detalles_data = validated_data.pop('detalles')
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        instance.detalles.all().delete()
        _crear_detalles_factura(instance, detalles_data)
        return instance
