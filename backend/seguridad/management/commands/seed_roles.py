from django.core.management.base import BaseCommand

from seguridad.models import Rol


ROLES = [
    ('admin', 'Administrador', 'Acceso total al sistema HelpMed'),
    ('jefe_compras', 'Jefe de Compras', 'Gestiona compras y reposiciones'),
    ('jefe_almacen', 'Jefe de Almacén', 'Supervisa recepción, calidad e inventario'),
    ('supervisor_almacen', 'Supervisor de Almacén', 'Supervisión operativa del almacén'),
    ('operario_almacen', 'Operario de Almacén', 'Ejecuta registros, controles y almacenamiento'),
    ('encargado_calidad', 'Control de Calidad', 'Verifica calidad y cumplimiento de estándares'),
    ('jefe_operaciones', 'Jefe de Operaciones', 'Atiende incidencias críticas'),
    ('area_administrativa', 'Área Administrativa', 'Evalúa discrepancias de inventario'),
    ('gerente_general', 'Gerente General', 'Supervisa incidencias y reportes críticos'),
    ('auditor_seguridad', 'Auditor de Seguridad', 'Auditoría y gestión de riesgos ISO 27005'),
]


class Command(BaseCommand):
    help = 'Carga los roles iniciales de HelpMed'

    def handle(self, *args, **options):
        for codigo, nombre, descripcion in ROLES:
            rol, created = Rol.objects.update_or_create(
                codigo=codigo,
                defaults={'nombre': nombre, 'descripcion': descripcion, 'activo': True},
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Rol creado: {nombre}'))
            else:
                self.stdout.write(f'Rol actualizado: {nombre}')
