from django.core.management.base import BaseCommand

from logistica.models import Categoria, Producto, Subcategoria, UnidadMedida

UNIDADES = [
    ('UND', 'Unidad', 'und'),
    ('CAJA', 'Caja', 'cja'),
    ('FRASCO', 'Frasco', 'frs'),
    ('AMP', 'Ampolla', 'amp'),
    ('TUBO', 'Tubo', 'tub'),
    ('KG', 'Kilogramo', 'kg'),
    ('LT', 'Litro', 'lt'),
    ('PAR', 'Par', 'par'),
    ('ROLLO', 'Rollo', 'rll'),
]

CATEGORIAS = [
    ('MED', 'Medicinas', 'Medicamentos e insumos farmacéuticos', True),
    ('MAT', 'Materiales médicos', 'Material médico descartable y reutilizable', False),
    ('EPP', 'Equipos de protección', 'EPP y bioseguridad', False),
]

SUBCATEGORIAS_MED = [
    ('ANALG', 'Analgésicos'),
    ('ANTIB', 'Antibiótico'),
    ('AGRIP', 'Antigripales'),
    ('ANTIH', 'Antihistamínicos'),
    ('ANTIIN', 'Antiinflamatorios'),
    ('ANTIP', 'Antipirético'),
    ('VIT', 'Vitaminas'),
]


class Command(BaseCommand):
    help = 'Carga datos maestros iniciales (unidades, categorías, subcategorías)'

    def handle(self, *args, **options):
        for codigo, nombre, simbolo in UNIDADES:
            UnidadMedida.objects.get_or_create(
                codigo=codigo, defaults={'nombre': nombre, 'simbolo': simbolo},
            )
        for codigo, nombre, desc, req_vcto in CATEGORIAS:
            cat, _ = Categoria.objects.update_or_create(
                codigo=codigo,
                defaults={
                    'nombre': nombre,
                    'descripcion': desc,
                    'requiere_fecha_vencimiento': req_vcto,
                    'activo': True,
                },
            )
            if codigo == 'MED':
                for sc_cod, sc_nom in SUBCATEGORIAS_MED:
                    Subcategoria.objects.get_or_create(
                        categoria=cat,
                        codigo=sc_cod,
                        defaults={'nombre': sc_nom, 'activo': True},
                    )
        und = UnidadMedida.objects.get(codigo='UND')
        Producto.objects.filter(unidad__isnull=True).update(unidad=und)
        self.stdout.write(self.style.SUCCESS('Datos maestros cargados correctamente.'))
