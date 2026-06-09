from django.core.management.base import BaseCommand

from inventario.services.recepcion import registrar_entrada_desde_factura_controlada
from logistica.models import OrdenCompra


class Command(BaseCommand):
    help = 'Genera entradas de inventario para facturas con control de calidad ya cerrado'

    def handle(self, *args, **options):
        qs = OrdenCompra.objects.filter(
            estado=OrdenCompra.Estado.ATENDIDO,
        ).exclude(
            control_calidad_estado=OrdenCompra.EstadoCalidad.PENDIENTE,
        ).select_related('proveedor', 'registrado_por').prefetch_related('detalles')

        total_entradas = 0
        for orden in qs:
            user = orden.control_calidad_por or orden.registrado_por
            result = registrar_entrada_desde_factura_controlada(orden, user)
            total_entradas += result['entradas']
            if result['entradas']:
                self.stdout.write(self.style.SUCCESS(
                    f'{orden.numero_completo}: {result["entradas"]} entrada(s)'
                ))
            if result['omitidos_sin_producto']:
                self.stdout.write(self.style.WARNING(
                    f'{orden.numero_completo}: sin catálogo — {", ".join(result["omitidos_sin_producto"])}'
                ))

        self.stdout.write(self.style.SUCCESS(f'Total movimientos creados: {total_entradas}'))
