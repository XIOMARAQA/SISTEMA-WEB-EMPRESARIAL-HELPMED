import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('calidad', '0003_alter_incidenciacalidad_producto'),
        ('logistica', '0010_rename_detalleorden_detallefactura'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql=(
                        'ALTER TABLE incidencias_calidad '
                        'RENAME COLUMN detalle_orden_id TO detalle_factura_id;'
                    ),
                    reverse_sql=(
                        'ALTER TABLE incidencias_calidad '
                        'RENAME COLUMN detalle_factura_id TO detalle_orden_id;'
                    ),
                ),
            ],
            state_operations=[
                migrations.RemoveField(
                    model_name='incidenciacalidad',
                    name='detalle_orden',
                ),
                migrations.AddField(
                    model_name='incidenciacalidad',
                    name='detalle_factura',
                    field=models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='incidencias',
                        to='logistica.detallefactura',
                    ),
                ),
            ],
        ),
    ]
