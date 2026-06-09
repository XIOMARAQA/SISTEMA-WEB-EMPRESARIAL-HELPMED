import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventario', '0004_movimientoinventario_codigo_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='inventario',
            name='cantidad_fisica',
            field=models.DecimalField(
                blank=True, decimal_places=2, max_digits=12, null=True,
                verbose_name='Cantidad contada físicamente',
            ),
        ),
        migrations.AddField(
            model_name='inventario',
            name='cuadre_estado',
            field=models.CharField(
                choices=[
                    ('pendiente', 'Pendiente'),
                    ('conforme', 'Conforme'),
                    ('discrepancia', 'Discrepancia'),
                ],
                default='pendiente',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='inventario',
            name='cuadre_observaciones',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='inventario',
            name='cuadre_actualizado_en',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='inventario',
            name='cuadre_por',
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                related_name='cuadres_inventario', to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
