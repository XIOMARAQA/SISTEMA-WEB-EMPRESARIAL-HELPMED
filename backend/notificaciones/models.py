from django.conf import settings
from django.db import models


class Notificacion(models.Model):
    """Tabla: notificaciones — alertas del sistema."""

    class Tipo(models.TextChoices):
        INVENTARIO = 'inventario', 'Inventario'
        AMBIENTAL = 'ambiental', 'Control ambiental'
        CALIDAD = 'calidad', 'Calidad'
        RIESGO = 'riesgo', 'Riesgo'
        SEGURIDAD = 'seguridad', 'Seguridad'
        SISTEMA = 'sistema', 'Sistema'

    class Prioridad(models.TextChoices):
        BAJA = 'baja', 'Baja'
        MEDIA = 'media', 'Media'
        ALTA = 'alta', 'Alta'
        CRITICA = 'critica', 'Crítica'

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notificaciones'
    )
    tipo = models.CharField(max_length=20, choices=Tipo.choices)
    prioridad = models.CharField(max_length=20, choices=Prioridad.choices, default=Prioridad.MEDIA)
    titulo = models.CharField(max_length=200)
    mensaje = models.TextField()
    leida = models.BooleanField(default=False)
    referencia_modulo = models.CharField(max_length=50, blank=True)
    referencia_id = models.PositiveIntegerField(null=True, blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'notificaciones'
        ordering = ['-creado_en']


class Backup(models.Model):
    """Tabla: backups."""

    class Estado(models.TextChoices):
        EXITOSO = 'exitoso', 'Exitoso'
        FALLIDO = 'fallido', 'Fallido'
        EN_PROCESO = 'en_proceso', 'En proceso'

    nombre = models.CharField(max_length=200)
    archivo = models.FileField(upload_to='backups/', null=True, blank=True)
    tamano_bytes = models.BigIntegerField(default=0)
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.EN_PROCESO)
    ejecutado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    observaciones = models.TextField(blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'backups'
