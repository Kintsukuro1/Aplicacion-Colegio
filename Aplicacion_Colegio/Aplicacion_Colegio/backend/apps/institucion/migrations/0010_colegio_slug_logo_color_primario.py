from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('institucion', '0009_solicitudreunion'),
    ]

    operations = [
        migrations.AddField(
            model_name='colegio',
            name='slug',
            field=models.SlugField(blank=True, max_length=50, null=True, unique=True),
        ),
        migrations.AddField(
            model_name='colegio',
            name='logo',
            field=models.ImageField(blank=True, null=True, upload_to='colegios/logos/'),
        ),
        migrations.AddField(
            model_name='colegio',
            name='color_primario',
            field=models.CharField(default='#6366f1', max_length=7),
        ),
    ]
