from django.conf import settings
from django.db import models


class Medicion(models.Model):
    """Tabla: mediciones — control ambiental."""

    TEMP_MIN = 20.0
    TEMP_MAX = 25.0

    temperatura = models.DecimalField(max_digits=5, decimal_places=2)
    humedad = models.DecimalField(max_digits=5, decimal_places=2)
    fecha = models.DateField()
    hora = models.TimeField()
    responsable = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='mediciones_ambientales'
    )
    ubicacion = models.CharField(max_length=100, default='Almacén principal')
    observaciones = models.TextField(blank=True)
    fuera_rango = models.BooleanField(default=False)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'mediciones'
        ordering = ['-fecha', '-hora']

    def evaluar_rango(self):
        return self.TEMP_MIN <= float(self.temperatura) <= self.TEMP_MAX


class AccionCorrectiva(models.Model):
    """Tabla: acciones_correctivas"""

    class Origen(models.TextChoices):
        AMBIENTAL = 'ambiental', 'Control ambiental'
        CALIDAD = 'calidad', 'Control de calidad'
        INVENTARIO = 'inventario', 'Inventario'
        RIESGO = 'riesgo', 'Gestión de riesgos'
        OTRO = 'otro', 'Otro'

    class Estado(models.TextChoices):
        PENDIENTE = 'pendiente', 'Pendiente'
        EN_PROCESO = 'en_proceso', 'En proceso'
        COMPLETADA = 'completada', 'Completada'
        CANCELADA = 'cancelada', 'Cancelada'

    origen = models.CharField(max_length=20, choices=Origen.choices)
    referencia_id = models.PositiveIntegerField(null=True, blank=True)
    descripcion = models.TextField()
    responsable = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='acciones_correctivas'
    )
    fecha_programada = models.DateField(null=True, blank=True)
    fecha_cierre = models.DateField(null=True, blank=True)
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.PENDIENTE)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'acciones_correctivas'


class IncidenteAmbiental(models.Model):
    medicion = models.OneToOneField(Medicion, on_delete=models.CASCADE, related_name='incidente')
    descripcion = models.TextField()
    accion_correctiva = models.ForeignKey(
        AccionCorrectiva, on_delete=models.SET_NULL, null=True, blank=True, related_name='incidentes_ambientales'
    )
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'incidentes_ambientales'
