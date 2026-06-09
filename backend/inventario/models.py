from django.conf import settings
from django.db import models
from django.utils import timezone

from logistica.models import Producto


class Inventario(models.Model):
    """Tabla: inventarios — stock por producto y lote."""

    class ClasificacionVencimiento(models.TextChoices):
        CONFORME = 'conforme', 'Conforme (>60 días)'
        REPOSICION = 'reposicion', 'Reposición (30-60 días)'
        ALTA_PRIORIDAD = 'alta_prioridad', 'Alta prioridad (<30 días)'
        RETIRO_INMEDIATO = 'retiro_inmediato', 'Retiro inmediato (caducado)'

    producto = models.ForeignKey(Producto, on_delete=models.PROTECT, related_name='inventarios')
    lote = models.CharField(max_length=50)
    cantidad = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    fecha_vencimiento = models.DateField(null=True, blank=True)
    ubicacion = models.CharField(max_length=100, default='Almacén principal')
    clasificacion = models.CharField(
        max_length=20, choices=ClasificacionVencimiento.choices, blank=True
    )
    cantidad_fisica = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        verbose_name='Cantidad contada físicamente',
    )
    class CuadreEstado(models.TextChoices):
        PENDIENTE = 'pendiente', 'Pendiente'
        CONFORME = 'conforme', 'Conforme'
        DISCREPANCIA = 'discrepancia', 'Discrepancia'

    cuadre_estado = models.CharField(
        max_length=20, choices=CuadreEstado.choices, default=CuadreEstado.PENDIENTE,
    )
    cuadre_observaciones = models.TextField(blank=True)
    cuadre_actualizado_en = models.DateTimeField(null=True, blank=True)
    cuadre_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cuadres_inventario',
    )
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'inventarios'
        unique_together = ('producto', 'lote', 'ubicacion')

    def evaluar_cuadre(self):
        if self.cantidad_fisica is None:
            return self.CuadreEstado.PENDIENTE
        if self.cantidad_fisica == self.cantidad:
            return self.CuadreEstado.CONFORME
        return self.CuadreEstado.DISCREPANCIA

    def calcular_clasificacion(self):
        if not self.fecha_vencimiento:
            return self.ClasificacionVencimiento.CONFORME
        dias = (self.fecha_vencimiento - timezone.now().date()).days
        if dias < 0:
            return self.ClasificacionVencimiento.RETIRO_INMEDIATO
        if dias < 30:
            return self.ClasificacionVencimiento.ALTA_PRIORIDAD
        if dias <= 60:
            return self.ClasificacionVencimiento.REPOSICION
        return self.ClasificacionVencimiento.CONFORME


class MovimientoInventario(models.Model):
    """Tabla: movimientos_inventario — FEAT 09/10 entradas y salidas."""

    class Tipo(models.TextChoices):
        ENTRADA = 'entrada', 'Entrada'
        SALIDA = 'salida', 'Salida'
        AJUSTE = 'ajuste', 'Ajuste'
        TRANSFERENCIA = 'transferencia', 'Transferencia'

    class TerceroTipo(models.TextChoices):
        PROVEEDOR = 'proveedor', 'Proveedor'
        CLIENTE = 'cliente', 'Cliente'

    inventario = models.ForeignKey(Inventario, on_delete=models.PROTECT, related_name='movimientos')
    codigo = models.CharField(max_length=30, unique=True, blank=True)
    tipo = models.CharField(max_length=20, choices=Tipo.choices)
    cantidad = models.DecimalField(max_digits=12, decimal_places=2)
    stock_anterior = models.DecimalField(max_digits=12, decimal_places=2)
    stock_posterior = models.DecimalField(max_digits=12, decimal_places=2)
    tercero_tipo = models.CharField(max_length=20, choices=TerceroTipo.choices, blank=True)
    tercero_documento = models.CharField(max_length=20, blank=True)
    tercero_nombre = models.CharField(max_length=200, blank=True)
    doc_fecha = models.DateField(null=True, blank=True)
    doc_tipo = models.CharField(max_length=50, blank=True)
    doc_serie = models.CharField(max_length=20, blank=True)
    doc_numero = models.CharField(max_length=30, blank=True)
    motivo = models.CharField(max_length=200, blank=True)
    referencia = models.CharField(max_length=100, blank=True)
    observaciones = models.TextField(blank=True)
    registrado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'movimientos_inventario'
        ordering = ['-creado_en']

    @classmethod
    def generar_codigo(cls, tipo):
        prefijo = 'E' if tipo == cls.Tipo.ENTRADA else 'S' if tipo == cls.Tipo.SALIDA else 'M'
        anio = timezone.now().year
        ultimo = cls.objects.filter(codigo__startswith=f'{prefijo}-{anio}-').order_by('-id').first()
        if ultimo and ultimo.codigo:
            try:
                seq = int(ultimo.codigo.split('-')[-1]) + 1
            except ValueError:
                seq = 1
        else:
            seq = 1
        return f'{prefijo}-{anio}-{seq:06d}'


class InventarioFisico(models.Model):
    """Conteo físico de inventario."""

    class Estado(models.TextChoices):
        EN_PROCESO = 'en_proceso', 'En proceso'
        FINALIZADO = 'finalizado', 'Finalizado'
        CANCELADO = 'cancelado', 'Cancelado'

    codigo = models.CharField(max_length=30, unique=True)
    fecha = models.DateField()
    responsable = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.EN_PROCESO)
    observaciones = models.TextField(blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'inventarios_fisicos'


class DetalleInventarioFisico(models.Model):
    inventario_fisico = models.ForeignKey(
        InventarioFisico, on_delete=models.CASCADE, related_name='detalles'
    )
    inventario = models.ForeignKey(Inventario, on_delete=models.PROTECT)
    cantidad_sistema = models.DecimalField(max_digits=12, decimal_places=2)
    cantidad_fisica = models.DecimalField(max_digits=12, decimal_places=2)
    diferencia = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    observaciones = models.TextField(blank=True)

    class Meta:
        db_table = 'detalle_inventario_fisico'
