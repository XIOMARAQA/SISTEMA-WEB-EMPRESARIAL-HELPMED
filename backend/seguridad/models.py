from django.contrib.auth.models import AbstractUser
from django.db import models


class Usuario(AbstractUser):
    """Tabla: usuarios"""

    class Estado(models.TextChoices):
        ACTIVO = 'activo', 'Activo'
        INACTIVO = 'inactivo', 'Inactivo'
        BLOQUEADO = 'bloqueado', 'Bloqueado'

    nombres = models.CharField(max_length=100, blank=True)
    apellidos = models.CharField(max_length=100, blank=True)
    documento = models.CharField(max_length=20, unique=True, null=True, blank=True)
    telefono = models.CharField(max_length=20, blank=True)
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.ACTIVO)
    intentos_fallidos = models.PositiveSmallIntegerField(default=0)
    bloqueado_hasta = models.DateTimeField(null=True, blank=True)
    ultimo_acceso = models.DateTimeField(null=True, blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'usuarios'
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'

    def __str__(self):
        return self.get_full_name() or self.username


class Rol(models.Model):
    """Tabla: roles"""

    codigo = models.CharField(max_length=50, unique=True)
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True)
    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'roles'

    def __str__(self):
        return self.nombre


class Permiso(models.Model):
    """Tabla: permisos"""

    codigo = models.CharField(max_length=100, unique=True)
    nombre = models.CharField(max_length=150)
    modulo = models.CharField(max_length=50)
    descripcion = models.TextField(blank=True)

    class Meta:
        db_table = 'permisos'

    def __str__(self):
        return f'{self.modulo}: {self.nombre}'


class RolPermiso(models.Model):
    rol = models.ForeignKey(Rol, on_delete=models.CASCADE, related_name='permisos_asignados')
    permiso = models.ForeignKey(Permiso, on_delete=models.CASCADE, related_name='roles_asignados')

    class Meta:
        db_table = 'roles_permisos'
        unique_together = ('rol', 'permiso')


class UsuarioRol(models.Model):
    """Tabla: usuarios_roles"""

    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='roles_asignados')
    rol = models.ForeignKey(Rol, on_delete=models.CASCADE, related_name='usuarios_asignados')
    asignado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'usuarios_roles'
        unique_together = ('usuario', 'rol')


class SesionUsuario(models.Model):
    """Control de sesiones activas."""

    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='sesiones')
    token_jti = models.CharField(max_length=255, unique=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    activa = models.BooleanField(default=True)
    creada_en = models.DateTimeField(auto_now_add=True)
    expira_en = models.DateTimeField()
    cerrada_en = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'sesiones_usuario'
        indexes = [models.Index(fields=['usuario', 'activa'])]


class RefreshToken(models.Model):
    """Tabla: refresh_tokens"""

    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='refresh_tokens')
    token = models.CharField(max_length=512, unique=True)
    revocado = models.BooleanField(default=False)
    creado_en = models.DateTimeField(auto_now_add=True)
    expira_en = models.DateTimeField()

    class Meta:
        db_table = 'refresh_tokens'


class IntentoLogin(models.Model):
    """Bloqueo por intentos fallidos."""

    username = models.CharField(max_length=150)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    exitoso = models.BooleanField(default=False)
    motivo = models.CharField(max_length=255, blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'intentos_login'
        indexes = [models.Index(fields=['username', 'creado_en'])]


class TokenRecuperacion(models.Model):
    """Recuperación de contraseña."""

    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='tokens_recuperacion')
    token = models.CharField(max_length=128, unique=True)
    usado = models.BooleanField(default=False)
    creado_en = models.DateTimeField(auto_now_add=True)
    expira_en = models.DateTimeField()

    class Meta:
        db_table = 'tokens_recuperacion'
