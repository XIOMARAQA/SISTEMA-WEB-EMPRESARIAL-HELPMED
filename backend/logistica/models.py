from django.conf import settings
from django.db import models


class Proveedor(models.Model):
    """Tabla: proveedores"""

    ruc = models.CharField(max_length=11, unique=True)
    razon_social = models.CharField(max_length=200)
    direccion = models.TextField(blank=True)
    telefono = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    contacto = models.CharField(max_length=100, blank=True)
    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'proveedores'

    def __str__(self):
        return self.razon_social


class Categoria(models.Model):
    """Tabla: categorias — Datos maestros"""

    codigo = models.CharField(max_length=30, unique=True)
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True)
    requiere_fecha_vencimiento = models.BooleanField(
        default=False,
        help_text='Si es True, los productos de esta categoría deben registrar fecha de vencimiento.',
    )
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = 'categorias'
        verbose_name_plural = 'Categorías de producto'

    def __str__(self):
        return self.nombre


class Subcategoria(models.Model):
    """Tabla: subcategorias — hijas de una categoría padre."""

    categoria = models.ForeignKey(Categoria, on_delete=models.PROTECT, related_name='subcategorias')
    codigo = models.CharField(max_length=30)
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True)
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = 'subcategorias'
        verbose_name = 'Subcategoría'
        verbose_name_plural = 'Subcategorías'
        constraints = [
            models.UniqueConstraint(fields=['categoria', 'codigo'], name='uq_subcategoria_categoria_codigo'),
        ]

    def __str__(self):
        return f'{self.categoria.nombre} › {self.nombre}'


class Marca(models.Model):
    """Tabla: marcas — Datos maestros"""

    codigo = models.CharField(max_length=30, unique=True)
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True)
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = 'marcas'

    def __str__(self):
        return self.nombre


class UnidadMedida(models.Model):
    """Tabla: unidades_medida — Datos maestros"""

    codigo = models.CharField(max_length=10, unique=True)
    nombre = models.CharField(max_length=50)
    simbolo = models.CharField(max_length=10, blank=True)
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = 'unidades_medida'
        verbose_name = 'Unidad de medida'
        verbose_name_plural = 'Unidades de medida'

    def __str__(self):
        return f'{self.codigo} — {self.nombre}'


class Producto(models.Model):
    """Tabla: productos — Datos maestros (productos y servicios)"""

    class Tipo(models.TextChoices):
        PRODUCTO = 'producto', 'Producto'
        SERVICIO = 'servicio', 'Servicio'

    codigo = models.CharField(max_length=50, unique=True)
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)
    tipo = models.CharField(max_length=20, choices=Tipo.choices, default=Tipo.PRODUCTO)
    categoria = models.ForeignKey(Categoria, on_delete=models.PROTECT, related_name='productos')
    subcategoria = models.ForeignKey(
        'Subcategoria', on_delete=models.SET_NULL, null=True, blank=True, related_name='productos',
    )
    marca = models.ForeignKey(Marca, on_delete=models.SET_NULL, null=True, blank=True, related_name='productos')
    unidad = models.ForeignKey(
        UnidadMedida, on_delete=models.PROTECT, null=True, blank=True, related_name='productos'
    )
    stock_minimo = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    stock_maximo = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    requiere_cadena_frio = models.BooleanField(default=False)
    laboratorio = models.CharField(max_length=150, blank=True)
    fecha_vencimiento = models.DateField(
        null=True, blank=True,
        help_text='Obligatoria cuando la categoría exige control de vencimiento (ej. medicinas).',
    )
    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'productos'

    def __str__(self):
        return f'{self.codigo} - {self.nombre}'

    @property
    def unidad_medida(self):
        return self.unidad.codigo if self.unidad_id else 'UND'

    @classmethod
    def obtener_siguiente_codigo(cls, prefijo):
        """Genera código correlativo: PREFIJO + 6 dígitos (ej. ANALG000001)."""
        prefijo = (prefijo or '').upper()
        max_num = 0
        for codigo in cls.objects.filter(codigo__startswith=prefijo).values_list('codigo', flat=True):
            suffix = codigo[len(prefijo):]
            if suffix.isdigit():
                max_num = max(max_num, int(suffix))
        return f'{prefijo}{max_num + 1:06d}'


