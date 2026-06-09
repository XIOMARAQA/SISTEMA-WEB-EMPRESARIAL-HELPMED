"""Usuarios demo por actor — complementa seed_roles (solo crea los que faltan)."""
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from seguridad.models import Rol, UsuarioRol

User = get_user_model()

USUARIOS_ACTOR = [
    {
        'username': 'areaadm',
        'password': 'areaadm123',
        'email': 'area.administrativa@seguricel.com',
        'nombres': 'María',
        'apellidos': 'López Administración',
        'documento': '71234567',
        'rol': 'area_administrativa',
    },
    {
        'username': 'joperaciones',
        'password': 'joperaciones123',
        'email': 'operaciones@seguricel.com',
        'nombres': 'Carlos',
        'apellidos': 'Ríos Operaciones',
        'documento': '72345678',
        'rol': 'jefe_operaciones',
    },
    {
        'username': 'gerente',
        'password': 'gerente123',
        'email': 'gerente@seguricel.com',
        'nombres': 'Patricia',
        'apellidos': 'Vega Gerente',
        'documento': '73456789',
        'rol': 'gerente_general',
    },
    {
        'username': 'operario',
        'password': 'operario123',
        'email': 'operario@seguricel.com',
        'nombres': 'Luis',
        'apellidos': 'Mendoza Almacén',
        'documento': '74567890',
        'rol': 'operario_almacen',
    },
]


class Command(BaseCommand):
    help = 'Crea usuarios demo para actores del flujo (área administrativa, operaciones, etc.)'

    def handle(self, *args, **options):
        for datos in USUARIOS_ACTOR:
            rol_codigo = datos.pop('rol')
            password = datos.pop('password')
            rol = Rol.objects.filter(codigo=rol_codigo, activo=True).first()
            if not rol:
                self.stdout.write(self.style.WARNING(f'Rol no encontrado: {rol_codigo} — ejecute seed_roles'))
                continue

            user, created = User.objects.get_or_create(
                username=datos['username'],
                defaults={
                    **datos,
                    'estado': User.Estado.ACTIVO,
                    'is_active': True,
                },
            )
            if created:
                user.set_password(password)
                user.save(update_fields=['password'])
                self.stdout.write(self.style.SUCCESS(f'Usuario creado: {user.username} ({rol.nombre})'))
            else:
                self.stdout.write(f'Usuario existente: {user.username}')

            UsuarioRol.objects.get_or_create(usuario=user, rol=rol)
