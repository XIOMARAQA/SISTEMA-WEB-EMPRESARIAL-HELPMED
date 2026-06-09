from django.conf import settings
from django.db import models

from logistica.models import DetalleFactura, OrdenCompra, Producto


class IncidenciaCalidad(models.Model):
    """Productos rechazados y seguimiento de incidencias."""

    class Estado(models.TextChoices):
        ABIERTA = 'abierta', 'Abierta'
        EN_SEGUIMIENTO = 'en_seguimiento', 'En seguimiento'
        CERRADA = 'cerrada', 'Cerrada'

    orden = models.ForeignKey(
        OrdenCompra, on_delete=models.SET_NULL, null=True, blank=True, related_name='incidencias_calidad'
    )
    detalle_factura = models.ForeignKey(
        DetalleFactura, on_delete=models.SET_NULL, null=True, blank=True, related_name='incidencias'
    )
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT, null=True, blank=True, related_name='incidencias_calidad')
    cantidad_rechazada = models.DecimalField(max_digits=12, decimal_places=2)
    motivo = models.TextField()
    comentarios = models.TextField(blank=True)
    accion_correctiva = models.TextField(blank=True)
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.ABIERTA)
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='incidencias_registradas'
    )
    creado_en = models.DateTimeField(auto_now_add=True)
    cerrado_en = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'incidencias_calidad'
        verbose_name = 'Incidencia de calidad'
        verbose_name_plural = 'Incidencias de calidad'


class EvidenciaCalidad(models.Model):
    incidencia = models.ForeignKey(IncidenciaCalidad, on_delete=models.CASCADE, related_name='evidencias')
    nombre = models.CharField(max_length=200)
    archivo = models.FileField(upload_to='calidad/evidencias/%Y/%m/')
    descripcion = models.TextField(blank=True)
    subido_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'evidencias_calidad'
