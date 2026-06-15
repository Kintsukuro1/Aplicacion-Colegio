"""
Migración: Fase 1 — tipo de dependencia en Colegio + modelo ConfiguracionAcademica.

Cambios:
- Agrega campo `tipo` (MUNICIPAL / SUBVENCIONADO / PARTICULAR / TP) a Colegio
- Crea tabla `configuracion_academica` con parámetros operativos por colegio
"""
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('institucion', '0005_cicloacademico_descripcion'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # 1. Campo tipo en Colegio
        migrations.AddField(
            model_name='colegio',
            name='tipo',
            field=models.CharField(
                choices=[
                    ('MUNICIPAL', 'Municipal'),
                    ('SUBVENCIONADO', 'Particular Subvencionado'),
                    ('PARTICULAR', 'Particular Pagado'),
                    ('TP', 'Técnico-Profesional'),
                ],
                default='SUBVENCIONADO',
                help_text='Tipo de dependencia del establecimiento (determina subvenciones disponibles)',
                max_length=20,
            ),
        ),

        # 2. Tabla ConfiguracionAcademica
        migrations.CreateModel(
            name='ConfiguracionAcademica',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('anio_escolar_activo', models.PositiveSmallIntegerField(
                    help_text='Año escolar en curso (ej: 2025)',
                )),
                ('regimen_evaluacion', models.CharField(
                    choices=[
                        ('SEMESTRAL', 'Semestral (2 períodos)'),
                        ('TRIMESTRAL', 'Trimestral (3 períodos)'),
                        ('ANUAL', 'Anual (1 período)'),
                    ],
                    default='SEMESTRAL',
                    help_text='Régimen de períodos de evaluación del colegio',
                    max_length=15,
                )),
                ('tiene_convenio_sep', models.BooleanField(
                    default=False,
                    help_text='¿El colegio tiene convenio SEP vigente con el MINEDUC?',
                )),
                ('porcentaje_alumnos_prioritarios', models.DecimalField(
                    decimal_places=2,
                    default=0,
                    help_text='% de alumnos prioritarios sobre matrícula total (para reporte SEP)',
                    max_digits=5,
                )),
                ('umbral_inasistencia_alerta', models.PositiveSmallIntegerField(
                    default=3,
                    help_text='Número de inasistencias consecutivas que activa una alerta temprana',
                )),
                ('umbral_notas_alerta', models.DecimalField(
                    decimal_places=1,
                    default=4.0,
                    help_text='Promedio mínimo; si el alumno baja de este valor se genera alerta',
                    max_digits=4,
                )),
                ('actualizado_en', models.DateTimeField(auto_now=True)),
                ('colegio', models.OneToOneField(
                    help_text='Establecimiento al que aplica esta configuración',
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='configuracion_academica',
                    to='institucion.colegio',
                )),
                ('actualizado_por', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='configuraciones_actualizadas',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'verbose_name': 'Configuración Académica',
                'verbose_name_plural': 'Configuraciones Académicas',
                'db_table': 'configuracion_academica',
            },
        ),
    ]
