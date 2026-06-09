from django.conf import settings
from django.db import models


class Activo(models.Model):
    """Tabla: activos — gestión de activos ISO/IEC 27005."""

    class Clasificacion(models.TextChoices):
        INFORMACION = 'informacion', 'Información'
        SOFTWARE = 'software', 'Software'
        HARDWARE = 'hardware', 'Hardware'
        PERSONAL = 'personal', 'Personal'
        SERVICIOS = 'servicios', 'Servicios'
        INFRAESTRUCTURA = 'infraestructura', 'Infraestructura'

    class Criticidad(models.TextChoices):
        BAJA = 'baja', 'Baja'
        MEDIA = 'media', 'Media'
        ALTA = 'alta', 'Alta'
        CRITICA = 'critica', 'Crítica'

    PREFIJOS_CODIGO = {
        Clasificacion.INFORMACION: 'ACT-INF',
        Clasificacion.SOFTWARE: 'ACT-SFW',
        Clasificacion.HARDWARE: 'ACT-HDW',
        Clasificacion.PERSONAL: 'ACT-PER',
        Clasificacion.SERVICIOS: 'ACT-SRV',
        Clasificacion.INFRAESTRUCTURA: 'ACT-INS',
    }

    codigo = models.CharField(max_length=50, unique=True)
    nombre = models.CharField(max_length=200)
    propietario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='activos_propiedad'
    )
    clasificacion = models.CharField(max_length=20, choices=Clasificacion.choices)
    criticidad = models.CharField(max_length=20, choices=Criticidad.choices)
    descripcion = models.TextField(blank=True)
    ubicacion = models.CharField(max_length=100, blank=True)
    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'activos'

    def __str__(self):
        return f'{self.codigo} - {self.nombre}'

    @classmethod
    def prefijo_codigo(cls, clasificacion):
        prefijo = cls.PREFIJOS_CODIGO.get(clasificacion)
        if not prefijo:
            raise ValueError(f'Clasificación no válida: {clasificacion}')
        return prefijo

    @classmethod
    def obtener_siguiente_codigo(cls, clasificacion):
        """Correlativo por clasificación: ACT-INF-0001, ACT-SFW-0001, etc."""
        prefijo = cls.prefijo_codigo(clasificacion)
        base = f'{prefijo}-'
        max_num = 0
        for codigo in cls.objects.filter(codigo__startswith=base).values_list('codigo', flat=True):
            parte = codigo[len(base):]
            if parte.isdigit():
                max_num = max(max_num, int(parte))
        return f'{base}{max_num + 1:04d}'


class Amenaza(models.Model):
    """Tabla: amenazas."""

    PREFIJO_CODIGO = 'AMN'

    class Tipo(models.TextChoices):
        PHISHING = 'phishing', 'Phishing'
        MALWARE = 'malware', 'Malware'
        RANSOMWARE = 'ransomware', 'Ransomware'
        SQL_INJECTION = 'sql_injection', 'SQL Injection'
        XSS = 'xss', 'XSS'
        FUERZA_BRUTA = 'fuerza_bruta', 'Fuerza Bruta'
        ERROR_HUMANO = 'error_humano', 'Error Humano'
        ROBO_EQUIPOS = 'robo_equipos', 'Robo de Equipos'
        ACCESO_NO_AUTORIZADO = 'acceso_no_autorizado', 'Acceso No Autorizado'

    codigo = models.CharField(max_length=50, unique=True)
    tipo = models.CharField(max_length=30, choices=Tipo.choices)
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)
    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'amenazas'

    def __str__(self):
        return self.nombre

    @classmethod
    def obtener_siguiente_codigo(cls):
        """Correlativo global: AMN-0001, AMN-0002, …"""
        base = f'{cls.PREFIJO_CODIGO}-'
        max_num = 0
        for codigo in cls.objects.filter(codigo__startswith=base).values_list('codigo', flat=True):
            parte = codigo[len(base):]
            if parte.isdigit():
                max_num = max(max_num, int(parte))
        return f'{base}{max_num + 1:04d}'


