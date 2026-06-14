from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('notificaciones', '0003_dispositivo_fcm'),
    ]

    operations = [
        migrations.DeleteModel(
            name='DispositivoFCM',
        ),
    ]
