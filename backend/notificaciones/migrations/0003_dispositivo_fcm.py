# Generated manually for DispositivoFCM

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('notificaciones', '0002_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='DispositivoFCM',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('token', models.CharField(max_length=512, unique=True)),
                ('plataforma', models.CharField(
                    choices=[('web', 'Web'), ('android', 'Android'), ('ios', 'iOS')],
                    default='web',
                    max_length=20,
                )),
                ('activo', models.BooleanField(default=True)),
                ('creado_en', models.DateTimeField(auto_now_add=True)),
                ('actualizado_en', models.DateTimeField(auto_now=True)),
                ('usuario', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='dispositivos_fcm',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'db_table': 'dispositivos_fcm',
            },
        ),
        migrations.AddIndex(
            model_name='dispositivofcm',
            index=models.Index(fields=['usuario', 'activo'], name='dispositivo_usuario_activo_idx'),
        ),
    ]
