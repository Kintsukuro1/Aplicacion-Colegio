from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('auditoria', '0002_sensitiveactionrequest'),
    ]

    operations = [
        migrations.AddField(
            model_name='configuracionauditoria',
            name='hosts_permitidos',
            field=models.TextField(
                blank=True,
                default='',
                help_text='Lista de hosts permitidos separados por coma',
            ),
        ),
    ]
