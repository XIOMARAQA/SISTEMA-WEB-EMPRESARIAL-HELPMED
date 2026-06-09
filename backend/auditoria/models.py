from django.conf import settings
from django.db import models


class Auditoria(models.Model):
    """Tabla: auditorias — registros formales de auditoría."""

    PREFIJO_CODIGO = 'AUD'

    class Tipo(models.TextChoices):
        INTERNA = 'interna', 'Interna'
        EXTERNA = 'externa', 'Externa'
        SEGURIDAD = 'seguridad', 'Seguridad de la información'
        ISO27001 = 'iso27001', 'ISO 27001'

    class Estado(models.TextChoices):
        PROGRAMADA = 'programada', 'Programada'
        EN_CURSO = 'en_curso', 'En curso'
        FINALIZADA = 'finalizada', 'Finalizada'

    codigo = models.CharField(max_length=30, unique=True)
    titulo = models.CharField(max_length=200)
    tipo = models.CharField(max_length=20, choices=Tipo.choices)
    auditor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField(null=True, blank=True)
    alcance = models.TextField()
    hallazgos = models.TextField(blank=True)
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.PROGRAMADA)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'auditorias'

    @classmethod
    def obtener_siguiente_codigo(cls):
        """Correlativo global: AUD-0001, AUD-0002, …"""
        base = f'{cls.PREFIJO_CODIGO}-'
        max_num = 0
        for codigo in cls.objects.filter(codigo__startswith=base).values_list('codigo', flat=True):
            parte = codigo[len(base):]
            if parte.isdigit():
                max_num = max(max_num, int(parte))
        return f'{base}{max_num + 1:04d}'


class RegistroAuditoria(models.Model):
    """Log de auditoría del sistema — trazabilidad de acciones."""

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    accion = models.CharField(max_length=100)
    modulo = models.CharField(max_length=50)
    tabla = models.CharField(max_length=50, blank=True)
    registro_id = models.PositiveIntegerField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    datos_anteriores = models.JSONField(null=True, blank=True)
    datos_nuevos = models.JSONField(null=True, blank=True)
    descripcion = models.TextField(blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'registros_auditoria'
        ordering = ['-creado_en']
        indexes = [
            models.Index(fields=['modulo', 'creado_en']),
            models.Index(fields=['usuario', 'creado_en']),
        ]
