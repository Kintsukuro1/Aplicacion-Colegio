from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0013_merge_20260527_2137'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='requiere_cambio_password',
            field=models.BooleanField(
                default=False,
                help_text='El usuario debe cambiar contraseña en el próximo inicio de sesión',
            ),
        ),
    ]
