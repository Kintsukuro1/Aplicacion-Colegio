from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('security', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='passwordhistory',
            name='tipo_accion',
            field=models.CharField(
                blank=True,
                default='cambio_voluntario',
                help_text='Tipo de evento registrado (cambio_voluntario, cambio_forzado, reset_admin)',
                max_length=32,
            ),
        ),
    ]