class OrdenCompra(models.Model):
    """Tabla: ordenes_compra — serie + número correlativo."""

    class Estado(models.TextChoices):
        PENDIENTE = 'pendiente', 'Pendiente'
        ATENDIDO = 'atendido', 'Atendido'
        RECHAZADO = 'rechazado', 'Rechazado'

    SERIE_DEFAULT = '2026'

    serie = models.CharField(max_length=10, default=SERIE_DEFAULT)
    numero = models.PositiveIntegerField(verbose_name='Número correlativo')
    proveedor = models.ForeignKey(Proveedor, on_delete=models.PROTECT, related_name='ordenes')
    fecha_orden = models.DateField()
    fecha_esperada = models.DateField(null=True, blank=True)
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.PENDIENTE)
    observaciones = models.TextField(blank=True)
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='ordenes_registradas'
    )
    aprobado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ordenes_aprobadas',
    )
    fecha_aprobacion = models.DateTimeField(null=True, blank=True)
    motivo_rechazo = models.TextField(blank=True)
    comentarios_validacion = models.TextField(
        blank=True, verbose_name='Comentarios validación documental (FEAT 02)'
    )

    class EstadoCalidad(models.TextChoices):
        PENDIENTE = 'pendiente', 'Pendiente control calidad'
        CONFORME = 'conforme', 'Conforme — sin rechazos'
        CON_RECHAZOS = 'con_rechazos', 'Con productos rechazados'

    control_calidad_estado = models.CharField(
        max_length=20, choices=EstadoCalidad.choices, default=EstadoCalidad.PENDIENTE
    )
    control_calidad_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='controles_calidad_realizados',
    )
    fecha_control_calidad = models.DateTimeField(null=True, blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ordenes_compra'
        unique_together = ('serie', 'numero')
        ordering = ['-serie', '-numero']

    def __str__(self):
        return self.numero_completo

    @property
    def numero_completo(self):
        return f'{self.serie}-{self.numero:06d}'

    @classmethod
    def obtener_siguiente_numero(cls, serie=None):
        from django.conf import settings
        serie = serie or getattr(settings, 'ORDEN_COMPRA_SERIE_DEFAULT', cls.SERIE_DEFAULT)
        ultimo = cls.objects.filter(serie=serie).order_by('-numero').values_list('numero', flat=True).first()
        return (ultimo or 0) + 1


class DetalleFactura(models.Model):
    """Tabla: detalle_factura — ítems de la factura de compra."""

    orden = models.ForeignKey(OrdenCompra, on_delete=models.CASCADE, related_name='detalles')
    numero_item = models.PositiveIntegerField(verbose_name='N° ítem', default=1)
    producto = models.ForeignKey(
        Producto, on_delete=models.SET_NULL, null=True, blank=True, related_name='detalles_factura'
    )
    descripcion = models.CharField(max_length=500, default='')
    laboratorio = models.CharField(max_length=150, blank=True)
    marca = models.CharField(max_length=100, blank=True)
    cantidad = models.DecimalField(max_digits=12, decimal_places=2)
    unidad_medida = models.CharField(max_length=20, default='UND')
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    igv_incluido = models.BooleanField(
        default=False,
        help_text='True si el precio unitario ya incluye IGV (18%).',
    )
    lote = models.CharField(max_length=50, blank=True)
    fecha_vencimiento = models.DateField(null=True, blank=True)

    class Meta:
        db_table = 'detalle_factura'
        unique_together = ('orden', 'numero_item')
        ordering = ['numero_item']

    def __str__(self):
        return f'{self.orden.numero_completo} - Ítem {self.numero_item}'


class Documento(models.Model):
    """Tabla: documentos — PDFs, certificados, fichas técnicas."""

    class Tipo(models.TextChoices):
        ORDEN_COMPRA = 'orden_compra', 'Orden de compra'
        CERTIFICADO = 'certificado', 'Certificado'
        FICHA_TECNICA = 'ficha_tecnica', 'Ficha técnica'
        FACTURA = 'factura', 'Factura'
        GUIA = 'guia', 'Guía de remisión'
        OTRO = 'otro', 'Otro'

    orden = models.ForeignKey(
        OrdenCompra, on_delete=models.CASCADE, related_name='documentos', null=True, blank=True
    )
    tipo = models.CharField(max_length=30, choices=Tipo.choices)
    nombre = models.CharField(max_length=200)
    archivo = models.FileField(upload_to='documentos/%Y/%m/')
    descripcion = models.TextField(blank=True)
    subido_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='documentos_subidos'
    )
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'documentos'