class Vulnerabilidad(models.Model):
    """Tabla: vulnerabilidades."""

    PREFIJO_CODIGO = 'VLN'

    class Severidad(models.TextChoices):
        BAJA = 'baja', 'Baja'
        MEDIA = 'media', 'Media'
        ALTA = 'alta', 'Alta'
        CRITICA = 'critica', 'Crítica'

    class Estado(models.TextChoices):
        ABIERTA = 'abierta', 'Abierta'
        EN_TRATAMIENTO = 'en_tratamiento', 'En tratamiento'
        MITIGADA = 'mitigada', 'Mitigada'
        CERRADA = 'cerrada', 'Cerrada'

    activo = models.ForeignKey(Activo, on_delete=models.CASCADE, related_name='vulnerabilidades')
    codigo = models.CharField(max_length=50, unique=True)
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField()
    severidad = models.CharField(max_length=20, choices=Severidad.choices)
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.ABIERTA)
    evidencia = models.FileField(upload_to='riesgos/vulnerabilidades/', null=True, blank=True)
    detectada_en = models.DateField(auto_now_add=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'vulnerabilidades'

    @classmethod
    def obtener_siguiente_codigo(cls):
        """Correlativo global: VLN-0001, VLN-0002, …"""
        base = f'{cls.PREFIJO_CODIGO}-'
        max_num = 0
        for codigo in cls.objects.filter(codigo__startswith=base).values_list('codigo', flat=True):
            parte = codigo[len(base):]
            if parte.isdigit():
                max_num = max(max_num, int(parte))
        return f'{base}{max_num + 1:04d}'


class Riesgo(models.Model):
    """Tabla: riesgos."""

    PREFIJO_CODIGO = 'RSG'

    codigo = models.CharField(max_length=50, unique=True)
    activo = models.ForeignKey(Activo, on_delete=models.CASCADE, related_name='riesgos')
    amenaza = models.ForeignKey(Amenaza, on_delete=models.PROTECT, related_name='riesgos')
    vulnerabilidad = models.ForeignKey(
        Vulnerabilidad, on_delete=models.SET_NULL, null=True, blank=True, related_name='riesgos'
    )
    descripcion = models.TextField()
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'riesgos'

    @classmethod
    def obtener_siguiente_codigo(cls):
        """Correlativo global: RSG-0001, RSG-0002, …"""
        base = f'{cls.PREFIJO_CODIGO}-'
        max_num = 0
        for codigo in cls.objects.filter(codigo__startswith=base).values_list('codigo', flat=True):
            parte = codigo[len(base):]
            if parte.isdigit():
                max_num = max(max_num, int(parte))
        return f'{base}{max_num + 1:04d}'


class EvaluacionRiesgo(models.Model):
    """Tabla: evaluaciones_riesgo — RIESGO = PROBABILIDAD × IMPACTO."""

    class Probabilidad(models.IntegerChoices):
        MUY_BAJA = 1, 'Muy Baja'
        BAJA = 2, 'Baja'
        MEDIA = 3, 'Media'
        ALTA = 4, 'Alta'
        MUY_ALTA = 5, 'Muy Alta'

    class Impacto(models.IntegerChoices):
        INSIGNIFICANTE = 1, 'Insignificante'
        MENOR = 2, 'Menor'
        MODERADO = 3, 'Moderado'
        MAYOR = 4, 'Mayor'
        CRITICO = 5, 'Crítico'

    class Nivel(models.TextChoices):
        BAJO = 'bajo', 'Bajo (1-5)'
        MEDIO = 'medio', 'Medio (6-10)'
        ALTO = 'alto', 'Alto (11-15)'
        CRITICO = 'critico', 'Crítico (16-25)'

    class Tipo(models.TextChoices):
        INHERENTE = 'inherente', 'Riesgo inherente'
        RESIDUAL = 'residual', 'Riesgo residual'

    riesgo = models.ForeignKey(Riesgo, on_delete=models.CASCADE, related_name='evaluaciones')
    tipo = models.CharField(max_length=20, choices=Tipo.choices, default=Tipo.INHERENTE)
    probabilidad = models.PositiveSmallIntegerField(choices=Probabilidad.choices)
    impacto = models.PositiveSmallIntegerField(choices=Impacto.choices)
    valor_riesgo = models.PositiveSmallIntegerField()
    nivel = models.CharField(max_length=20, choices=Nivel.choices)
    evaluado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    fecha_evaluacion = models.DateField()
    observaciones = models.TextField(blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'evaluaciones_riesgo'

    @staticmethod
    def calcular_nivel(valor):
        if valor <= 5:
            return EvaluacionRiesgo.Nivel.BAJO
        if valor <= 10:
            return EvaluacionRiesgo.Nivel.MEDIO
        if valor <= 15:
            return EvaluacionRiesgo.Nivel.ALTO
        return EvaluacionRiesgo.Nivel.CRITICO


class TratamientoRiesgo(models.Model):
    """Tabla: tratamientos_riesgo."""

    class Estrategia(models.TextChoices):
        MITIGAR = 'mitigar', 'Mitigar'
        TRANSFERIR = 'transferir', 'Transferir'
        EVITAR = 'evitar', 'Evitar'
        ACEPTAR = 'aceptar', 'Aceptar'

    riesgo = models.ForeignKey(Riesgo, on_delete=models.CASCADE, related_name='tratamientos')
    estrategia = models.CharField(max_length=20, choices=Estrategia.choices)
    responsable = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='tratamientos_riesgo'
    )
    control_aplicado = models.TextField()
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField(null=True, blank=True)
    riesgo_residual = models.PositiveSmallIntegerField(null=True, blank=True)
    evaluacion_residual = models.ForeignKey(
        EvaluacionRiesgo,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tratamientos',
    )
    observaciones = models.TextField(blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'tratamientos_riesgo'


class ControlISO27001(models.Model):
    """Tabla: controles_iso27001."""

    codigo = models.CharField(max_length=20, unique=True)
    nombre = models.CharField(max_length=200)
    dominio = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True)
    implementado = models.BooleanField(default=False)
    fecha_implementacion = models.DateField(null=True, blank=True)
    responsable = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='controles_iso',
    )
    riesgo = models.ForeignKey(
        Riesgo, on_delete=models.SET_NULL, null=True, blank=True, related_name='controles'
    )
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'controles_iso27001'


class IndicadorCIA(models.Model):
    """Indicadores Confidencialidad, Integridad, Disponibilidad — variable dependiente tesis."""

    class Dimension(models.TextChoices):
        CONFIDENCIALIDAD = 'confidencialidad', 'Confidencialidad'
        INTEGRIDAD = 'integridad', 'Integridad'
        DISPONIBILIDAD = 'disponibilidad', 'Disponibilidad'

    dimension = models.CharField(max_length=20, choices=Dimension.choices)
    periodo = models.CharField(max_length=7)  # YYYY-MM
    accesos_no_autorizados = models.PositiveIntegerField(default=0)
    incidentes_alteracion = models.PositiveIntegerField(default=0)
    tiempo_indisponibilidad_min = models.PositiveIntegerField(default=0)
    nivel_riesgo_residual = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    percepcion_seguridad = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    registrado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'indicadores_cia'
        unique_together = ('dimension', 'periodo')
