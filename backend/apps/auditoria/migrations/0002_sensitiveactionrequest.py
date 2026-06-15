from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('auditoria', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='SensitiveActionRequest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('action_type', models.CharField(choices=[('ROLE_CHANGE', 'Cambio de rol'), ('PASSWORD_RESET', 'Reset de contraseña'), ('SENSITIVE_EXPORT', 'Exportación de datos sensibles')], db_index=True, max_length=32)),
                ('status', models.CharField(choices=[('PENDING', 'Pendiente'), ('APPROVED', 'Aprobada'), ('EXECUTED', 'Ejecutada'), ('FAILED', 'Fallida'), ('REJECTED', 'Rechazada')], db_index=True, default='PENDING', max_length=16)),
                ('school_rbd', models.CharField(blank=True, db_index=True, max_length=10, null=True)),
                ('justification', models.TextField(blank=True, default='')),
                ('approval_comment', models.TextField(blank=True, default='')),
                ('payload', models.JSONField(blank=True, default=dict)),
                ('execution_result', models.JSONField(blank=True, null=True)),
                ('requested_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('approved_at', models.DateTimeField(blank=True, null=True)),
                ('executed_at', models.DateTimeField(blank=True, null=True)),
                ('approved_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='sensitive_requests_approved', to=settings.AUTH_USER_MODEL)),
                ('executed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='sensitive_requests_executed', to=settings.AUTH_USER_MODEL)),
                ('requested_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='sensitive_requests_created', to=settings.AUTH_USER_MODEL)),
                ('target_user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='sensitive_requests_targeted', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Solicitud de Acción Sensible',
                'verbose_name_plural': 'Solicitudes de Acciones Sensibles',
                'db_table': 'auditoria_sensitive_action_request',
                'ordering': ['-requested_at'],
            },
        ),
        migrations.AddIndex(
            model_name='sensitiveactionrequest',
            index=models.Index(fields=['school_rbd', 'status', '-requested_at'], name='aud_sar_school_status_idx'),
        ),
        migrations.AddIndex(
            model_name='sensitiveactionrequest',
            index=models.Index(fields=['action_type', 'status', '-requested_at'], name='aud_sar_action_status_idx'),
        ),
        migrations.AddIndex(
            model_name='sensitiveactionrequest',
            index=models.Index(fields=['requested_by', '-requested_at'], name='aud_sar_requested_at_idx'),
        ),
    ]
