from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0011_seed_jefe_utp_role_and_chile_capabilities'),
    ]

    operations = [
        migrations.AddField(
            model_name='perfilestudiante',
            name='foto_perfil',
            field=models.ImageField(
                blank=True,
                help_text='Fotografía de perfil del estudiante',
                null=True,
                upload_to='perfiles/estudiantes/%Y/%m/',
            ),
        ),
    ]
