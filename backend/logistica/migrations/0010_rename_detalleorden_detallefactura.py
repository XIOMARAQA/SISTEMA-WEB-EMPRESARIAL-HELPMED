from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('logistica', '0009_detalle_marca'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='DetalleOrden',
            new_name='DetalleFactura',
        ),
        migrations.AlterModelTable(
            name='detallefactura',
            table='detalle_factura',
        ),
    ]
