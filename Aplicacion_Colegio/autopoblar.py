"""
============================================================
SCRIPT DE AUTOPOBLADO PARA SISTEMA DE GESTIÓN ESCOLAR
FASE 3 - Domain Redesign: Ciclos Académicos y Estados Explícitos
============================================================

DATOS DE INICIO DE SESIÓN (USUARIOS DE PRUEBA):

⚠️  CONTRASEÑAS SEGURAS IMPLEMENTADAS (Mínimo 12 caracteres, símbolos, mayúsculas, números)

1) Administrador General
   Usuario (RUT): 12.345.678-5
   Email: carlos.perez@colegio.cl
   Contraseña: Admin#2025*Seg!

2) Administrador Escolar
   Usuario (RUT): 20.111.333-6
   Email: maria.lopez@colegio.cl
   Contraseña: Escolar@2025#!

3) Profesor
   Usuario (RUT): 18.222.444-1
   Email: javier.torres@colegio.cl
   Contraseña: Prof*2025&Seg!

4) Apoderado
   Usuario (RUT): 15.555.666-7
   Email: carmen.silva@gmail.com
   Contraseña: Apod#2025!Seg*
   (Apoderado principal de 2 estudiantes)

5) Asesor Financiero
   Usuario (RUT): 19.888.999-3
   Email: laura.mendez@colegio.cl
   Contraseña: Finan#2025$Seg!
   (Acceso completo al módulo financiero)

6) Coordinador Académico
    Usuario (RUT): 21.123.456-7
    Email: paula.rios@colegio.cl
    Contraseña: Coord#2025!Seg

7) Inspector Convivencia
    Usuario (RUT): 22.234.567-8
    Email: oscar.leiva@colegio.cl
    Contraseña: Insp#2025!Seg+

8) Psicólogo Orientador
    Usuario (RUT): 23.345.678-9
    Email: daniela.reyes@colegio.cl
    Contraseña: Psico#2025!Seg

9) Soporte Técnico Escolar
    Usuario (RUT): 24.456.789-0
    Email: nicolas.araya@colegio.cl
    Contraseña: Soport#2025!Seg

10) Bibliotecario Digital
    Usuario (RUT): 25.567.890-1
    Email: elena.poblete@colegio.cl
    Contraseña: Biblio#2025!Seg

11) Alumno (Ejemplo: Ana González)
   Email: alumno1@colegio.cl
   RUT: 26.000.000-0
   Contraseña: Estud#2025*[N]  (donde [N] es el número del alumno 01-30)
   Ejemplos:
   - alumno1: Estud#2025*01!
   - alumno2: Estud#2025*02!
   (30 alumnos disponibles: alumno1@colegio.cl hasta alumno30@colegio.cl)

* NOTA IMPORTANTE DE SEGURIDAD:
  - ✅ Todas las contraseñas cumplen con los requisitos de seguridad:
    * Mínimo 12 caracteres
    * Incluyen mayúsculas, minúsculas, números y símbolos
    * No contienen secuencias comunes ni palabras prohibidas
  - ✅ Las contraseñas están hasheadas con Django's make_password (bcrypt/PBKDF2)
  - ⚠️  CAMBIAR ESTAS CONTRASEÑAS INMEDIATAMENTE EN PRODUCCIÓN
  - ⚠️  Este es solo un entorno de desarrollo/testing

* NUEVAS CARACTERÍSTICAS (FASE 3):
  - ✅ Ciclos Académicos: Concepto temporal fundamental (2025-2026)
  - ✅ Estados Explícitos: Transiciones validadas para matrículas
  - ✅ Constraints BD: Validaciones preventivas a nivel de base de datos
  - ✅ Audit Trails: Trazabilidad completa de cambios
  - ✅ Matrículas Mejoradas: Con ciclo académico y estados

EJECUCIÓN:
  python autopoblar.py
============================================================
"""

import os
import sys
import django
import random
from datetime import datetime, time, timedelta, date

# Configurar Django con nueva estructura backend.apps
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.apps.core.settings')
django.setup()

from django.contrib.auth.hashers import make_password
from django.utils import timezone
from backend.apps.accounts.models import (
    Role, User, DisponibilidadProfesor, PerfilProfesor, PerfilEstudiante,
    Apoderado, RelacionApoderadoEstudiante, FirmaDigitalApoderado, PerfilAsesorFinanciero
)
from backend.apps.institucion.models import (
    Region, Comuna, TipoEstablecimiento, DependenciaAdministrativa,
    NivelEducativo, TipoInfraestructura, Colegio, ColegioInfraestructura,
    Infraestructura, CicloAcademico  # Usar la versión de institucion (la que usa Curso)
)
from backend.apps.cursos.models import Curso, Asignatura, Clase, BloqueHorario
from backend.apps.matriculas.models import Matricula, Cuota, Pago, EstadoCuenta, Beca
from backend.apps.academico.models import (
    Evaluacion, Calificacion, Asistencia, Tarea, EntregaTarea,
    MaterialClase, Planificacion
)
from backend.apps.comunicados.models import Comunicado
from backend.apps.mensajeria.models import Anuncio, Conversacion, Mensaje
from backend.apps.notificaciones.models import Notificacion
from backend.apps.subscriptions.models import Plan, Subscription

# NUEVOS MODELOS FASE 3
from backend.apps.core.models import CambioEstado
from backend.apps.matriculas.models import EstadoMatricula, MatriculaMejorada, CambioEstadoMatricula
# CicloAcademico se importa desde institucion.models para consistencia

def limpiar_base_datos():
    """Limpiar base de datos de forma segura - solo eliminar datos de tablas que existen"""
    print("\n" + "="*60)
    print("🗑️  VERIFICANDO ESTADO DE BASE DE DATOS...")
    print("="*60 + "\n")

    from django.db import connection

    cursor = connection.cursor()

    # Desactivar restricciones de claves foráneas en SQLite para este borrado
    cursor.execute("PRAGMA foreign_keys = OFF;")

    # Verificar qué tablas existen realmente
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tablas_existentes = {row[0] for row in cursor.fetchall()}

    print(f"📊 Total de tablas en base de datos: {len(tablas_existentes)}")

    # Tablas que NO queremos eliminar (sistema Django/infraestructura)
    tablas_sistema = {
        'django_migrations', 'sqlite_sequence', 'django_content_type',
        'auth_permission', 'auth_group', 'auth_group_permissions',
        'django_session',
        # Tablas de capabilities/roles se limpian pero los roles se re-crean
        # Las capabilities del sistema se mantienen para no perder la configuración
    }

    # Orden de borrado: tablas hijas (con FK) primero, tablas padre al final
    tablas_ordenadas = [
        # M2M / tablas de relación puras
        'estado_matricula_transiciones_posibles',
        'user_groups',
        'user_user_permissions',
        # Capabilities y roles del sistema (se vuelven a crear con la migración)
        'role_capability',
        # Registros de auditoría y acceso
        'axes_accessattempt',
        'axes_accessattemptexpiration',
        'axes_accessfailurelog',
        'axes_accesslog',
        'auditoria_evento',
        'auditoria_configuracion',
        'django_admin_log',
        'usage_log',
        # Relaciones entre entidades
        'relacion_apoderado_estudiante',
        'firma_digital_apoderado',
        'comunicado_cursos_destinatarios',
        'comunicados_estadisticacomunicado',
        'comunicados_adjuntocomunicado',
        'comunicados_plantillacomunicado',
        'confirmacion_lectura',
        'anuncio_leido_por',
        'clase_estudiante',
        # Datos académicos detalle
        'entrega_tarea',
        'calificacion',
        'asistencia',
        'anotacion_convivencia',
        'justificativo_inasistencia',
        'entrevista_orientacion',
        'derivacion_externa',
        'planificacion_actividad',
        'planificacion_evaluacion',
        'planificacion_objetivo',
        'planificacion_recurso',
        # Financiero
        'detalle_informe_academico',
        'pago',
        'cuota',
        'boleta',
        'estado_cuenta',
        'beca',
        'informe_academico',
        # Soporte / Biblioteca
        'ticket_soporte',
        'prestamo_recurso',
        'recurso_digital',
        # Mensajería / notificaciones
        'mensaje',
        'conversacion',
        'notificacion',
        'preferencia_notificacion',
        'dispositivo_movil',
        # Contenido académico
        'cambio_estado_matricula',
        'matricula_mejorada',
        'matricula',
        'material_clase',
        'tarea',
        'evaluacion',
        'planificacion',
        'comunicado',
        'anuncio',
        # Perfiles de usuario
        'perfil_asesor_financiero',
        'perfil_estudiante',
        'perfil_profesor',
        'disponibilidad_profesor',
        'apoderado',
        # Estructura académica
        'clase',
        'asignatura',
        'bloque_horario',
        'curso',
        # Suscripciones
        'subscription',
        'plan',
        # Ciclos / estados
        'cambio_estado_ciclo',
        'ciclo_academico',
        'estado_matricula',
        # Estructura institucional
        'colegio_infraestructura',
        'infraestructura',
        'colegio',
        'comuna',
        'region',
        'nivel_educativo',
        'dependencia_administrativa',
        'tipo_establecimiento',
        'tipo_infraestructura',
        # Usuarios y roles (al final porque muchas tablas los referencian)
        'user',
        'role',
    ]

    total_registros_eliminados = 0

    for tabla in tablas_ordenadas:
        if tabla in tablas_existentes and tabla not in tablas_sistema:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM \"{tabla}\"")
                count = cursor.fetchone()[0]
                if count > 0:
                    cursor.execute(f"DELETE FROM \"{tabla}\"")
                    print(f"  ✓ {tabla}: {count} registros eliminados")
                    total_registros_eliminados += count
                else:
                    print(f"  ⏭️  {tabla}: tabla vacía")
            except Exception as e:
                print(f"  ⚠️  {tabla}: error al limpiar - {str(e)}")

    # Resetear secuencias de auto-incremento
    for tabla in tablas_ordenadas:
        if tabla in tablas_existentes:
            try:
                cursor.execute("DELETE FROM sqlite_sequence WHERE name=?", [tabla])
            except Exception:
                pass

    # Reactivar restricciones de claves foráneas
    cursor.execute("PRAGMA foreign_keys = ON;")

    # Hacer commit explícito de todos los cambios
    connection.commit()

    # Cerrar la conexión para que el ORM abra una conexión fresca con autocommit correcto
    # Esto evita problemas de visibilidad de las transacciones al cambiar entre raw SQL y ORM
    cursor.close()
    connection.close()

    print(f"\n✅ Limpieza completada - Total registros eliminados: {total_registros_eliminados}\n")

def poblar_roles():
    """Crear roles del sistema"""
    print("📋 Creando Roles...")
    roles_data = [
        'Administrador general',
        'Administrador escolar',
        'Profesor',
        'Apoderado',
        'Alumno',
        'Asesor financiero',
        'Coordinador académico',
        'Inspector convivencia',
        'Psicólogo orientador',
        'Soporte técnico escolar',
        'Bibliotecario digital',
    ]

    for nombre in roles_data:
        role, created = Role.objects.get_or_create(nombre=nombre)
        if created:
            print(f"  ✓ Rol: {nombre}")
        else:
            print(f"  ⏭️  Rol ya existe: {nombre}")

    print("✅ Roles creados\n")

def poblar_regiones_comunas():
    """Crear regiones y comunas de Chile"""
    print("🗺️  Creando Regiones y Comunas...")

    regiones_data = {
        'Región Metropolitana': ['Santiago', 'Maipú', 'Las Condes', 'Providencia', 'La Florida', 'Puente Alto', 'Ñuñoa', 'Vitacura'],
        'Valparaíso': ['Valparaíso', 'Viña del Mar', 'Quilpué', 'Villa Alemana', 'San Antonio'],
        'Biobío': ['Concepción', 'Talcahuano', 'Los Ángeles', 'Chillán', 'Coronel'],
        'Araucanía': ['Temuco', 'Villarrica', 'Angol', 'Pucón', 'Lautaro'],
        'Los Lagos': ['Puerto Montt', 'Osorno', 'Castro', 'Ancud', 'Puerto Varas']
    }

    for region_nombre, comunas in regiones_data.items():
        region, created = Region.objects.get_or_create(nombre=region_nombre)
        if created:
            print(f"  ✓ Región: {region_nombre}")
        else:
            print(f"  ⏭️  Región ya existe: {region_nombre}")

        for comuna_nombre in comunas:
            comuna, created = Comuna.objects.get_or_create(
                nombre=comuna_nombre,
                region=region
            )
            if created:
                print(f"    → Comuna: {comuna_nombre}")
            else:
                print(f"    ⏭️  Comuna ya existe: {comuna_nombre}")

    print("✅ Regiones y Comunas creadas\n")

def poblar_catalogos():
    """Crear catálogos de clasificación"""
    print("📚 Creando Catálogos...")

    # Tipos de Establecimiento
    print("  → Tipos de Establecimiento")
    tipos_est = ['Presencial', 'Online', 'Híbrido']
    for tipo in tipos_est:
        obj, created = TipoEstablecimiento.objects.get_or_create(nombre=tipo)
        if created:
            print(f"    ✓ {tipo}")
        else:
            print(f"    ⏭️  {tipo} ya existe")

    # Dependencias Administrativas
    print("  → Dependencias Administrativas")
    dependencias = ['Municipal', 'Particular Subvencionado', 'Particular Pagado', 'Corporación']
    for dep in dependencias:
        obj, created = DependenciaAdministrativa.objects.get_or_create(nombre=dep)
        if created:
            print(f"    ✓ {dep}")
        else:
            print(f"    ⏭️  {dep} ya existe")

    # Niveles Educativos
    print("  → Niveles Educativos")
    niveles = ['Educación Parvularia', 'Educación Básica', 'Educación Media']
    for nivel in niveles:
        obj, created = NivelEducativo.objects.get_or_create(nombre=nivel)
        if created:
            print(f"    ✓ {nivel}")
        else:
            print(f"    ⏭️  {nivel} ya existe")

    # Tipos de Infraestructura
    print("  → Tipos de Infraestructura")
    tipos_infra = [
        'Sala de Clases', 'Laboratorio de Ciencias', 'Laboratorio de Computación',
        'Biblioteca', 'Gimnasio', 'Cancha Deportiva', 'Sala de Profesores',
        'Comedor', 'Enfermería', 'Auditorio'
    ]
    for tipo in tipos_infra:
        obj, created = TipoInfraestructura.objects.get_or_create(nombre=tipo)
        if created:
            print(f"    ✓ {tipo}")
        else:
            print(f"    ⏭️  {tipo} ya existe")

    print("✅ Catálogos creados\n")

def poblar_ciclos_academicos():
    """Crear ciclos académicos para Fase 3 - Concepto temporal fundamental"""
    print("📅 Creando Ciclos Académicos (Fase 3)...")

    # Verificar si las tablas existen
    from django.db import connection
    cursor = connection.cursor()

    # Verificar tabla ciclo_academico
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ciclo_academico';")
    if not cursor.fetchone():
        print("  ⚠️  Tabla ciclo_academico no existe. Saltando creación de ciclos académicos.")
        print("  💡 Ejecuta 'python manage.py migrate core' para crear las tablas Fase 3.")
        return

    # Obtener usuario admin para audit trail
    admin_user = User.objects.filter(is_superuser=True).first()
    if not admin_user:
        print("  ❌ No se encontró usuario administrador")
        return

    # Obtener colegios
    try:
        colegio1 = Colegio.objects.get(rbd=10001)
        colegio2 = Colegio.objects.get(rbd=10002)
    except Colegio.DoesNotExist:
        print("  ❌ No se encontraron los colegios. Asegúrate de que autopoblar.py se ejecutó completamente primero.")
        return

    ciclos_data = [
        {
            'colegio': colegio1,
            'nombre': '2025-2026',
            'fecha_inicio': date(2025, 3, 1),
            'fecha_fin': date(2026, 12, 31),
            'estado': 'ACTIVO',
            'periodos_config': {
                "periodos": [
                    {
                        "nombre": "Primer Semestre 2025",
                        "inicio": "2025-03-01",
                        "fin": "2025-07-31"
                    },
                    {
                        "nombre": "Segundo Semestre 2025",
                        "inicio": "2025-08-01",
                        "fin": "2025-12-20"
                    },
                    {
                        "nombre": "Primer Semestre 2026",
                        "inicio": "2026-03-01",
                        "fin": "2026-07-31"
                    },
                    {
                        "nombre": "Segundo Semestre 2026",
                        "inicio": "2026-08-01",
                        "fin": "2026-12-20"
                    }
                ]
            }
        },
        {
            'colegio': colegio2,
            'nombre': '2025-2026',
            'fecha_inicio': date(2025, 3, 1),
            'fecha_fin': date(2026, 12, 31),
            'estado': 'ACTIVO',
            'periodos_config': {
                "periodos": [
                    {
                        "nombre": "Primer Semestre 2025",
                        "inicio": "2025-03-01",
                        "fin": "2025-07-31"
                    },
                    {
                        "nombre": "Segundo Semestre 2025",
                        "inicio": "2025-08-01",
                        "fin": "2025-12-20"
                    },
                    {
                        "nombre": "Primer Semestre 2026",
                        "inicio": "2026-03-01",
                        "fin": "2026-07-31"
                    },
                    {
                        "nombre": "Segundo Semestre 2026",
                        "inicio": "2026-08-01",
                        "fin": "2026-12-20"
                    }
                ]
            }
        }
    ]

    for data in ciclos_data:
        ciclo, created = CicloAcademico.objects.get_or_create(
            colegio=data['colegio'],
            nombre=data['nombre'],
            defaults={
                'fecha_inicio': data['fecha_inicio'],
                'fecha_fin': data['fecha_fin'],
                'estado': data['estado'],
                'periodos_config': data['periodos_config'],
                'creado_por': admin_user,
                'modificado_por': admin_user
            }
        )

        if created:
            print(f"  ✅ Creado ciclo: {ciclo.nombre} para {ciclo.colegio.nombre}")
        else:
            print(f"  ⏭️  Ciclo ya existe: {ciclo.nombre} para {ciclo.colegio.nombre}")

    print("✅ Ciclos Académicos creados\n")

def poblar_estados_matricula():
    """Crear estados de matrícula con transiciones para Fase 3"""
    print("🏷️  Creando Estados de Matrícula (Fase 3)...")

    # Verificar si las tablas existen
    from django.db import connection
    cursor = connection.cursor()

    # Verificar tabla estado_matricula
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='estado_matricula';")
    if not cursor.fetchone():
        print("  ⚠️  Tabla estado_matricula no existe. Saltando creación de estados.")
        print("  💡 Ejecuta 'python manage.py migrate core' para crear las tablas Fase 3.")
        return

    estados_data = [
        {
            'nombre': 'PREMATRICULA',
            'descripcion': 'Estudiante en proceso de pre-matrícula',
            'es_activo': False,
            'permite_cambios': True,
            'requiere_documentacion': True,
            'orden': 1
        },
        {
            'nombre': 'MATRICULADO',
            'descripcion': 'Estudiante matriculado, pendiente de activación',
            'es_activo': False,
            'permite_cambios': True,
            'requiere_documentacion': False,
            'orden': 2
        },
        {
            'nombre': 'ACTIVO',
            'descripcion': 'Estudiante activo en el ciclo académico',
            'es_activo': True,
            'permite_cambios': True,
            'requiere_documentacion': False,
            'orden': 3
        },
        {
            'nombre': 'INACTIVO_TEMPORAL',
            'descripcion': 'Estudiante inactivo temporalmente',
            'es_activo': False,
            'permite_cambios': True,
            'requiere_documentacion': False,
            'orden': 4
        },
        {
            'nombre': 'SUSPENDIDO',
            'descripcion': 'Estudiante suspendido por razones disciplinarias',
            'es_activo': False,
            'permite_cambios': True,
            'requiere_documentacion': True,
            'orden': 5
        },
        {
            'nombre': 'RETIRADO',
            'descripcion': 'Estudiante retirado del establecimiento',
            'es_activo': False,
            'permite_cambios': False,
            'requiere_documentacion': True,
            'orden': 6
        },
        {
            'nombre': 'GRADUADO',
            'descripcion': 'Estudiante graduado del nivel educativo',
            'es_activo': False,
            'permite_cambios': False,
            'requiere_documentacion': False,
            'orden': 7
        },
        {
            'nombre': 'CERRADO',
            'descripcion': 'Matrícula cerrada permanentemente',
            'es_activo': False,
            'permite_cambios': False,
            'requiere_documentacion': False,
            'orden': 8
        }
    ]

    estados_creados = []
    for estado_data in estados_data:
        estado, created = EstadoMatricula.objects.get_or_create(
            nombre=estado_data['nombre'],
            defaults=estado_data
        )

        if created:
            estados_creados.append(estado.nombre)
            print(f"  ✅ Creado estado: {estado.nombre}")
        else:
            print(f"  ⏭️  Estado ya existe: {estado.nombre}")

    # Configurar transiciones válidas
    print("  🔗 Configurando transiciones entre estados...")

    transiciones = {
        'PREMATRICULA': ['MATRICULADO', 'RETIRADO'],
        'MATRICULADO': ['ACTIVO', 'RETIRADO'],
        'ACTIVO': ['INACTIVO_TEMPORAL', 'SUSPENDIDO', 'RETIRADO', 'GRADUADO'],
        'INACTIVO_TEMPORAL': ['ACTIVO', 'RETIRADO'],
        'SUSPENDIDO': ['ACTIVO', 'RETIRADO'],
        'RETIRADO': ['CERRADO'],  # Estado final
        'GRADUADO': ['CERRADO'],  # Estado final
        'CERRADO': []  # Estado final absoluto
    }

    for estado_origen_nombre, estados_destino_nombres in transiciones.items():
        try:
            estado_origen = EstadoMatricula.objects.get(nombre=estado_origen_nombre)

            for estado_destino_nombre in estados_destino_nombres:
                estado_destino = EstadoMatricula.objects.get(nombre=estado_destino_nombre)
                estado_origen.transiciones_posibles.add(estado_destino)
                print(f"    ✓ {estado_origen_nombre} → {estado_destino_nombre}")

        except EstadoMatricula.DoesNotExist as e:
            print(f"    ❌ Error configurando transición: {e}")

    print(f"✅ Estados de Matrícula creados: {len(estados_creados)}\n")

def poblar_colegios():
    """Crear colegios de prueba"""
    print("🏫 Creando Colegios...")
    
    santiago = Comuna.objects.get(nombre='Santiago')
    vina = Comuna.objects.get(nombre='Viña del Mar')
    
    presencial = TipoEstablecimiento.objects.get(nombre='Presencial')
    municipal = DependenciaAdministrativa.objects.get(nombre='Municipal')
    particular_sub = DependenciaAdministrativa.objects.get(nombre='Particular Subvencionado')
    
    colegios_data = [
        {
            'rbd': 10001,
            'rut_establecimiento': '76.123.456-7',
            'nombre': 'Colegio Santa María',
            'direccion': 'Av. Libertador Bernardo O\'Higgins 1234',
            'telefono': '+56 2 2234 5678',
            'correo': 'contacto@santamaria.cl',
            'web': 'www.santamaria.cl',
            'capacidad_maxima': 1200,
            'fecha_fundacion': datetime(1980, 3, 15).date(),
            'comuna': santiago,
            'tipo_establecimiento': presencial,
            'dependencia': particular_sub
        },
        {
            'rbd': 10002,
            'rut_establecimiento': '76.234.567-8',
            'nombre': 'Liceo Técnico Industrial',
            'direccion': 'Calle Principal 567',
            'telefono': '+56 32 2987 6543',
            'correo': 'contacto@liceotecnico.cl',
            'web': 'www.liceotecnico.cl',
            'capacidad_maxima': 800,
            'fecha_fundacion': datetime(1975, 6, 20).date(),
            'comuna': vina,
            'tipo_establecimiento': presencial,
            'dependencia': municipal
        }
    ]
    
    for data in colegios_data:
        colegio, created = Colegio.objects.get_or_create(
            rbd=data['rbd'],
            defaults=data
        )
        if created:
            print(f"  ✓ {colegio.nombre} (RBD: {colegio.rbd})")
            # Agregar infraestructura al colegio
            poblar_infraestructura_colegio(colegio)
        else:
            print(f"  ⏭️  {colegio.nombre} (RBD: {colegio.rbd}) ya existe")
    
    print("✅ Colegios creados\n")

def poblar_infraestructura_colegio(colegio):
    """Agregar infraestructura a un colegio"""
    infraestructura_data = [
        ('Sala de Clases', 20),
        ('Laboratorio de Ciencias', 2),
        ('Laboratorio de Computación', 3),
        ('Biblioteca', 1),
        ('Gimnasio', 1),
        ('Cancha Deportiva', 2),
        ('Sala de Profesores', 1),
        ('Comedor', 1),
        ('Enfermería', 1),
        ('Auditorio', 1)
    ]
    
    for tipo_nombre, cantidad in infraestructura_data:
        tipo_infra = TipoInfraestructura.objects.get(nombre=tipo_nombre)
        ColegioInfraestructura.objects.create(
            colegio=colegio,
            tipo_infra=tipo_infra,
            cantidad=cantidad
        )
    
    # Crear salas específicas en el modelo Infraestructura
    for i in range(1, 21):
        Infraestructura.objects.create(
            rbd_colegio=colegio.rbd,
            nombre=f"Sala {i}",
            tipo='Sala de Clases',
            capacidad_estudiantes=45,
            piso=((i-1) // 5) + 1,
            activo=True
        )

def poblar_usuarios():
    """Crear usuarios de prueba"""
    print("👥 Creando Usuarios...")
    
    # Obtener roles
    rol_admin_general = Role.objects.get(nombre='Administrador general')
    rol_admin_escolar = Role.objects.get(nombre='Administrador escolar')
    rol_profesor = Role.objects.get(nombre='Profesor')
    rol_apoderado = Role.objects.get(nombre='Apoderado')
    rol_alumno = Role.objects.get(nombre='Alumno')
    rol_asesor_financiero = Role.objects.get(nombre='Asesor financiero')
    rol_coordinador = Role.objects.get(nombre='Coordinador académico')
    rol_inspector = Role.objects.get(nombre='Inspector convivencia')
    rol_psicologo = Role.objects.get(nombre='Psicólogo orientador')
    rol_soporte_tecnico = Role.objects.get(nombre='Soporte técnico escolar')
    rol_bibliotecario = Role.objects.get(nombre='Bibliotecario digital')
    
    # Obtener colegios
    colegio1 = Colegio.objects.get(rbd=10001)
    colegio2 = Colegio.objects.get(rbd=10002)
    
    usuarios_data = [
        # Administrador General
        {
            'email': 'carlos.perez@colegio.cl',
            'rut': '12.345.678-5',
            'nombre': 'Carlos',
            'apellido_paterno': 'Pérez',
            'apellido_materno': 'González',
            'password': make_password('Admin#2025*Seg!'),
            'role': rol_admin_general,
            'rbd_colegio': None,
            'is_staff': True,
            'is_superuser': True,
            'is_active': True
        },
        # Administrador Escolar
        {
            'email': 'maria.lopez@colegio.cl',
            'rut': '20.111.333-6',
            'nombre': 'María',
            'apellido_paterno': 'López',
            'apellido_materno': 'Martínez',
            'password': make_password('Escolar@2025#!'),
            'role': rol_admin_escolar,
            'rbd_colegio': colegio1.rbd,
            'is_staff': True,
            'is_active': True
        },
        # Asesor Financiero
        {
            'email': 'laura.mendez@colegio.cl',
            'rut': '19.888.999-3',
            'nombre': 'Laura',
            'apellido_paterno': 'Méndez',
            'apellido_materno': 'Fuentes',
            'password': make_password('Finan#2025$Seg!'),
            'role': rol_asesor_financiero,
            'rbd_colegio': colegio1.rbd,
            'is_staff': False,
            'is_active': True
        },
        {
            'email': 'paula.rios@colegio.cl',
            'rut': '21.123.456-7',
            'nombre': 'Paula',
            'apellido_paterno': 'Ríos',
            'apellido_materno': 'Soto',
            'password': make_password('Coord#2025!Seg'),
            'role': rol_coordinador,
            'rbd_colegio': colegio1.rbd,
            'is_staff': True,
            'is_active': True
        },
        {
            'email': 'oscar.leiva@colegio.cl',
            'rut': '22.234.567-8',
            'nombre': 'Óscar',
            'apellido_paterno': 'Leiva',
            'apellido_materno': 'Moreno',
            'password': make_password('Insp#2025!Seg+'),
            'role': rol_inspector,
            'rbd_colegio': colegio1.rbd,
            'is_staff': True,
            'is_active': True
        },
        {
            'email': 'daniela.reyes@colegio.cl',
            'rut': '23.345.678-9',
            'nombre': 'Daniela',
            'apellido_paterno': 'Reyes',
            'apellido_materno': 'Vera',
            'password': make_password('Psico#2025!Seg'),
            'role': rol_psicologo,
            'rbd_colegio': colegio1.rbd,
            'is_staff': True,
            'is_active': True
        },
        {
            'email': 'nicolas.araya@colegio.cl',
            'rut': '24.456.789-0',
            'nombre': 'Nicolás',
            'apellido_paterno': 'Araya',
            'apellido_materno': 'Pino',
            'password': make_password('Soport#2025!Seg'),
            'role': rol_soporte_tecnico,
            'rbd_colegio': colegio1.rbd,
            'is_staff': True,
            'is_active': True
        },
        {
            'email': 'elena.poblete@colegio.cl',
            'rut': '25.567.890-1',
            'nombre': 'Elena',
            'apellido_paterno': 'Poblete',
            'apellido_materno': 'Hidalgo',
            'password': make_password('Biblio#2025!Seg'),
            'role': rol_bibliotecario,
            'rbd_colegio': colegio1.rbd,
            'is_staff': True,
            'is_active': True
        },
    ]
    
    # Profesores - Uno por cada asignatura (9 profesores)
    profesores_data = [
        {'nombre': 'Javier', 'apellido': 'Torres', 'email': 'javier.torres@colegio.cl', 'rut': '18.222.444-1'},
        {'nombre': 'Lucía', 'apellido': 'Ramírez', 'email': 'lucia.ramirez@colegio.cl', 'rut': '17.333.555-2'},
        {'nombre': 'Roberto', 'apellido': 'Silva', 'email': 'roberto.silva@colegio.cl', 'rut': '16.444.666-3'},
        {'nombre': 'Patricia', 'apellido': 'González', 'email': 'patricia.gonzalez@colegio.cl', 'rut': '16.234.567-8'},
        {'nombre': 'Diego', 'apellido': 'Morales', 'email': 'diego.morales@colegio.cl', 'rut': '15.123.456-9'},
        {'nombre': 'Carmen', 'apellido': 'Vega', 'email': 'carmen.vega@colegio.cl', 'rut': '14.987.654-3'},
        {'nombre': 'Andrés', 'apellido': 'Pinto', 'email': 'andres.pinto@colegio.cl', 'rut': '13.456.789-0'},
        {'nombre': 'Francisca', 'apellido': 'Rojas', 'email': 'francisca.rojas@colegio.cl', 'rut': '12.789.012-4'},
        {'nombre': 'Manuel', 'apellido': 'Castro', 'email': 'manuel.castro@colegio.cl', 'rut': '11.234.567-5'},
    ]
    
    for i, prof in enumerate(profesores_data, 1):
        usuarios_data.append({
            'email': prof['email'],
            'rut': prof['rut'],
            'nombre': prof['nombre'],
            'apellido_paterno': prof['apellido'],
            'apellido_materno': 'Docente',
            'password': make_password('Prof*2025&Seg!'),
            'role': rol_profesor,
            'rbd_colegio': colegio1.rbd,
            'is_active': True
        })
    
    # Apoderados - 15 apoderados para los 30 estudiantes (algunos con múltiples hijos)
    apoderados_data = [
        {'nombre': 'Carmen', 'apellido': 'Silva', 'email': 'carmen.silva@gmail.com', 'rut': '15.555.666-7'},
        {'nombre': 'Roberto', 'apellido': 'Muñoz', 'email': 'roberto.munoz@gmail.com', 'rut': '14.666.777-8'},
        {'nombre': 'Patricia', 'apellido': 'Díaz', 'email': 'patricia.diaz@gmail.com', 'rut': '13.777.888-9'},
        {'nombre': 'Fernando', 'apellido': 'Rojas', 'email': 'fernando.rojas@gmail.com', 'rut': '16.888.999-0'},
        {'nombre': 'Gloria', 'apellido': 'Pérez', 'email': 'gloria.perez@gmail.com', 'rut': '15.999.000-1'},
        {'nombre': 'Jorge', 'apellido': 'Fuentes', 'email': 'jorge.fuentes@gmail.com', 'rut': '14.000.111-2'},
        {'nombre': 'Rosa', 'apellido': 'Contreras', 'email': 'rosa.contreras@gmail.com', 'rut': '13.111.222-3'},
        {'nombre': 'Luis', 'apellido': 'Sepúlveda', 'email': 'luis.sepulveda@gmail.com', 'rut': '16.222.333-4'},
        {'nombre': 'Mónica', 'apellido': 'Morales', 'email': 'monica.morales@gmail.com', 'rut': '15.333.444-5'},
        {'nombre': 'Andrés', 'apellido': 'Vega', 'email': 'andres.vega@gmail.com', 'rut': '14.444.555-6'},
        {'nombre': 'Elena', 'apellido': 'Álvarez', 'email': 'elena.alvarez@gmail.com', 'rut': '13.555.666-7'},
        {'nombre': 'Ricardo', 'apellido': 'Soto', 'email': 'ricardo.soto@gmail.com', 'rut': '16.666.777-8'},
        {'nombre': 'Claudia', 'apellido': 'Torres', 'email': 'claudia.torres@gmail.com', 'rut': '15.777.888-9'},
        {'nombre': 'Marcelo', 'apellido': 'González', 'email': 'marcelo.gonzalez@gmail.com', 'rut': '14.888.999-0'},
        {'nombre': 'Verónica', 'apellido': 'Rodríguez', 'email': 'veronica.rodriguez@gmail.com', 'rut': '13.999.000-1'},
    ]
    
    for apod in apoderados_data:
        usuarios_data.append({
            'email': apod['email'],
            'rut': apod['rut'],
            'nombre': apod['nombre'],
            'apellido_paterno': apod['apellido'],
            'apellido_materno': 'Apoderado',
            'password': make_password('Apod#2025!Seg*'),
            'role': rol_apoderado,
            'rbd_colegio': colegio1.rbd,
            'is_active': True
        })
    
    # Alumnos - 30 estudiantes para 1° Medio A
    nombres_masculinos = ['Pedro', 'Diego', 'Matías', 'Sebastián', 'Felipe', 'Tomás', 'Nicolás', 'Martín', 'Joaquín', 'Benjamín', 'Lucas', 'Cristóbal', 'Gabriel', 'Maximiliano', 'Vicente']
    nombres_femeninos = ['Ana', 'Sofía', 'Valentina', 'Camila', 'Fernanda', 'Catalina', 'Javiera', 'Isidora', 'Amanda', 'Carolina', 'Daniela', 'Francisca', 'Victoria', 'Antonia', 'Constanza']
    apellidos = ['González', 'Rodríguez', 'Muñoz', 'Rojas', 'Díaz', 'Pérez', 'Fuentes', 'Contreras', 'Silva', 'Sepúlveda', 'Morales', 'Vega', 'Álvarez', 'Soto', 'Torres']
    
    # Combinar nombres (15 hombres + 15 mujeres)
    alumnos_nombres = nombres_masculinos + nombres_femeninos
    
    for i in range(30):
        # Generar RUTs realistas: 26.000.000-0 hasta 26.000.029-9
        rut_numero = 26000000 + i
        # Calcular dígito verificador simple (módulo 10)
        dv = (10 - (rut_numero % 10)) % 10
        usuarios_data.append({
            'email': f'alumno{i+1}@colegio.cl',
            'rut': f'{rut_numero//1000000}.{(rut_numero%1000000)//1000:03d}.{rut_numero%1000:03d}-{dv}',
            'nombre': alumnos_nombres[i],
            'apellido_paterno': apellidos[i % 15],
            'apellido_materno': apellidos[(i + 7) % 15],
            'password': make_password(f'Estud#2025*{i+1:02d}!'),
            'role': rol_alumno,
            'rbd_colegio': colegio1.rbd,
            'is_active': True
        })
    
    for data in usuarios_data:
        try:
            usuario, created = User.objects.get_or_create(
                email=data['email'],
                defaults=data
            )
            if created and usuario:
                print(f"  ✓ {usuario.get_full_name()} - {usuario.role.nombre} ({usuario.email})")
            elif usuario:
                print(f"  ⏭️  {usuario.get_full_name()} - {usuario.role.nombre} ({usuario.email}) ya existe")
            else:
                print(f"  ❌ Error al procesar usuario: {data['email']}")
        except Exception as e:
            print(f"  ❌ Error creando usuario {data['email']}: {str(e)}")
            # Intentar crear sin get_or_create como fallback
            try:
                usuario = User.objects.create(**data)
                print(f"  ✓ {usuario.get_full_name()} - {usuario.role.nombre} ({usuario.email}) [fallback]")
            except Exception as e2:
                print(f"  ❌ Error en fallback para {data['email']}: {str(e2)}")
    
    print("✅ Usuarios creados\n")

def poblar_cursos_asignaturas():
    """Crear cursos y asignaturas"""
    print("📖 Creando Cursos y Asignaturas...")
    
    colegio = Colegio.objects.get(rbd=10001)
    ciclo = CicloAcademico.objects.get(colegio=colegio, nombre='2025-2026')
    nivel_basica = NivelEducativo.objects.get(nombre='Educación Básica')
    nivel_media = NivelEducativo.objects.get(nombre='Educación Media')
    
    # Crear Cursos - 1° a 8° Básico y 1° a 4° Medio (sección A)
    print("  → Cursos")
    cursos_data = []
    
    # Básica: 1° a 8°
    for grado in range(1, 9):
        cursos_data.append({
            'nombre': f'{grado}° Básico A',
            'nivel': nivel_basica
        })
    
    # Media: 1° a 4°
    for grado in range(1, 5):
        cursos_data.append({
            'nombre': f'{grado}° Medio A',
            'nivel': nivel_media
        })
    
    for data in cursos_data:
        curso, created = Curso.objects.get_or_create(
            colegio=colegio,
            nombre=data['nombre'],
            nivel=data['nivel'],
            ciclo_academico=ciclo,
            defaults={'activo': True}
        )
        if created:
            print(f"    ✓ {curso.nombre}")
        else:
            print(f"    ⏭️  {curso.nombre} ya existe")
    
    # Crear Asignaturas
    print("  → Asignaturas")
    asignaturas_data = [
        {'nombre': 'Lenguaje y Comunicación', 'codigo': 'LEN', 'horas': 6},
        {'nombre': 'Matemática', 'codigo': 'MAT', 'horas': 6},
        {'nombre': 'Ciencias Naturales', 'codigo': 'CIE', 'horas': 4},
        {'nombre': 'Historia, Geografía y Ciencias Sociales', 'codigo': 'HIS', 'horas': 4},
        {'nombre': 'Inglés', 'codigo': 'ING', 'horas': 3},
        {'nombre': 'Artes Visuales', 'codigo': 'ART', 'horas': 2},
        {'nombre': 'Música', 'codigo': 'MUS', 'horas': 2},
        {'nombre': 'Educación Física', 'codigo': 'EFI', 'horas': 2},
        {'nombre': 'Tecnología', 'codigo': 'TEC', 'horas': 2},
    ]
    
    for data in asignaturas_data:
        asignatura, created = Asignatura.objects.get_or_create(
            colegio=colegio,
            nombre=data['nombre'],
            defaults={
                'codigo': data['codigo'],
                'horas_semanales': data['horas'],
                'activa': True
            }
        )
        if created:
            print(f"    ✓ {asignatura.nombre} ({asignatura.codigo}) - Color: {asignatura.color}")
        else:
            print(f"    ⏭️  {asignatura.nombre} ({asignatura.codigo}) ya existe")
    
    print("✅ Cursos y Asignaturas creados\n")

def poblar_clases():
    """Asignar profesores a cursos y asignaturas (crear clases)"""
    print("🎓 Creando Clases (Asignaciones Curso+Asignatura+Profesor)...")
    
    colegio = Colegio.objects.get(rbd=10001)
    
    # Obtener los 9 profesores
    profesores = list(User.objects.filter(
        rbd_colegio=colegio.rbd,
        role__nombre='Profesor',
        is_active=True
    ).order_by('email'))
    
    prof1, prof2, prof3, prof4, prof5, prof6, prof7, prof8, prof9 = profesores[:9]
    
    # Obtener todos los cursos
    cursos = Curso.objects.filter(colegio=colegio, activo=True).order_by('nombre')
    
    # Obtener asignaturas
    matematica = Asignatura.objects.get(nombre='Matemática', colegio=colegio)
    lenguaje = Asignatura.objects.get(nombre='Lenguaje y Comunicación', colegio=colegio)
    ciencias = Asignatura.objects.get(nombre='Ciencias Naturales', colegio=colegio)
    historia = Asignatura.objects.get(nombre='Historia, Geografía y Ciencias Sociales', colegio=colegio)
    ingles = Asignatura.objects.get(nombre='Inglés', colegio=colegio)
    ed_fisica = Asignatura.objects.get(nombre='Educación Física', colegio=colegio)
    artes = Asignatura.objects.get(nombre='Artes Visuales', colegio=colegio)
    musica = Asignatura.objects.get(nombre='Música', colegio=colegio)
    tecnologia = Asignatura.objects.get(nombre='Tecnología', colegio=colegio)
    
    # Asignación 1:1 profesor-asignatura
    # Un profesor por asignatura para todos los cursos
    asignaciones = [
        (matematica, prof1),     # Javier Torres
        (lenguaje, prof2),       # Lucía Ramírez
        (ciencias, prof3),       # Roberto Silva
        (historia, prof4),       # Patricia González
        (ingles, prof5),         # Diego Morales
        (artes, prof6),          # Carmen Vega
        (musica, prof7),         # Andrés Pinto
        (ed_fisica, prof8),      # Francisca Rojas
        (tecnologia, prof9),     # Manuel Castro
    ]
    
    # Crear clases para cada curso con cada asignatura
    for curso in cursos:
        for asignatura, profesor in asignaciones:
            clase, created = Clase.objects.get_or_create(
                colegio=colegio,
                curso=curso,
                asignatura=asignatura,
                profesor=profesor,
                defaults={'activo': True}
            )
            if created:
                print(f"  ✓ {clase.curso.nombre} - {clase.asignatura.nombre} ({clase.profesor.get_full_name()})")
            else:
                print(f"  ⏭️  {clase.curso.nombre} - {clase.asignatura.nombre} ya existe")
    
    print("✅ Clases creadas\n")

def poblar_horarios():
    """Crear algunos horarios de ejemplo (el resto se puede asignar automáticamente)"""
    print("⏰ Creando Horarios de Ejemplo (Bloques)...")
    
    colegio = Colegio.objects.get(rbd=10001)
    
    # Obtener algunas clases para crear horarios de ejemplo (solo 1° Básico A)
    clases_1basico = Clase.objects.filter(
        curso__nombre='1° Básico A',
        colegio=colegio,
        activo=True
    ).select_related('asignatura')
    
    # Horarios: Lunes a Viernes, 8 bloques por día
    # Bloque 1: 08:00-08:45
    # Bloque 2: 09:00-09:45
    # Bloque 3: 10:00-10:45
    # Bloque 4: 11:00-11:45
    # Bloque 5: 12:00-12:45 (Almuerzo)
    # Bloque 6: 13:45-14:30
    # Bloque 7: 14:45-15:30
    # Bloque 8: 15:45-16:30
    
    horarios_bloques = [
        (time(8, 0), time(8, 45)),
        (time(9, 0), time(9, 45)),
        (time(10, 0), time(10, 45)),
        (time(11, 0), time(11, 45)),
        (time(12, 0), time(12, 45)),
        (time(13, 45), time(14, 30)),
        (time(14, 45), time(15, 30)),
        (time(15, 45), time(16, 30)),
    ]
    
    # Crear un horario de ejemplo para 1° Básico A (solo algunos bloques)
    # El resto se puede asignar con el botón de asignación automática
    bloques_ejemplo = [
        # Lunes
        {'dia': 1, 'bloque': 1, 'asignatura': 'Matemática'},
        {'dia': 1, 'bloque': 2, 'asignatura': 'Lenguaje y Comunicación'},
        {'dia': 1, 'bloque': 3, 'asignatura': 'Ciencias Naturales'},
        
        # Martes
        {'dia': 2, 'bloque': 1, 'asignatura': 'Lenguaje y Comunicación'},
        {'dia': 2, 'bloque': 2, 'asignatura': 'Matemática'},
        
        # Miércoles
        {'dia': 3, 'bloque': 1, 'asignatura': 'Historia, Geografía y Ciencias Sociales'},
        {'dia': 3, 'bloque': 2, 'asignatura': 'Inglés'},
    ]
    
    for bloque_data in bloques_ejemplo:
        clase = clases_1basico.filter(asignatura__nombre=bloque_data['asignatura']).first()
        if clase:
            hora_inicio, hora_fin = horarios_bloques[bloque_data['bloque'] - 1]
            bloque = BloqueHorario.objects.create(
                colegio=colegio,
                clase=clase,
                dia_semana=bloque_data['dia'],
                bloque_numero=bloque_data['bloque'],
                hora_inicio=hora_inicio,
                hora_fin=hora_fin,
                activo=True
            )
            dia_nombre = dict(BloqueHorario.DIAS_SEMANA)[bloque_data['dia']]
            print(f"  ✓ {dia_nombre} - Bloque {bloque_data['bloque']} ({hora_inicio}-{hora_fin}): {bloque.clase.asignatura.nombre} - {bloque.clase.curso.nombre}")
    
    print("✅ Horarios de ejemplo creados")
    print("   💡 Usa el botón 'Asignar Automáticamente' para completar el resto\n")

def poblar_matriculas():
    """Matricular los 30 alumnos en 1° Medio A usando modelo Matricula estándar"""
    print("📝 Creando Matrículas para 1° Medio A...")

    colegio = Colegio.objects.get(rbd=10001)
    ciclo = CicloAcademico.objects.get(colegio=colegio, nombre='2025-2026')

    # Obtener curso 1° Medio A
    try:
        curso = Curso.objects.get(
            colegio=colegio,
            nombre='1° Medio A',
            ciclo_academico=ciclo
        )
    except Curso.DoesNotExist:
        print("  ❌ No se encontró el curso 1° Medio A")
        return

    # Eliminar matrículas existentes para evitar duplicados con estado incorrecto
    Matricula.objects.filter(
        estudiante__rbd_colegio=colegio.rbd,
        ciclo_academico=ciclo
    ).delete()
    print("  🗑️  Matrículas existentes eliminadas")

    # Obtener TODOS los alumnos activos
    alumnos = User.objects.filter(
        rbd_colegio=colegio.rbd,
        role__nombre__in=['Estudiante', 'Alumno'],
        is_active=True
    ).order_by('email')

    matriculas_creadas = 0
    for i, alumno in enumerate(alumnos, 1):
        # Crear matrícula estándar
        matricula, created = Matricula.objects.get_or_create(
            estudiante=alumno,
            colegio=colegio,
            ciclo_academico=ciclo,  # ✅ Usar ciclo_academico en lugar de anio_escolar
            defaults={
                'curso': curso,
                'estado': 'ACTIVA',
                'fecha_matricula': timezone.now().date(),
                'fecha_inicio': ciclo.fecha_inicio,
                'valor_matricula': 150000,
                'observaciones': f"Matrícula automática generada por autopoblar.py"
            }
        )

        if created:
            print(f"  ✓ {alumno.get_full_name()} → {curso.nombre}")
            matriculas_creadas += 1
        else:
            print(f"  ⏭️  Matrícula ya existe: {alumno.get_full_name()}")

    print(f"✅ {matriculas_creadas} matrículas creadas para {len(alumnos)} alumnos\n")

def poblar_matriculas_clases():
    """
    Matricular estudiantes en clases específicas (relación ClaseEstudiante).
    Vincula cada estudiante matriculado en un curso con todas las clases de ese curso.
    """
    print("📚 Creando relaciones Estudiante-Clase (ClaseEstudiante)...")
    
    from backend.apps.cursos.models import ClaseEstudiante
    
    colegio = Colegio.objects.get(rbd=10001)
    ciclo = CicloAcademico.objects.get(colegio=colegio, nombre='2025-2026')
    
    # Eliminar relaciones existentes para evitar duplicados
    ClaseEstudiante.objects.filter(
        clase__colegio=colegio
    ).delete()
    print("  🗑️  Relaciones ClaseEstudiante existentes eliminadas")
    
    # Obtener todas las matrículas activas
    matriculas = Matricula.objects.filter(
        colegio=colegio,
        ciclo_academico=ciclo,
        estado='ACTIVA'
    ).select_related('estudiante', 'curso')
    
    print(f"  📝 Procesando {matriculas.count()} matrículas activas...")
    
    relaciones_creadas = 0
    for matricula in matriculas:
        # Obtener todas las clases del curso
        clases_del_curso = Clase.objects.filter(
            curso=matricula.curso,
            colegio=colegio,
            activo=True
        )
        
        # Matricular al estudiante en cada clase
        for clase in clases_del_curso:
            ClaseEstudiante.objects.create(
                clase=clase,
                estudiante=matricula.estudiante,
                activo=True
            )
            relaciones_creadas += 1
        
        print(f"  ✓ {matricula.estudiante.get_full_name()} → {clases_del_curso.count()} clases de {matricula.curso.nombre}")
    
    print(f"✅ {relaciones_creadas} relaciones ClaseEstudiante creadas\n")

def poblar_perfiles_profesores():
    """Crear perfiles de profesores con sus especialidades"""
    print("👨‍🏫 Creando Perfiles de Profesores...")
    
    # Esta función se puede implementar si se necesitan datos adicionales de profesores
    print("  ℹ️  Perfiles de profesores básicos ya creados con usuarios\n")

def poblar_perfil_asesor_financiero():
    """Crear perfil de asesor financiero"""
    print("💰 Creando Perfil de Asesor Financiero...")
    
    # Obtener el usuario asesor financiero
    try:
        asesor = User.objects.get(email='laura.mendez@colegio.cl')
        
        # Crear perfil de asesor financiero
        perfil = PerfilAsesorFinanciero.objects.create(
            user=asesor,
            area_especialidad='finanzas',
            titulo_profesional='Contador Auditor',
            registro_profesional='N° 12345 - Colegio de Contadores',
            puede_aprobar_descuentos=True,
            puede_anular_pagos=False,
            puede_modificar_aranceles=True,
            puede_generar_reportes_contables=True,
            acceso_configuracion_transbank=False,
            telefono_oficina='+56 2 2234 5690',
            extension='105',
            horario_atencion='Lunes a Viernes 9:00-17:00',
            fecha_ingreso=datetime(2024, 1, 15).date(),
            estado_laboral='Activo',
            notas_internas='Asesor financiero principal. Responsable de gestión de pagos, estados de cuenta y reportes contables.'
        )
        
        print(f"  ✓ {asesor.get_full_name()} - Área: {perfil.get_area_especialidad_display()}")
        print(f"    → Permisos: Descuentos={perfil.puede_aprobar_descuentos}, Aranceles={perfil.puede_modificar_aranceles}, Reportes={perfil.puede_generar_reportes_contables}")
        print("✅ Perfil de Asesor Financiero creado\n")
    except User.DoesNotExist:
        print("  ⚠ Usuario asesor financiero no encontrado\n")

def poblar_perfiles_estudiantes():
    """Crear perfiles de estudiantes con datos NEE"""
    print("👥 Creando Perfiles de Estudiantes...")
    
    colegio = Colegio.objects.get(rbd=10001)
    ciclo = CicloAcademico.objects.get(colegio=colegio, nombre='2025-2026')
    curso_1medio = Curso.objects.get(nombre='1° Medio A', colegio=colegio, ciclo_academico=ciclo)
    
    # Obtener los 30 alumnos
    alumnos = list(User.objects.filter(
        rbd_colegio=colegio.rbd,
        role__nombre__in=['Estudiante', 'Alumno'],
        is_active=True
    ).order_by('email'))
    
    # Grupos sanguíneos para variar
    grupos_sanguineos = ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-']
    
    # Datos NEE para algunos estudiantes (~20% = 6 estudiantes)
    nee_data = [
        {'tipo': 'TEA', 'descripcion': 'Trastorno del Espectro Autista nivel 1. Requiere apoyo en interacción social y comunicación.', 'pie': True},
        {'tipo': 'TDAH', 'descripcion': 'Trastorno por Déficit de Atención e Hiperactividad. Dificultad para mantener la concentración.', 'pie': True},
        {'tipo': 'Dislexia', 'descripcion': 'Dificultad específica en el aprendizaje de la lectura. Requiere material adaptado.', 'pie': True},
        {'tipo': 'Discalculia', 'descripcion': 'Dificultad específica en el aprendizaje de las matemáticas.', 'pie': True},
        {'tipo': 'Déficit Atencional', 'descripcion': 'Déficit atencional sin hiperactividad. Requiere ubicación preferencial en sala.', 'pie': False},
        {'tipo': 'Dislexia leve', 'descripcion': 'Dislexia de grado leve. Requiere tiempo adicional en evaluaciones de lectura.', 'pie': False},
    ]
    
    for i, alumno in enumerate(alumnos):
        # Fecha de nacimiento: estudiantes de 1° Medio tienen ~15 años (nacidos en 2010)
        fecha_nac = datetime(2010, random.randint(1, 12), random.randint(1, 28)).date()
        
        # Asignar NEE a algunos estudiantes (primeros 6)
        tiene_nee = i < 6
        nee_info = nee_data[i] if tiene_nee else None
        
        # Crear perfil
        perfil = PerfilEstudiante.objects.create(
            user=alumno,
            fecha_nacimiento=fecha_nac,
            direccion=f'Calle {random.randint(100, 999)}, Santiago',
            telefono=f'+56 9 {random.randint(1000, 9999)} {random.randint(1000, 9999)}',
            grupo_sanguineo=random.choice(grupos_sanguineos),
            alergias='Ninguna' if random.random() > 0.2 else random.choice(['Polen', 'Maní', 'Lactosa', 'Ninguna']),
            # Datos NEE
            tiene_nee=tiene_nee,
            tipo_nee=nee_info['tipo'] if nee_info else None,
            descripcion_nee=nee_info['descripcion'] if nee_info else None,
            requiere_pie=nee_info['pie'] if nee_info else False,
            # Datos académicos
            fecha_ingreso=datetime(2024, 3, 1).date(),
            estado_academico='Activo',
            ciclo_actual=ciclo,
            # Nota: curso_actual es una propiedad calculada desde la matrícula, no se asigna aquí
            # Datos apoderado
            apoderado_nombre=f'{random.choice(["Sr.", "Sra."])} {random.choice(["Carlos", "María", "José", "Ana"])} {alumno.apellido_paterno}',
            apoderado_rut=f'{random.randint(10, 25)}.{random.randint(100, 999)}.{random.randint(100, 999)}-{random.randint(0, 9)}',
            apoderado_email=f'apoderado.{alumno.email.split("@")[0]}@gmail.com',
            apoderado_telefono=f'+56 9 {random.randint(1000, 9999)} {random.randint(1000, 9999)}'
        )
        
        nee_str = f' [NEE: {nee_info["tipo"]}]' if tiene_nee else ''
        print(f'  ✓ {alumno.get_full_name()} → 1° Medio A{nee_str}')
    
    print(f'✅ Perfiles creados (6 estudiantes con NEE)\n')

def poblar_disponibilidades_profesores():
    """Crear disponibilidades horarias para los profesores"""
    print("📅 Creando Disponibilidades de Profesores...")
    
    # Obtener todos los profesores
    rol_profesor = Role.objects.get(nombre='Profesor')
    profesores = User.objects.filter(role=rol_profesor)
    
    # Horarios de bloques (mismo esquema que bloques horarios)
    horarios_bloques = [
        (time(8, 0), time(8, 45)),
        (time(9, 0), time(9, 45)),
        (time(10, 0), time(10, 45)),
        (time(11, 0), time(11, 45)),
        (time(12, 0), time(12, 45)),
        (time(13, 45), time(14, 30)),
        (time(14, 45), time(15, 30)),
        (time(15, 45), time(16, 30)),
    ]
    
    for profesor in profesores:
        # Crear perfil de profesor si no existe
        perfil, created = PerfilProfesor.objects.get_or_create(
            user=profesor,
            defaults={
                'estado_laboral': 'Activo',
                'horas_semanales_contrato': 44,
                'horas_no_lectivas': 10,
                'fecha_ingreso': datetime(2020, 3, 1).date()
            }
        )
        
        if created:
            print(f"  ✓ Perfil creado para {profesor.get_full_name()}")
        
        # Crear disponibilidad para cada profesor (Lunes a Viernes, 8 bloques)
        # Ejemplo: Javier Torres solo tiene disponibilidad de 14:00 a 17:00 Lunes a Miércoles
        # (bloques 6, 7, 8 de lunes, martes y miércoles)
        # Los demás profesores tienen disponibilidad completa excepto almuerzo
        
        # Configuración especial para Javier Torres (primer profesor)
        if profesor.email == 'javier.torres@colegio.cl':
            bloques_disponibles_javier = [
                (1, 6), (1, 7), (1, 8),  # Lunes 13:45-16:30
                (2, 6), (2, 7), (2, 8),  # Martes 13:45-16:30
                (3, 6), (3, 7), (3, 8),  # Miércoles 13:45-16:30
            ]
            
            for dia in range(1, 6):  # Lunes a Viernes
                for bloque in range(1, 9):  # 8 bloques
                    hora_inicio, hora_fin = horarios_bloques[bloque - 1]
                    disponible = (dia, bloque) in bloques_disponibles_javier
                    
                    DisponibilidadProfesor.objects.create(
                        profesor=profesor,
                        dia_semana=dia,
                        bloque_numero=bloque,
                        hora_inicio=hora_inicio,
                        hora_fin=hora_fin,
                        disponible=disponible,
                        observaciones='Horario restringido: 14:00-16:30 L-M-X' if not disponible else None
                    )
            
            print(f"  ✓ Disponibilidad creada para {profesor.get_full_name()} (solo 14:00-16:30 L-M-X)")
        else:
            # Disponibilidad estándar para otros profesores (todo excepto almuerzo)
            bloques_no_disponibles = [
                (1, 5),  # Lunes bloque 5 (almuerzo)
                (2, 5),  # Martes bloque 5
                (3, 5),  # Miércoles bloque 5
                (4, 5),  # Jueves bloque 5
                (5, 5),  # Viernes bloque 5
            ]
            
            for dia in range(1, 6):  # Lunes a Viernes
                for bloque in range(1, 9):  # 8 bloques
                    hora_inicio, hora_fin = horarios_bloques[bloque - 1]
                    disponible = (dia, bloque) not in bloques_no_disponibles
                    
                    DisponibilidadProfesor.objects.create(
                        profesor=profesor,
                        dia_semana=dia,
                        bloque_numero=bloque,
                        hora_inicio=hora_inicio,
                        hora_fin=hora_fin,
                        disponible=disponible,
                        observaciones='Almuerzo' if bloque == 5 else None
                    )
            
            print(f"  ✓ Disponibilidad creada para {profesor.get_full_name()} (35/40 bloques)")
    
    print("✅ Disponibilidades creadas\n")

def poblar_evaluaciones_calificaciones():
    """Crear evaluaciones y calificaciones para 1° Medio A"""
    print("📊 Creando Evaluaciones y Calificaciones...")
    
    colegio = Colegio.objects.get(rbd=10001)
    curso_1medio = Curso.objects.get(nombre='1° Medio A', colegio=colegio)
    
    # Obtener todas las clases de 1° Medio A
    clases = Clase.objects.filter(curso=curso_1medio, activo=True).select_related('asignatura', 'profesor')
    
    # Obtener estudiantes del curso
    estudiantes = User.objects.filter(
        rbd_colegio=colegio.rbd,
        role__nombre__in=['Estudiante', 'Alumno'],
        perfil_estudiante__ciclo_actual=curso_1medio.ciclo_academico
    )
    
    tipos_evaluacion = ['Prueba', 'Control', 'Trabajo Práctico', 'Disertación', 'Proyecto']
    tipos_modelo = ['sumativa', 'formativa', 'diagnostica', 'acumulativa']

    def inferir_periodo(fecha_evaluacion):
        if fecha_evaluacion.month <= 6:
            return 'semestre1'
        return 'semestre2'
    
    for clase in clases:
        # Crear 3-4 evaluaciones por asignatura
        num_evaluaciones = random.randint(3, 4)
        
        for i in range(1, num_evaluaciones + 1):
            # Fecha de evaluación en los últimos 2 meses
            fecha_eval = timezone.now().date() - timedelta(days=random.randint(7, 60))
            
            tipo = random.choice(tipos_evaluacion)
            ponderacion = random.choice([10, 15, 20, 25, 30])
            tipo_modelo = random.choice(tipos_modelo)
            
            evaluacion = Evaluacion.objects.create(
                colegio=colegio,
                clase=clase,
                nombre=f"{tipo} {i} - {clase.asignatura.nombre}",
                fecha_evaluacion=fecha_eval,
                ponderacion=ponderacion,
                periodo=inferir_periodo(fecha_eval),
                tipo_evaluacion=tipo_modelo,
                es_recuperacion=random.random() < 0.1,
                activa=True
            )
            
            # Crear calificaciones para cada estudiante
            for estudiante in estudiantes:
                # Generar nota aleatoria entre 4.0 y 7.0 (más probabilidad de notas altas)
                nota_base = random.uniform(4.5, 7.0)
                
                # Estudiantes con NEE pueden tener notas más variables
                if hasattr(estudiante, 'perfil_estudiante') and estudiante.perfil_estudiante.tiene_nee:
                    nota_base = random.uniform(4.0, 6.5)
                
                nota_final = round(nota_base, 1)
                
                Calificacion.objects.create(
                    colegio=colegio,
                    evaluacion=evaluacion,
                    estudiante=estudiante,
                    nota=nota_final,
                    registrado_por=clase.profesor
                )
            
            print(f"  ✓ {evaluacion.nombre} - {clase.curso.nombre} ({len(estudiantes)} calificaciones)")
    
    print("✅ Evaluaciones y Calificaciones creadas\n")

def poblar_asistencia():
    """Crear registros de asistencia para los últimos 60 días con patrones realistas"""
    print("📅 Creando Registros de Asistencia (últimos 60 días)...")
    
    colegio = Colegio.objects.get(rbd=10001)
    
    # Obtener TODAS las clases activas del colegio
    clases = Clase.objects.filter(
        colegio=colegio,
        activo=True
    ).select_related('asignatura', 'profesor', 'curso', 'curso__ciclo_academico')
    
    print(f"  → Generando asistencia para {len(clases)} clases")
    
    # Agrupar estudiantes por curso/ciclo para eficiencia
    estudiantes_por_curso = {}
    for clase in clases:
        curso = clase.curso
        if curso.pk not in estudiantes_por_curso:
            estudiantes_por_curso[curso.pk] = list(User.objects.filter(
                rbd_colegio=colegio.rbd,
                role__nombre__in=['Estudiante', 'Alumno'],
                perfil_estudiante__ciclo_actual=curso.ciclo_academico
            ))
    
    total_estudiantes = sum(len(est) for est in estudiantes_por_curso.values())
    print(f"  → {total_estudiantes} estudiantes en total")
    
    # Crear asistencia para los últimos 30 días hábiles
    dias_atras = 30
    registros_creados = 0
    dias_procesados = 0
    
    for dias in range(dias_atras, 0, -1):
        fecha = timezone.now().date() - timedelta(days=dias)
        
        # Solo días de semana (lunes a viernes)
        if fecha.weekday() >= 5:  # 5=sábado, 6=domingo
            continue
        
        dias_procesados += 1
        
        # Para TODAS las clases (simular 1 clase por día por asignatura)
        for clase in clases:
            estudiantes = estudiantes_por_curso[clase.curso.pk]
            for estudiante in estudiantes:
                # Patrones realistas de asistencia
                # 92% presente, 4% tardanza, 2% ausente, 2% justificada
                rand = random.random()
                
                if rand < 0.92:
                    estado = 'P'  # Presente
                    observaciones = None
                elif rand < 0.96:
                    estado = 'T'  # Tardanza
                    observaciones = random.choice([None, 'Problema de transporte', 'Trámite médico'])
                elif rand < 0.98:
                    estado = 'A'  # Ausente
                    observaciones = None
                else:
                    estado = 'J'  # Justificada
                    observaciones = random.choice([
                        'Certificado médico',
                        'Terapia PIE',
                        'Trámite familiar',
                        'Control de salud'
                    ])
                
                # Estudiantes con NEE tienen más ausencias justificadas
                if hasattr(estudiante, 'perfil_estudiante') and estudiante.perfil_estudiante.tiene_nee:
                    if random.random() < 0.08:  # 8% adicional de ausencias justificadas
                        estado = 'J'
                        observaciones = 'Terapia PIE' if not observaciones else observaciones
                
                Asistencia.objects.create(
                    colegio=colegio,
                    clase=clase,
                    estudiante=estudiante,
                    fecha=fecha,
                    estado=estado,
                    observaciones=observaciones
                )
                registros_creados += 1
    
    print(f"  ✓ {registros_creados} registros de asistencia creados")
    print(f"  ✓ {dias_procesados} días hábiles procesados")
    print(f"  ✓ {len(clases)} clases con asistencia")
    promedio = (registros_creados / total_estudiantes) if total_estudiantes > 0 else 0
    print(f"  ✓ Promedio: {promedio:.0f} registros por estudiante")
    print("✅ Registros de Asistencia creados para TODOS los cursos\n")

def poblar_tareas():
    """Crear tareas y algunas entregas"""
    print("📝 Creando Tareas y Entregas...")
    
    colegio = Colegio.objects.get(rbd=10001)
    curso_1medio = Curso.objects.get(nombre='1° Medio A', colegio=colegio)
    
    # Obtener clases
    clases = Clase.objects.filter(curso=curso_1medio, activo=True).select_related('asignatura', 'profesor')
    
    # Obtener estudiantes
    estudiantes = list(User.objects.filter(
        rbd_colegio=colegio.rbd,
        role__nombre__in=['Estudiante', 'Alumno'],
        perfil_estudiante__ciclo_actual=curso_1medio.ciclo_academico
    ))
    
    tareas_creadas = 0
    entregas_creadas = 0
    
    for clase in clases:
        # 2-3 tareas por clase
        num_tareas = random.randint(2, 3)
        
        for i in range(1, num_tareas + 1):
            # Algunas tareas pasadas, algunas futuras
            dias_offset = random.randint(-15, 15)
            fecha_entrega = timezone.now() + timedelta(days=dias_offset)
            
            es_pasada = dias_offset < 0
            
            tarea = Tarea.objects.create(
                colegio=colegio,
                clase=clase,
                titulo=f"Tarea {i} - {clase.asignatura.nombre}",
                instrucciones=f"Realizar ejercicios del capítulo {i}. Entregar en formato PDF o Word.",
                fecha_entrega=fecha_entrega,
                es_publica=True,
                creada_por=clase.profesor
            )
            tareas_creadas += 1
            
            # Si la tarea ya venció, crear entregas para ~80% de estudiantes
            if es_pasada:
                num_entregas = int(len(estudiantes) * random.uniform(0.75, 0.95))
                estudiantes_entregan = random.sample(estudiantes, num_entregas)
                
                for estudiante in estudiantes_entregan:
                    # Fecha de entrega entre la creación y el vencimiento (o un poco después)
                    dias_entrega = random.randint(dias_offset - 5, dias_offset + 2)
                    fecha_entrega_real = timezone.now() + timedelta(days=dias_entrega)
                    
                    # Algunos entregarán tarde
                    entrega_tardia = fecha_entrega_real > tarea.fecha_entrega
                    estado = 'tarde' if entrega_tardia else 'revisada'
                    
                    # 70% de las entregas ya tienen calificación
                    tiene_calificacion = random.random() > 0.3
                    
                    EntregaTarea.objects.create(
                        tarea=tarea,
                        estudiante=estudiante,
                        comentario_estudiante="Adjunto mi tarea completada.",
                        calificacion=round(random.uniform(5.0, 7.0), 1) if tiene_calificacion else None,
                        retroalimentacion="Buen trabajo" if not entrega_tardia else "Entrega tardía" if tiene_calificacion else None,
                        estado=estado if not tiene_calificacion else 'revisada',
                        revisada_por=clase.profesor if tiene_calificacion else None
                    )
                    entregas_creadas += 1
            
            print(f"  ✓ {tarea.titulo} - {clase.curso.nombre}")
    
    print(f"  ✓ {tareas_creadas} tareas y {entregas_creadas} entregas creadas")
    print("✅ Tareas y Entregas creadas\n")

def poblar_materiales():
    """Crear materiales de clase"""
    print("📚 Creando Materiales de Clase...")
    
    colegio = Colegio.objects.get(rbd=10001)
    curso_1medio = Curso.objects.get(nombre='1° Medio A', colegio=colegio)
    
    # Obtener clases
    clases = Clase.objects.filter(curso=curso_1medio, activo=True).select_related('asignatura', 'profesor')
    
    tipos_material = ['PDF', 'Presentación', 'Video', 'Documento']
    materiales_creados = 0
    
    for clase in clases:
        # 2-4 materiales por clase
        num_materiales = random.randint(2, 4)
        
        for i in range(1, num_materiales + 1):
            tipo = random.choice(tipos_material)
            
            MaterialClase.objects.create(
                colegio=colegio,
                clase=clase,
                titulo=f"Material {i} - {clase.asignatura.nombre}",
                descripcion=f"Material de estudio para {clase.asignatura.nombre}",
                archivo=f"materiales/ejemplo_{tipo}_{i}.pdf",  # Archivo ficticio
                tipo_archivo=tipo,
                es_publico=True,
                subido_por=clase.profesor,
                tamanio_bytes=random.randint(50000, 5000000)  # Entre 50KB y 5MB
            )
            materiales_creados += 1
    
    print(f"  ✓ {materiales_creados} materiales creados")
    print("✅ Materiales de Clase creados\n")

def poblar_anuncios():
    """Crear anuncios en las clases"""
    print("📢 Creando Anuncios...")
    
    colegio = Colegio.objects.get(rbd=10001)
    curso_1medio = Curso.objects.get(nombre='1° Medio A', colegio=colegio)
    
    # Obtener clases
    clases = Clase.objects.filter(curso=curso_1medio, activo=True).select_related('asignatura', 'profesor')
    
    anuncios_tipos = [
        ("Cambio de Horario", "Se informa que la clase del viernes se adelantará al jueves."),
        ("Material Disponible", "Ya está disponible el material de estudio para la próxima evaluación."),
        ("Recordatorio Evaluación", "Recuerden que la próxima semana tendremos evaluación."),
        ("Tarea Adicional", "Se asigna tarea adicional para reforzar los contenidos vistos."),
        ("Felicitaciones", "¡Excelente trabajo en la última actividad! Sigan así."),
    ]
    
    anuncios_creados = 0
    
    for clase in clases:
        # 1-2 anuncios por clase
        num_anuncios = random.randint(1, 2)
        
        for _ in range(num_anuncios):
            titulo, contenido = random.choice(anuncios_tipos)
            fecha = timezone.now() - timedelta(days=random.randint(1, 20))
            
            Anuncio.objects.create(
                clase=clase,
                autor=clase.profesor,
                titulo=titulo,
                contenido=contenido,
                anclado=random.random() < 0.2  # 20% anclados
            )
            anuncios_creados += 1
    
    print(f"  ✓ {anuncios_creados} anuncios creados")
    print("✅ Anuncios creados\n")

def poblar_comunicados():
    """Crear comunicados para el curso"""
    print("📨 Creando Comunicados...")
    
    colegio = Colegio.objects.get(rbd=10001)
    curso_1medio = Curso.objects.get(nombre='1° Medio A', colegio=colegio)
    
    # Admin escolar como autor
    admin_escolar = User.objects.get(email='maria.lopez@colegio.cl')
    
    comunicados_data = [
        {
            'titulo': 'Reunión de Apoderados',
            'contenido': 'Se les convoca a reunión de apoderados el próximo viernes 15 de diciembre a las 19:00 hrs. Es importante su asistencia.',
            'tipo': 'citacion',
            'es_prioritario': True
        },
        {
            'titulo': 'Suspensión de Clases',
            'contenido': 'Se informa que el lunes 18 de diciembre no habrá clases por actividad interna del establecimiento.',
            'tipo': 'urgente',
            'es_prioritario': True
        },
        {
            'titulo': 'Horario de Verano',
            'contenido': 'A partir del 1 de enero, el horario de atención será de 9:00 a 13:00 hrs.',
            'tipo': 'comunicado',
            'es_prioritario': False
        },
        {
            'titulo': 'Materiales para el próximo año',
            'contenido': 'Ya está disponible la lista de útiles escolares para el año 2026 en la página web del colegio.',
            'tipo': 'noticia',
            'es_prioritario': False
        },
    ]
    
    comunicados_creados = 0
    
    for comm_data in comunicados_data:
        comunicado = Comunicado.objects.create(
            colegio=colegio,
            publicado_por=admin_escolar,
            titulo=comm_data['titulo'],
            contenido=comm_data['contenido'],
            tipo=comm_data['tipo'],
            destinatario='curso_especifico',
            es_prioritario=comm_data['es_prioritario'],
            requiere_confirmacion=random.random() < 0.5
        )
        
        # Asignar a curso específico
        comunicado.cursos_destinatarios.add(curso_1medio)
        comunicados_creados += 1
    
    print(f"  ✓ {comunicados_creados} comunicados creados")
    print("✅ Comunicados creados\n")


def poblar_notificaciones():
    """Crear notificaciones reales en la tabla Notificacion + ajustar escenarios de mensajeria."""
    print("🔔 Creando Notificaciones del sistema...")

    colegio = Colegio.objects.get(rbd=10001)
    curso_1medio = Curso.objects.get(nombre='1° Medio A', colegio=colegio)
    clase = (
        Clase.objects.filter(curso=curso_1medio, activo=True)
        .select_related('profesor', 'asignatura')
        .first()
    )
    if not clase or not clase.profesor:
        print("  ⚠️  No se encontro clase/profesor para crear escenarios de notificacion")
        print("✅ Escenarios de Notificaciones ajustados\n")
        return

    estudiante_rel = (
        clase.estudiantes.select_related('estudiante')
        .filter(activo=True)
        .first()
    )
    if not estudiante_rel:
        print("  ⚠️  No se encontro estudiante en la clase para escenario de mensajeria")
        print("✅ Escenarios de Notificaciones ajustados\n")
        return

    estudiante = estudiante_rel.estudiante
    profesor = clase.profesor

    # Forzar al menos una tarea y una evaluacion para "hoy"
    tarea_hoy = Tarea.objects.filter(clase=clase, activa=True).order_by('fecha_entrega').first()
    if tarea_hoy:
        tarea_hoy.fecha_entrega = timezone.make_aware(datetime.combine(date.today(), time(18, 0)))
        tarea_hoy.save(update_fields=['fecha_entrega'])

    evaluacion_hoy = Evaluacion.objects.filter(clase=clase, activa=True).order_by('fecha_evaluacion').first()
    if evaluacion_hoy:
        evaluacion_hoy.fecha_evaluacion = date.today()
        evaluacion_hoy.save(update_fields=['fecha_evaluacion'])

    conversacion, _created = Conversacion.objects.get_or_create(
        clase=clase,
        participante1=profesor,
        participante2=estudiante,
    )

    Mensaje.objects.create(
        conversacion=conversacion,
        emisor=profesor,
        receptor=estudiante,
        contenido='Recuerda revisar la tarea y prepararte para la evaluacion de hoy.',
    )
    Mensaje.objects.create(
        conversacion=conversacion,
        emisor=estudiante,
        receptor=profesor,
        contenido='Profesor, ya subi mi tarea. Quedo atento a comentarios.',
    )

    # ─── Crear Notificaciones reales en la BD ───────────────────────────────
    now = timezone.now()

    # Obtener usuarios clave del colegio
    admin_escolar = User.objects.filter(email='maria.lopez@colegio.cl').first()
    apoderado = User.objects.filter(email='carmen.silva@gmail.com').first()
    asesor_fin = User.objects.filter(email='laura.mendez@colegio.cl').first()
    coordinador = User.objects.filter(email='paula.rios@colegio.cl').first()
    admin_gral = User.objects.filter(email='carlos.perez@colegio.cl').first()

    # Obtener algunos estudiantes mas
    estudiantes = list(User.objects.filter(
        rbd_colegio=colegio.rbd,
        role__nombre__in=['Estudiante', 'Alumno'],
        is_active=True,
    ).order_by('email')[:5])

    notifs_creadas = 0

    # ── BATCH: Notificaciones para el PROFESOR ──────────────────────────────
    notifs_profesor = [
        {
            'tipo': 'tarea_entregada',
            'titulo': f'{estudiante.nombre} entregó tarea de {clase.asignatura.nombre}',
            'mensaje': f'El estudiante {estudiante.nombre} {estudiante.apellido_paterno} entregó la tarea "{tarea_hoy.titulo if tarea_hoy else "Actividad"}" a tiempo.',
            'prioridad': 'normal',
            'leido': False,
            'fecha_creacion': now - timedelta(minutes=15),
        },
        {
            'tipo': 'evaluacion',
            'titulo': 'Recordatorio: Evaluación programada hoy',
            'mensaje': f'Tienes una evaluación programada hoy para {clase.asignatura.nombre} en {curso_1medio.nombre}.',
            'enlace': '/profesor/evaluaciones',
            'prioridad': 'alta',
            'leido': False,
            'fecha_creacion': now - timedelta(hours=2),
        },
        {
            'tipo': 'mensaje_nuevo',
            'titulo': 'Nuevo mensaje de estudiante',
            'mensaje': f'{estudiante.nombre} {estudiante.apellido_paterno} te envió un mensaje sobre la tarea pendiente.',
            'prioridad': 'normal',
            'leido': True,
            'fecha_creacion': now - timedelta(hours=5),
        },
        {
            'tipo': 'asistencia',
            'titulo': 'Asistencia pendiente de registro',
            'mensaje': f'Falta registrar asistencia de hoy para {curso_1medio.nombre} - {clase.asignatura.nombre}.',
            'enlace': '/profesor/asistencias',
            'prioridad': 'alta',
            'leido': False,
            'fecha_creacion': now - timedelta(hours=1),
        },
        {
            'tipo': 'sistema',
            'titulo': 'Planificación semanal pendiente',
            'mensaje': 'Recuerda completar la planificación de clases para la próxima semana.',
            'prioridad': 'baja',
            'leido': True,
            'fecha_creacion': now - timedelta(days=1),
        },
        {
            'tipo': 'comunicado_nuevo',
            'titulo': 'Nuevo comunicado de dirección',
            'mensaje': 'La dirección ha publicado un comunicado sobre actualización de protocolos de evaluación.',
            'prioridad': 'normal',
            'leido': False,
            'fecha_creacion': now - timedelta(days=2),
        },
    ]

    for n in notifs_profesor:
        fecha = n.pop('fecha_creacion')
        obj = Notificacion(**n, destinatario=profesor)
        obj.save()
        Notificacion.objects.filter(pk=obj.pk).update(fecha_creacion=fecha)
        notifs_creadas += 1

    # ── BATCH: Notificaciones para ESTUDIANTES ──────────────────────────────
    notifs_estudiante_tpl = [
        {
            'tipo': 'calificacion',
            'titulo': f'Nueva calificación en {clase.asignatura.nombre}',
            'mensaje': 'Tu profesor ha registrado una nueva calificación. Revisa tu libreta de notas.',
            'enlace': '/estudiante/panel',
            'prioridad': 'normal',
            'leido': False,
            'delta': timedelta(hours=3),
        },
        {
            'tipo': 'tarea_nueva',
            'titulo': f'Nueva tarea: {tarea_hoy.titulo if tarea_hoy else "Ejercicios semana"}',
            'mensaje': f'Se ha asignado una nueva tarea en {clase.asignatura.nombre}. Fecha de entrega: hoy.',
            'enlace': '/estudiante/panel',
            'prioridad': 'alta',
            'leido': False,
            'delta': timedelta(hours=6),
        },
        {
            'tipo': 'evaluacion',
            'titulo': 'Evaluación programada para hoy',
            'mensaje': f'Recuerda que hoy tienes evaluación en {clase.asignatura.nombre}. ¡Prepárate!',
            'prioridad': 'alta',
            'leido': False,
            'delta': timedelta(hours=8),
        },
        {
            'tipo': 'asistencia',
            'titulo': 'Registro de inasistencia',
            'mensaje': 'Se registró una inasistencia en tu historial del día de ayer. Si fue justificada, contacta a tu profesor jefe.',
            'prioridad': 'normal',
            'leido': True,
            'delta': timedelta(days=1),
        },
        {
            'tipo': 'anuncio_nuevo',
            'titulo': 'Actividad extracurricular disponible',
            'mensaje': 'Se abrieron inscripciones para el taller de robótica. Consulta los horarios en la cartelera.',
            'prioridad': 'baja',
            'leido': True,
            'delta': timedelta(days=3),
        },
    ]

    for est in estudiantes:
        for tpl in notifs_estudiante_tpl:
            delta = tpl.pop('delta')
            data = {**tpl}
            fecha = now - delta
            obj = Notificacion(**data, destinatario=est)
            obj.save()
            Notificacion.objects.filter(pk=obj.pk).update(fecha_creacion=fecha)
            notifs_creadas += 1
            tpl['delta'] = delta  # restore for next student

    # ── BATCH: Notificaciones para APODERADO ────────────────────────────────
    if apoderado:
        notifs_apoderado = [
            {
                'tipo': 'calificacion',
                'titulo': 'Nueva calificación de su hijo/a',
                'mensaje': f'Se registró una nueva calificación en {clase.asignatura.nombre}. Promedio actual: 5.8.',
                'prioridad': 'normal',
                'leido': False,
                'fecha_creacion': now - timedelta(hours=4),
            },
            {
                'tipo': 'asistencia',
                'titulo': 'Alerta de inasistencia',
                'mensaje': 'Su hijo/a registró una inasistencia ayer. Si fue justificada, envíe el justificativo.',
                'enlace': '/apoderado/panel',
                'prioridad': 'alta',
                'leido': False,
                'fecha_creacion': now - timedelta(hours=20),
            },
            {
                'tipo': 'citacion_nueva',
                'titulo': 'Citación a reunión de apoderados',
                'mensaje': 'Se le convoca a reunión general de apoderados el próximo viernes a las 18:00.',
                'prioridad': 'urgente',
                'leido': False,
                'fecha_creacion': now - timedelta(days=1),
            },
            {
                'tipo': 'comunicado_nuevo',
                'titulo': 'Circular: Uniforme escolar 2026',
                'mensaje': 'Se informa sobre los proveedores autorizados para la adquisición del uniforme escolar.',
                'prioridad': 'baja',
                'leido': True,
                'fecha_creacion': now - timedelta(days=5),
            },
            {
                'tipo': 'alerta',
                'titulo': 'Rendimiento académico bajo',
                'mensaje': 'El promedio de su hijo/a ha descendido por debajo de 4.5 en Matemáticas. Le recomendamos solicitar reforzamiento.',
                'prioridad': 'urgente',
                'leido': False,
                'fecha_creacion': now - timedelta(hours=10),
            },
        ]
        for n in notifs_apoderado:
            fecha = n.pop('fecha_creacion')
            obj = Notificacion(**n, destinatario=apoderado)
            obj.save()
            Notificacion.objects.filter(pk=obj.pk).update(fecha_creacion=fecha)
            notifs_creadas += 1

    # ── BATCH: Notificaciones para ADMIN ESCOLAR ────────────────────────────
    if admin_escolar:
        notifs_admin = [
            {
                'tipo': 'sistema',
                'titulo': 'Resumen diario del colegio',
                'mensaje': f'Hoy asistieron 28 de 30 estudiantes en {curso_1medio.nombre}. Tasa: 93.3%.',
                'prioridad': 'normal',
                'leido': False,
                'fecha_creacion': now - timedelta(hours=1),
            },
            {
                'tipo': 'alerta',
                'titulo': '2 profesores sin registrar asistencia',
                'mensaje': 'Los siguientes profesores aún no registran asistencia hoy. Verificar antes de las 14:00.',
                'prioridad': 'alta',
                'leido': False,
                'fecha_creacion': now - timedelta(hours=3),
            },
            {
                'tipo': 'evento_nuevo',
                'titulo': 'Consejo de profesores agendado',
                'mensaje': 'Se ha agendado consejo de profesores para el miércoles 09/04 a las 16:00.',
                'enlace': '/calendario/eventos',
                'prioridad': 'normal',
                'leido': True,
                'fecha_creacion': now - timedelta(days=2),
            },
            {
                'tipo': 'urgente_nuevo',
                'titulo': '⚠️ Emergencia: Corte de agua programado',
                'mensaje': 'Se informa corte de agua para mañana de 08:00 a 12:00. Tomar previsiones.',
                'prioridad': 'urgente',
                'leido': False,
                'fecha_creacion': now - timedelta(minutes=30),
            },
        ]
        for n in notifs_admin:
            fecha = n.pop('fecha_creacion')
            obj = Notificacion(**n, destinatario=admin_escolar)
            obj.save()
            Notificacion.objects.filter(pk=obj.pk).update(fecha_creacion=fecha)
            notifs_creadas += 1

    # ── BATCH: Notificaciones para ASESOR FINANCIERO ────────────────────────
    if asesor_fin:
        notifs_fin = [
            {
                'tipo': 'sistema',
                'titulo': 'Cuotas vencidas: 12 pendientes',
                'mensaje': 'Hay 12 cuotas vencidas del mes de marzo. Se recomienda enviar recordatorios.',
                'enlace': '/asesor-financiero/panel',
                'prioridad': 'alta',
                'leido': False,
                'fecha_creacion': now - timedelta(hours=6),
            },
            {
                'tipo': 'sistema',
                'titulo': 'Pago recibido: $125.000',
                'mensaje': 'Se registró un pago por transferencia bancaria de la familia González.',
                'prioridad': 'normal',
                'leido': False,
                'fecha_creacion': now - timedelta(hours=2),
            },
        ]
        for n in notifs_fin:
            fecha = n.pop('fecha_creacion')
            obj = Notificacion(**n, destinatario=asesor_fin)
            obj.save()
            Notificacion.objects.filter(pk=obj.pk).update(fecha_creacion=fecha)
            notifs_creadas += 1

    # ── BATCH: Notificaciones para COORDINADOR ACADÉMICO ────────────────────
    if coordinador:
        notifs_coord = [
            {
                'tipo': 'alerta',
                'titulo': '5 estudiantes con promedio bajo 4.0',
                'mensaje': 'Se detectaron 5 estudiantes con promedio general bajo 4.0 en el período actual.',
                'prioridad': 'alta',
                'leido': False,
                'fecha_creacion': now - timedelta(hours=4),
            },
            {
                'tipo': 'sistema',
                'titulo': 'Reporte mensual disponible',
                'mensaje': 'El reporte ministerial de marzo 2026 está listo para revisión.',
                'prioridad': 'normal',
                'leido': True,
                'fecha_creacion': now - timedelta(days=3),
            },
        ]
        for n in notifs_coord:
            fecha = n.pop('fecha_creacion')
            obj = Notificacion(**n, destinatario=coordinador)
            obj.save()
            Notificacion.objects.filter(pk=obj.pk).update(fecha_creacion=fecha)
            notifs_creadas += 1

    # ── BATCH: Notificaciones para ADMIN GENERAL ────────────────────────────
    if admin_gral:
        notifs_global = [
            {
                'tipo': 'sistema',
                'titulo': 'Suscripción próxima a vencer',
                'mensaje': 'La suscripción del Liceo Técnico Industrial (RBD 10002) vence en 7 días.',
                'prioridad': 'urgente',
                'leido': False,
                'fecha_creacion': now - timedelta(hours=12),
            },
            {
                'tipo': 'sistema',
                'titulo': 'Nuevo colegio registrado',
                'mensaje': 'Se ha registrado un nuevo colegio en la plataforma. Pendiente de activación.',
                'prioridad': 'normal',
                'leido': True,
                'fecha_creacion': now - timedelta(days=4),
            },
            {
                'tipo': 'alerta',
                'titulo': 'Intento de acceso no autorizado',
                'mensaje': 'Se detectaron 3 intentos fallidos de inicio de sesión desde IP 192.168.1.45.',
                'prioridad': 'urgente',
                'leido': False,
                'fecha_creacion': now - timedelta(hours=1),
            },
        ]
        for n in notifs_global:
            fecha = n.pop('fecha_creacion')
            obj = Notificacion(**n, destinatario=admin_gral)
            obj.save()
            Notificacion.objects.filter(pk=obj.pk).update(fecha_creacion=fecha)
            notifs_creadas += 1

    # ── Resumen ─────────────────────────────────────────────────────────────
    total_notifs = Notificacion.objects.count()
    total_unread = Notificacion.objects.filter(leido=False).count()
    print(f"  ✓ Notificaciones creadas en batch: {notifs_creadas}")
    print(f"  ✓ Total notificaciones en BD: {total_notifs}")
    print(f"  ✓ Sin leer: {total_unread}")
    print(f"  ✓ Conversacion de prueba ID: {conversacion.id_conversacion}")
    print("✅ Notificaciones del sistema creadas\n")

def poblar_apoderados():
    """Crear perfiles de apoderados y relaciones con estudiantes"""
    print("👨‍👩‍👧‍👦 Creando Perfiles de Apoderados y Relaciones...")
    
    colegio = Colegio.objects.get(rbd=10001)
    
    # Obtener usuarios apoderados
    usuarios_apoderados = list(User.objects.filter(
        rbd_colegio=colegio.rbd,
        role__nombre='Apoderado',
        is_active=True
    ).order_by('email'))
    
    # Obtener todos los estudiantes
    estudiantes = list(User.objects.filter(
        rbd_colegio=colegio.rbd,
        role__nombre__in=['Estudiante', 'Alumno'],
        is_active=True
    ).order_by('email'))
    
    # Ocupaciones de ejemplo
    ocupaciones = [
        'Ingeniero/a', 'Profesor/a', 'Médico/a', 'Contador/a', 'Empresario/a',
        'Abogado/a', 'Arquitecto/a', 'Comerciante', 'Técnico/a', 'Enfermero/a',
        'Empleado/a Público', 'Vendedor/a', 'Dueña de casa', 'Jubilado/a', 'Otro'
    ]
    
    parentescos = ['padre', 'madre', 'abuelo', 'tio', 'tutor_legal']
    
    apoderados_creados = 0
    relaciones_creadas = 0
    
    # Crear perfiles de apoderados y asignarles estudiantes
    # Estrategia: cada 2 estudiantes comparten apoderados (hermanos)
    for i, usuario_apod in enumerate(usuarios_apoderados):
        # Crear perfil de apoderado
        fecha_nac = datetime(random.randint(1970, 1990), random.randint(1, 12), random.randint(1, 28)).date()
        
        # Algunos apoderados tienen permisos restringidos
        puede_firmar = random.random() > 0.1  # 90% puede firmar
        puede_autorizar_salidas = random.random() > 0.5  # 50% puede autorizar salidas
        
        apoderado = Apoderado.objects.create(
            user=usuario_apod,
            fecha_nacimiento=fecha_nac,
            direccion=f'Av. Principal {random.randint(100, 999)}, Santiago',
            telefono=f'+56 2 {random.randint(2000, 2999)} {random.randint(1000, 9999)}',
            telefono_movil=f'+56 9 {random.randint(8000, 9999)} {random.randint(1000, 9999)}',
            ocupacion=random.choice(ocupaciones),
            lugar_trabajo=f'Empresa {random.choice(["A", "B", "C", "D"])} Ltda.',
            telefono_trabajo=f'+56 2 {random.randint(2000, 2999)} {random.randint(1000, 9999)}',
            puede_ver_notas=True,
            puede_ver_asistencia=True,
            puede_recibir_comunicados=True,
            puede_firmar_citaciones=puede_firmar,
            puede_autorizar_salidas=puede_autorizar_salidas,
            puede_ver_tareas=True,
            puede_ver_materiales=True,
            activo=True
        )
        apoderados_creados += 1
        
        # Asignar 2 estudiantes por apoderado (hermanos)
        # Los primeros 2 apoderados tienen 2 hijos, el resto tiene 2 hijos también
        estudiantes_asignados = estudiantes[i*2:(i*2)+2] if (i*2)+2 <= len(estudiantes) else estudiantes[i*2:]
        
        for j, estudiante in enumerate(estudiantes_asignados):
            # El primer hijo tiene al apoderado como principal, el segundo también
            # Pero alternamos el parentesco
            es_principal = True
            parentesco = 'madre' if i % 2 == 0 else 'padre'
            prioridad = 1
            
            relacion = RelacionApoderadoEstudiante.objects.create(
                apoderado=apoderado,
                estudiante=estudiante,
                tipo_apoderado='principal',
                parentesco=parentesco,
                prioridad_contacto=prioridad,
                activa=True,
                usar_permisos_personalizados=False  # Usan permisos del apoderado
            )
            relaciones_creadas += 1
            
            print(f"  ✓ {apoderado.user.get_full_name()} ({parentesco}) → {estudiante.get_full_name()}")
    
    print(f"✅ {apoderados_creados} apoderados y {relaciones_creadas} relaciones creadas\n")

def poblar_firmas_digitales():
    """Crear algunas firmas digitales de ejemplo"""
    print("✍️  Creando Firmas Digitales de Ejemplo...")
    
    # Obtener algunos apoderados
    apoderados = list(Apoderado.objects.filter(activo=True)[:5])
    
    tipos_documentos = [
        ('citacion', 'Citación Reunión de Apoderados', 'Se cita a reunión de apoderados el día viernes 15 de diciembre.'),
        ('comunicado', 'Comunicado Suspensión de Clases', 'Se informa suspensión de clases el lunes 18 de diciembre.'),
        ('autorizacion_salida', 'Autorización Salida Anticipada', 'Autorizo la salida anticipada de mi pupilo/a el día de hoy.'),
        ('autorizacion_actividad', 'Autorización Salida Pedagógica', 'Autorizo la participación en la salida pedagógica al museo.'),
        ('compromiso_academico', 'Compromiso de Mejora Académica', 'Me comprometo a apoyar el proceso académico de mi hijo/a.'),
    ]
    
    firmas_creadas = 0
    
    for i, apoderado in enumerate(apoderados):
        # Obtener un estudiante del apoderado
        estudiante = apoderado.get_estudiantes_activos().first()
        if not estudiante:
            continue
        
        # Crear 1-2 firmas por apoderado
        num_firmas = random.randint(1, 2)
        
        for _ in range(num_firmas):
            tipo, titulo, contenido = random.choice(tipos_documentos)
            
            # Simular IP y user agent
            ip_address = f'192.168.{random.randint(1, 255)}.{random.randint(1, 255)}'
            user_agent = random.choice([
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            ])
            
            firma = FirmaDigitalApoderado.crear_firma(
                apoderado=apoderado,
                tipo_documento=tipo,
                titulo=titulo,
                contenido=contenido,
                ip_address=ip_address,
                user_agent=user_agent,
                estudiante=estudiante
            )
            
            # Modificar el timestamp para que sea en los últimos 30 días
            dias_atras = random.randint(1, 30)
            firma.timestamp_firma = timezone.now() - timedelta(days=dias_atras)
            firma.save()
            
            firmas_creadas += 1
    
    print(f"  ✓ {firmas_creadas} firmas digitales creadas")
    print("✅ Firmas Digitales creadas\n")

def poblar_planificaciones():
    """Crear planificaciones/leccionarios de ejemplo"""
    print("📋 Creando Planificaciones de Clase...")
    
    colegio = Colegio.objects.get(rbd=10001)
    ciclo = CicloAcademico.objects.get(colegio=colegio, nombre='2025-2026')
    curso_1medio = Curso.objects.get(nombre='1° Medio A', colegio=colegio)
    
    # Obtener clases
    clases = Clase.objects.filter(curso=curso_1medio, activo=True).select_related('asignatura', 'profesor')
    
    planificaciones_creadas = 0
    
    for clase in clases:
        # 2-3 planificaciones por clase
        num_planificaciones = random.randint(2, 3)
        
        for i in range(1, num_planificaciones + 1):
            # Fechas de inicio y fin (2 semanas cada planificación)
            semanas_offset = (i - 1) * 2
            fecha_inicio = timezone.now().date() + timedelta(weeks=semanas_offset)
            fecha_fin = fecha_inicio + timedelta(weeks=2)
            
            planificacion = Planificacion.objects.create(
                colegio=colegio,
                clase=clase,
                titulo=f"Unidad {i}: {clase.asignatura.nombre}",
                objetivo_general=f"Comprender y aplicar conceptos fundamentales de {clase.asignatura.nombre}",
                fecha_inicio=fecha_inicio,
                fecha_fin=fecha_fin,
                ciclo_academico=ciclo,
                estado='activa',
                activa=True
            )
            
            # Agregar objetivos específicos
            from backend.apps.academico.models import PlanificacionObjetivo, PlanificacionActividad, PlanificacionRecurso
            
            PlanificacionObjetivo.objects.create(
                planificacion=planificacion,
                descripcion=f"Identificar conceptos clave de la unidad {i}",
                orden=1
            )
            PlanificacionObjetivo.objects.create(
                planificacion=planificacion,
                descripcion=f"Aplicar conocimientos en ejercicios prácticos",
                orden=2
            )
            
            # Agregar actividades
            PlanificacionActividad.objects.create(
                planificacion=planificacion,
                descripcion="Clase expositiva y ejercicios guiados",
                orden=1
            )
            PlanificacionActividad.objects.create(
                planificacion=planificacion,
                descripcion="Trabajo grupal y discusión",
                orden=2
            )
            
            # Agregar recursos
            PlanificacionRecurso.objects.create(
                planificacion=planificacion,
                descripcion="Proyector y presentación multimedia",
                orden=1
            )
            
            planificaciones_creadas += 1
    
    print(f"  ✓ {planificaciones_creadas} planificaciones creadas")
    print("✅ Planificaciones creadas\n")

def poblar_planes():
    """Crear los planes de suscripción del sistema"""
    print("💎 Creando Planes de Suscripción...")
    
    planes_data = [
        {
            'nombre': 'Plan Tester',
            'codigo': 'tester',
            'descripcion': 'Plan ilimitado para demostraciones y desarrollo. Todas las características habilitadas sin restricciones.',
            'precio_mensual': 0,
            'is_unlimited': True,
            'is_trial': False,
            'duracion_dias': None,
            'max_estudiantes': 999999,
            'max_profesores': 999999,
            'max_cursos': 999999,
            'max_mensajes_mes': 999999,
            'max_evaluaciones_mes': 999999,
            'max_almacenamiento_mb': 999999,
            'max_comunicados_mes': 999999,
            'has_attendance': True,
            'has_grades': True,
            'has_messaging': True,
            'has_reports': True,
            'has_advanced_reports': True,
            'has_file_attachments': True,
            'has_webpay_integration': True,
            'has_api_access': True,
            'has_priority_support': True,
            'has_custom_branding': True,
            'activo': True,
            'orden_visualizacion': 0,
            'destacado': False,
        },
        {
            'nombre': 'Prueba 30 Días',
            'codigo': 'trial',
            'descripcion': 'Prueba gratuita de 30 días con límites reducidos.',
            'precio_mensual': 0,
            'is_unlimited': False,
            'is_trial': True,
            'duracion_dias': 30,
            'max_estudiantes': 100,
            'max_profesores': 10,
            'max_cursos': 10,
            'max_mensajes_mes': 500,
            'max_evaluaciones_mes': 50,
            'max_almacenamiento_mb': 500,
            'max_comunicados_mes': 50,
            'has_attendance': True,
            'has_grades': True,
            'has_messaging': True,
            'has_reports': False,
            'has_advanced_reports': False,
            'has_file_attachments': True,
            'has_webpay_integration': False,
            'has_api_access': False,
            'has_priority_support': False,
            'has_custom_branding': False,
            'activo': True,
            'orden_visualizacion': 1,
            'destacado': False,
        },
        {
            'nombre': 'Plan Básico',
            'codigo': 'basic',
            'descripcion': 'Plan básico para colegios pequeños hasta 200 estudiantes.',
            'precio_mensual': 29990,
            'is_unlimited': False,
            'is_trial': False,
            'duracion_dias': None,
            'max_estudiantes': 200,
            'max_profesores': 20,
            'max_cursos': 15,
            'max_mensajes_mes': 1000,
            'max_evaluaciones_mes': 200,
            'max_almacenamiento_mb': 2000,
            'max_comunicados_mes': 100,
            'has_attendance': True,
            'has_grades': True,
            'has_messaging': True,
            'has_reports': True,
            'has_advanced_reports': False,
            'has_file_attachments': True,
            'has_webpay_integration': False,
            'has_api_access': False,
            'has_priority_support': False,
            'has_custom_branding': False,
            'activo': True,
            'orden_visualizacion': 2,
            'destacado': False,
        },
        {
            'nombre': 'Plan Estándar',
            'codigo': 'standard',
            'descripcion': 'Plan estándar para colegios medianos hasta 500 estudiantes.',
            'precio_mensual': 59990,
            'is_unlimited': False,
            'is_trial': False,
            'duracion_dias': None,
            'max_estudiantes': 500,
            'max_profesores': 50,
            'max_cursos': 40,
            'max_mensajes_mes': 5000,
            'max_evaluaciones_mes': 1000,
            'max_almacenamiento_mb': 10000,
            'max_comunicados_mes': 500,
            'has_attendance': True,
            'has_grades': True,
            'has_messaging': True,
            'has_reports': True,
            'has_advanced_reports': True,
            'has_file_attachments': True,
            'has_webpay_integration': True,
            'has_api_access': False,
            'has_priority_support': False,
            'has_custom_branding': False,
            'activo': True,
            'orden_visualizacion': 3,
            'destacado': True,
        },
        {
            'nombre': 'Plan Premium',
            'codigo': 'premium',
            'descripcion': 'Plan premium para colegios grandes hasta 1000 estudiantes.',
            'precio_mensual': 99990,
            'is_unlimited': False,
            'is_trial': False,
            'duracion_dias': None,
            'max_estudiantes': 1000,
            'max_profesores': 100,
            'max_cursos': 80,
            'max_mensajes_mes': 20000,
            'max_evaluaciones_mes': 5000,
            'max_almacenamiento_mb': 50000,
            'max_comunicados_mes': 2000,
            'has_attendance': True,
            'has_grades': True,
            'has_messaging': True,
            'has_reports': True,
            'has_advanced_reports': True,
            'has_file_attachments': True,
            'has_webpay_integration': True,
            'has_api_access': True,
            'has_priority_support': True,
            'has_custom_branding': False,
            'activo': True,
            'orden_visualizacion': 4,
            'destacado': False,
        },
        {
            'nombre': 'Plan Enterprise',
            'codigo': 'enterprise',
            'descripcion': 'Plan enterprise para instituciones con más de 1000 estudiantes. Personalizable y escalable.',
            'precio_mensual': 199990,
            'is_unlimited': False,
            'is_trial': False,
            'duracion_dias': None,
            'max_estudiantes': 999999,
            'max_profesores': 999999,
            'max_cursos': 999999,
            'max_mensajes_mes': 999999,
            'max_evaluaciones_mes': 999999,
            'max_almacenamiento_mb': 999999,
            'max_comunicados_mes': 999999,
            'has_attendance': True,
            'has_grades': True,
            'has_messaging': True,
            'has_reports': True,
            'has_advanced_reports': True,
            'has_file_attachments': True,
            'has_webpay_integration': True,
            'has_api_access': True,
            'has_priority_support': True,
            'has_custom_branding': True,
            'activo': True,
            'orden_visualizacion': 5,
            'destacado': False,
        },
    ]
    
    for plan_data in planes_data:
        plan, created = Plan.objects.get_or_create(
            codigo=plan_data['codigo'],
            defaults=plan_data
        )
        if created:
            print(f"  ✓ {plan.nombre} (${plan.precio_mensual}/mes)")
        else:
            print(f"  → {plan.nombre} ya existía")
    
    print("✅ Planes de Suscripción creados\n")

def poblar_suscripciones():
    """Asignar planes de suscripción a los colegios de prueba"""
    print("💳 Asignando Planes de Suscripción...")
    
    colegio1 = Colegio.objects.get(rbd=10001)
    colegio2 = Colegio.objects.get(rbd=10002)
    
    # Obtener planes
    plan_tester = Plan.objects.get(codigo='tester', is_unlimited=True)
    plan_standard = Plan.objects.get(codigo='standard')
    
    # Asignar plan TESTER al colegio 1 (para demos ilimitadas)
    subscription1, created1 = Subscription.objects.get_or_create(
        colegio=colegio1,
        defaults={
            'plan': plan_tester,
            'fecha_inicio': timezone.now().date(),
            'fecha_fin': None,  # TESTER no tiene fecha de fin
            'status': Subscription.STATUS_ACTIVE,
            'auto_renovar': False,
            'notas': 'Plan TESTER asignado para demostraciones y desarrollo'
        }
    )
    
    if created1:
        print(f"  ✓ {colegio1.nombre} → Plan TESTER (Ilimitado)")
    else:
        # Actualizar a TESTER si ya existe
        subscription1.plan = plan_tester
        subscription1.fecha_fin = None
        subscription1.status = Subscription.STATUS_ACTIVE
        subscription1.save()
        print(f"  ✓ {colegio1.nombre} → Plan TESTER actualizado")
    
    # Asignar plan STANDARD al colegio 2 (30 días activos)
    fecha_inicio = timezone.now().date()
    fecha_fin = fecha_inicio + timedelta(days=30)
    
    subscription2, created2 = Subscription.objects.get_or_create(
        colegio=colegio2,
        defaults={
            'plan': plan_standard,
            'fecha_inicio': fecha_inicio,
            'fecha_fin': fecha_fin,
            'proximo_pago': fecha_fin,
            'status': Subscription.STATUS_ACTIVE,
            'auto_renovar': True,
            'notas': 'Plan STANDARD de prueba (30 días)'
        }
    )
    
    if created2:
        print(f"  ✓ {colegio2.nombre} → Plan STANDARD (30 días)")
    else:
        subscription2.plan = plan_standard
        subscription2.fecha_fin = fecha_fin
        subscription2.proximo_pago = fecha_fin
        subscription2.status = Subscription.STATUS_ACTIVE
        subscription2.save()
        print(f"  ✓ {colegio2.nombre} → Plan STANDARD actualizado")
    
    # Actualizar contadores de uso para ambos colegios
    from backend.apps.subscriptions.utils import update_all_usage_counts
    
    usage1 = update_all_usage_counts(subscription1)
    print(f"    → Uso actualizado: {usage1.student_count} estudiantes, {usage1.teacher_count} profesores")
    
    usage2 = update_all_usage_counts(subscription2)
    print(f"    → Uso actualizado: {usage2.student_count} estudiantes, {usage2.teacher_count} profesores")
    
    print("✅ Suscripciones asignadas\n")

def poblar_datos_financieros():
    """Crear datos financieros de prueba: Cuotas, Pagos, Estados de Cuenta y Becas"""
    print("💰 Creando Datos Financieros de Prueba...")
    
    # Obtener colegio Santa María
    colegio = Colegio.objects.get(rbd=10001)
    
    # Obtener matriculas (ya existentes de poblar_matriculas)
    matriculas = Matricula.objects.filter(colegio=colegio).select_related('estudiante', 'curso')
    
    if not matriculas.exists():
        print("  ⚠️  No hay matrículas. Saltando datos financieros.")
        return
    
    print(f"  → Procesando {matriculas.count()} matrículas...")
    
    # Obtener asesor financiero para asignar
    asesor = User.objects.filter(
        rbd_colegio=colegio.rbd,
        role__nombre='Asesor financiero'
    ).first()
    
    # 1. CREAR CUOTAS (10 meses por matrícula: Marzo-Diciembre)
    print("\n  📋 Creando cuotas mensuales...")
    meses = [
        ('Enero', 1), ('Febrero', 2), ('Marzo', 3), ('Abril', 4), 
        ('Mayo', 5), ('Junio', 6), ('Julio', 7), ('Agosto', 8), 
        ('Septiembre', 9), ('Octubre', 10), ('Noviembre', 11), ('Diciembre', 12)
    ]
    
    cuotas_creadas = 0
    for matricula in matriculas:
        # Monto base según tipo (algunos tienen becas después)
        monto_base = 50000  # $50.000 mensuales
        
        for idx, (mes_nombre, mes_num) in enumerate(meses):
            # Fecha de vencimiento: día 5 de cada mes
            fecha_venc = datetime(2026, mes_num, 5).date()
            
            # Estado de pago varía:
            # - Enero: 90% pagadas (mes ya pasado casi)
            # - Febrero: 70% pagadas
            # - Marzo-Abril: 50% pagadas
            # - Mayo-Agosto: 30% pagadas
            # - Septiembre-Diciembre: 0% pagadas (aún no vencen)
            
            if mes_num == 1:
                prob_pagada = 0.9  # 90%
            elif mes_num == 2:
                prob_pagada = 0.7  # 70%
            elif mes_num <= 4:
                prob_pagada = 0.5  # 50%
            elif mes_num <= 8:
                prob_pagada = 0.3  # 30%
            else:
                prob_pagada = 0.0  # 0%
            
            esta_pagada = random.random() < prob_pagada
            monto_pagado = monto_base if esta_pagada else random.choice([0, monto_base * 0.3, monto_base * 0.5])
            
            # Determinar estado de la cuota
            if esta_pagada:
                estado_cuota = 'PAGADA'
            elif monto_pagado > 0:
                estado_cuota = 'PAGADA_PARCIAL'
            elif fecha_venc < datetime.now().date():
                estado_cuota = 'VENCIDA'
            else:
                estado_cuota = 'PENDIENTE'
            
            cuota = Cuota.objects.create(
                matricula=matricula,
                numero_cuota=idx + 1,
                mes=mes_num,
                anio=2026,
                monto_original=monto_base,
                monto_descuento=0,
                monto_final=monto_base,
                monto_pagado=monto_pagado,
                fecha_vencimiento=fecha_venc,
                estado=estado_cuota,
                fecha_pago_completo=datetime.now() if esta_pagada else None
            )
            cuotas_creadas += 1
    
    print(f"    ✓ {cuotas_creadas} cuotas creadas (10 meses × {matriculas.count()} estudiantes)")
    
    # 2. CREAR PAGOS (para las cuotas pagadas y parcialmente pagadas)
    print("\n  💳 Creando pagos...")
    
    metodos = ['EFECTIVO', 'TRANSFERENCIA', 'WEBPAY', 'CHEQUE', 'MERCADO_PAGO']
    estados = ['PENDIENTE', 'APROBADO', 'APROBADO', 'APROBADO']  # Mayoría aprobados
    
    cuotas_con_pago = Cuota.objects.filter(
        matricula__colegio=colegio,
        monto_pagado__gt=0
    ).select_related('matricula__estudiante')
    
    pagos_creados = 0
    for cuota in cuotas_con_pago:
        # Crear pago por el monto pagado
        metodo = random.choice(metodos)
        estado = random.choice(estados)
        
        # Fecha de pago: entre 1-10 días antes del vencimiento para pagos antiguos
        dias_antes = random.randint(1, 10)
        fecha_pago = cuota.fecha_vencimiento - timedelta(days=dias_antes)
        
        # Si es del mes actual o futuro, fecha de pago es hoy o reciente
        if cuota.fecha_vencimiento >= datetime.now().date():
            fecha_pago = datetime.now().date() - timedelta(days=random.randint(0, 5))
        
        pago = Pago.objects.create(
            cuota=cuota,
            estudiante=cuota.matricula.estudiante,
            monto=cuota.monto_pagado,
            metodo_pago=metodo,
            estado=estado,
            numero_comprobante=f'{metodo[:3]}-{random.randint(100000, 999999)}' if metodo != 'EFECTIVO' else '',
            fecha_pago=datetime.combine(fecha_pago, datetime.now().time()),
            procesado_por=asesor,
            fecha_procesamiento=datetime.combine(fecha_pago, datetime.now().time()) if estado == 'APROBADO' else None,
            observaciones=random.choice(['', '', '', 'Pago verificado', 'Abono parcial'])
        )
        pagos_creados += 1
    
    print(f"    ✓ {pagos_creados} pagos registrados")
    
    # Estadísticas de pagos
    pagos_efectivo = Pago.objects.filter(cuota__matricula__colegio=colegio, metodo_pago='EFECTIVO').count()
    pagos_transferencia = Pago.objects.filter(cuota__matricula__colegio=colegio, metodo_pago='TRANSFERENCIA').count()
    pagos_webpay = Pago.objects.filter(cuota__matricula__colegio=colegio, metodo_pago='WEBPAY').count()
    pagos_aprobados = Pago.objects.filter(cuota__matricula__colegio=colegio, estado='APROBADO').count()
    pagos_pendientes = Pago.objects.filter(cuota__matricula__colegio=colegio, estado='PENDIENTE').count()
    
    print(f"      → Efectivo: {pagos_efectivo} | Transferencia: {pagos_transferencia} | Webpay: {pagos_webpay}")
    print(f"      → Aprobados: {pagos_aprobados} | Pendientes: {pagos_pendientes}")
    
    # 3. CREAR ESTADOS DE CUENTA (para meses anteriores)
    print("\n  📊 Creando estados de cuenta...")
    
    meses_anteriores = [
        ('Enero', 1), ('Febrero', 2), ('Marzo', 3), ('Abril', 4),
        ('Mayo', 5), ('Junio', 6), ('Julio', 7), ('Agosto', 8)
    ]
    
    estados_creados = 0
    for matricula in matriculas[:15]:  # Solo para los primeros 15 estudiantes
        saldo_acumulado = 0
        for mes_nombre, mes_num in meses_anteriores[:6]:  # Enero-Junio
            # Calcular totales del mes
            cuotas_mes = Cuota.objects.filter(
                matricula=matricula,
                anio=2026,
                mes=mes_num
            )
            
            total_facturado = sum(c.monto_final for c in cuotas_mes)
            total_pagado = sum(c.monto_pagado for c in cuotas_mes)
            saldo_mes = total_facturado - total_pagado
            
            if total_facturado > 0:
                estado_cuenta = EstadoCuenta.objects.create(
                    estudiante=matricula.estudiante,
                    colegio=matricula.colegio,
                    mes=mes_num,
                    anio=2026,
                    total_deuda=total_facturado,
                    total_pagado=total_pagado,
                    saldo_pendiente=saldo_acumulado + saldo_mes,
                    estado='ENVIADO' if random.choice([True, False]) else 'GENERADO',
                    fecha_envio=datetime.now() if random.choice([True, False]) else None,
                )
                estados_creados += 1
                saldo_acumulado += saldo_mes
    
    print(f"    ✓ {estados_creados} estados de cuenta generados")
    
    # 4. CREAR BECAS (para algunos estudiantes)
    print("\n  🎓 Creando becas...")
    
    tipos_beca = [
        ('SOCIOECONOMICA', 50),
        ('RENDIMIENTO', 30),
        ('DEPORTIVA', 40),
        ('HERMANOS', 20),
        ('SOCIOECONOMICA', 100),
        ('RENDIMIENTO', 50),
    ]
    
    estados_beca = ['APROBADA', 'VIGENTE', 'VIGENTE', 'VIGENTE']
    
    becas_creadas = 0
    # Asignar becas a 10 estudiantes aleatorios
    estudiantes_con_beca = random.sample(list(matriculas), min(10, len(matriculas)))
    
    for i, matricula in enumerate(estudiantes_con_beca):
        tipo_beca, porcentaje = tipos_beca[i % len(tipos_beca)]
        estado = random.choice(estados_beca)
        
        beca = Beca.objects.create(
            estudiante=matricula.estudiante,
            matricula=matricula,
            tipo=tipo_beca,
            porcentaje_descuento=porcentaje,
            motivo=f'Beca otorgada por {tipo_beca.replace("_", " ").title()}. Estudiante cumple con requisitos.',
            descripcion=f'Beca aplicada para el año escolar 2026',
            fecha_inicio=datetime(2026, 3, 1).date(),
            fecha_fin=datetime(2026, 12, 31).date(),
            estado=estado if estado != 'VIGENTE' else 'APROBADA',
            aprobada_por=asesor if estado in ['APROBADA', 'VIGENTE'] else None,
            fecha_aprobacion=datetime.now() if estado in ['APROBADA', 'VIGENTE'] else None,
        )
        becas_creadas += 1
    
    print(f"    ✓ {becas_creadas} becas creadas")
    
    # 4. GENERAR BOLETAS PARA PAGOS APROBADOS
    print("\n  📄 Generando boletas electrónicas...")
    from backend.apps.matriculas.models import Boleta
    
    # Obtener pagos aprobados recientes (últimos 30 días como ejemplo)
    fecha_limite = datetime.now().date() - timedelta(days=90)
    pagos_para_boleta = Pago.objects.filter(
        cuota__matricula__colegio=colegio,
        estado='APROBADO',
        fecha_pago__date__gte=fecha_limite
    ).select_related('cuota__matricula__estudiante', 'cuota__matricula__curso')[:50]  # Limitar a 50 boletas
    
    boletas_creadas = 0
    for pago in pagos_para_boleta:
        # Generar número de boleta correlativo
        ultimo_numero = Boleta.objects.count()
        numero_boleta = f"BE-{colegio.rbd}-{(ultimo_numero + 1):06d}"
        
        # Obtener datos del estudiante como receptor
        matricula = pago.cuota.matricula
        estudiante = matricula.estudiante
        receptor_nombre = estudiante.get_full_name() if hasattr(estudiante, 'get_full_name') else f"Estudiante {estudiante.id}"
        receptor_rut = estudiante.rut if hasattr(estudiante, 'rut') and estudiante.rut else "12345678-9"
        receptor_email = estudiante.email if estudiante.email else f"estudiante{estudiante.id}@correo.cl"
        
        # Calcular montos (servicios educacionales están exentos de IVA en Chile)
        monto_neto = pago.monto
        monto_exento = monto_neto
        monto_iva = 0
        monto_total = monto_neto
        
        # Detalle de la boleta
        cuota = pago.cuota
        meses = ['', 'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 
                'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
        mes_nombre = meses[cuota.mes] if cuota.mes <= 12 else f"Cuota {cuota.numero_cuota}"
        estudiante_nombre = matricula.estudiante.get_full_name() if hasattr(matricula.estudiante, 'get_full_name') else f"Estudiante {matricula.estudiante.id}"
        detalle = f"Pago Cuota {mes_nombre} {cuota.anio} - {estudiante_nombre} - {matricula.curso.nombre if matricula.curso else 'Sin curso'}"
        
        # Estado de la boleta: mayoría emitidas
        estado_boleta = 'EMITIDA'
        
        # Crear boleta
        boleta = Boleta.objects.create(
            pago=pago,
            estudiante=estudiante,
            numero_boleta=numero_boleta,
            monto_total=monto_total,
            detalle=detalle,
            estado=estado_boleta,
        )
        boletas_creadas += 1
    
    print(f"    ✓ {boletas_creadas} boletas generadas")
    
    # 5. ACTUALIZAR ESTADOS DE CUENTA
    print("\n  📊 Actualizando estados de cuenta...")
    from decimal import Decimal
    
    # Actualizar estados existentes y crear faltantes
    estados_actualizados = 0
    estados_nuevos = 0
    
    for matricula in matriculas:
        # Calcular totales reales
        cuotas_matricula = Cuota.objects.filter(matricula=matricula)
        total_facturado = sum(c.monto_final for c in cuotas_matricula)
        total_pagado = sum(c.monto_pagado for c in cuotas_matricula)
        saldo_actual = total_facturado - total_pagado
        
        cuotas_pagadas = cuotas_matricula.filter(estado='PAGADA').count()
        cuotas_pendientes = cuotas_matricula.filter(estado='PENDIENTE').count()
        cuotas_vencidas = cuotas_matricula.filter(estado='VENCIDA').count()
        
        # Obtener mes y año de la primera cuota o usar mes actual
        primera_cuota = cuotas_matricula.first()
        if primera_cuota:
            mes_estado = primera_cuota.mes
            anio_estado = primera_cuota.anio
        else:
            mes_estado = 1  # Enero
            anio_estado = 2026
        
        # Buscar estado de cuenta existente o crear uno nuevo
        estado_cuenta, created = EstadoCuenta.objects.get_or_create(
            estudiante=matricula.estudiante,
            colegio=matricula.colegio,
            mes=mes_estado,
            anio=anio_estado,
            defaults={
                'total_deuda': Decimal(str(total_facturado)),
                'total_pagado': Decimal(str(total_pagado)),
                'saldo_pendiente': Decimal(str(saldo_actual)),
                'estado': 'GENERADO'
            }
        )
        
        if created:
            estados_nuevos += 1
        else:
            # Actualizar estado existente
            estado_cuenta.total_deuda = Decimal(str(total_facturado))
            estado_cuenta.total_pagado = Decimal(str(total_pagado))
            estado_cuenta.saldo_pendiente = Decimal(str(saldo_actual))
            estado_cuenta.save()
            estados_actualizados += 1
    
    print(f"    ✓ {estados_nuevos} estados de cuenta nuevos creados")
    print(f"    ✓ {estados_actualizados} estados de cuenta actualizados")
    
    # Estadísticas finales
    print("\n  📈 Resumen Financiero:")
    total_cuotas = Cuota.objects.filter(matricula__colegio=colegio)
    total_cobrado = sum(c.monto_final for c in total_cuotas)
    total_pagado = sum(c.monto_pagado for c in total_cuotas)
    total_pendiente = total_cobrado - total_pagado
    cuotas_vencidas = total_cuotas.filter(estado='VENCIDA').count()
    total_boletas = Boleta.objects.count()
    total_becas = Beca.objects.filter(matricula__colegio=colegio, estado='APROBADA').count()
    total_estados = EstadoCuenta.objects.filter(colegio=colegio).count()
    
    print(f"    → Total Cobrado: ${total_cobrado:,.0f}")
    print(f"    → Total Pagado: ${total_pagado:,.0f}")
    print(f"    → Total Pendiente: ${total_pendiente:,.0f}")
    print(f"    → Cuotas Vencidas: {cuotas_vencidas}")
    print(f"    → Tasa de Cobranza: {(total_pagado/total_cobrado*100):.1f}%")
    print(f"\n  📋 Documentos Generados:")
    print(f"    → Boletas Emitidas: {total_boletas}")
    print(f"    → Becas Activas: {total_becas}")
    print(f"    → Estados de Cuenta: {total_estados}")
    
    print("\n✅ Datos financieros creados exitosamente\n")

def poblar_datos_pedro_gonzalez():
    """
    Poblar datos exhaustivos específicos para Pedro González Contreras (alumno1@colegio.cl)
    para demostrar todas las funcionalidades del sistema.
    """
    print("🎯 Poblando datos exhaustivos para Pedro González Contreras...")
    print("=" * 60)
    
    colegio = Colegio.objects.get(rbd=10001)
    
    # Obtener Pedro
    try:
        pedro = User.objects.get(email='alumno1@colegio.cl')
        print(f"  ✓ Encontrado: {pedro.get_full_name()} ({pedro.email})")
    except User.DoesNotExist:
        print("  ❌ No se encontró a Pedro González Contreras")
        return
    
    # Verificar perfil
    perfil = PerfilEstudiante.objects.filter(user=pedro).first()
    if not perfil:
        print("  ❌ Pedro no tiene perfil de estudiante")
        return
    
    curso = perfil.curso_actual
    print(f"  ✓ Curso: {curso.nombre}")
    
    # Obtener clases de Pedro
    clases = Clase.objects.filter(curso=curso, activo=True).select_related('asignatura', 'profesor')
    print(f"  ✓ Clases disponibles: {clases.count()}")
    
    # 1. ASISTENCIA ADICIONAL (últimos 30 días con mayor detalle)
    print("\n  📅 Generando asistencia adicional detallada...")
    asistencias_creadas = 0
    for dias in range(30, 0, -1):
        fecha = timezone.now().date() - timedelta(days=dias)
        if fecha.weekday() >= 5:  # Skip weekends
            continue
        
        for clase in clases:
            # Patrón: Pedro es muy buen alumno (98% asistencia)
            rand = random.random()
            if rand < 0.98:
                estado = 'P'
                observaciones = None
            elif rand < 0.99:
                estado = 'T'
                observaciones = 'Problema de transporte'
            else:
                estado = 'J'
                observaciones = 'Control médico'
            
            # Evitar duplicados
            if not Asistencia.objects.filter(
                estudiante=pedro,
                clase=clase,
                fecha=fecha
            ).exists():
                Asistencia.objects.create(
                    colegio=colegio,
                    clase=clase,
                    estudiante=pedro,
                    fecha=fecha,
                    estado=estado,
                    observaciones=observaciones
                )
                asistencias_creadas += 1
    
    print(f"    ✓ {asistencias_creadas} registros de asistencia adicionales")
    
    # 2. CALIFICACIONES ADICIONALES
    print("\n  📊 Generando calificaciones adicionales...")
    calificaciones_creadas = 0
    
    # Obtener un profesor para registrar las calificaciones
    profesor = clases.first().profesor if clases.exists() else None
    
    if profesor:
        for clase in clases:
            # Verificar si ya tiene evaluaciones
            evaluaciones = Evaluacion.objects.filter(clase=clase)
            
            for evaluacion in evaluaciones:
                # Crear calificación si no existe
                if not Calificacion.objects.filter(
                    evaluacion=evaluacion,
                    estudiante=pedro
                ).exists():
                    # Pedro es buen alumno: notas entre 5.5 y 7.0
                    nota = round(random.uniform(5.5, 7.0), 1)
                    Calificacion.objects.create(
                        colegio=colegio,
                        evaluacion=evaluacion,
                        estudiante=pedro,
                        nota=nota,
                        registrado_por=profesor
                    )
                    calificaciones_creadas += 1
    
    print(f"    ✓ {calificaciones_creadas} calificaciones adicionales")
    
    # 3. TAREAS Y ENTREGAS
    print("\n  📝 Generando entregas de tareas...")
    entregas_creadas = 0
    for clase in clases:
        tareas = Tarea.objects.filter(clase=clase)
        
        for tarea in tareas:
            # Crear entrega si no existe
            if not EntregaTarea.objects.filter(
                tarea=tarea,
                estudiante=pedro
            ).exists():
                # Pedro entrega a tiempo (90% de las veces)
                dias_antes = random.randint(-2, 5) if random.random() < 0.9 else random.randint(-5, -1)
                fecha_entrega_real = tarea.fecha_entrega + timedelta(days=dias_antes)
                
                entrega_tardia = fecha_entrega_real > tarea.fecha_entrega
                calificacion = round(random.uniform(5.5, 7.0), 1) if not entrega_tardia else round(random.uniform(4.5, 6.0), 1)
                
                EntregaTarea.objects.create(
                    tarea=tarea,
                    estudiante=pedro,
                    comentario_estudiante="Adjunto mi tarea completada.",
                    calificacion=calificacion,
                    retroalimentacion="Excelente trabajo" if not entrega_tardia else "Entrega tardía, pero buen contenido",
                    estado='revisada',
                    revisada_por=clase.profesor
                )
                entregas_creadas += 1
    
    print(f"    ✓ {entregas_creadas} entregas de tareas creadas")
    
    # 4. RESUMEN FINAL
    total_asistencias = Asistencia.objects.filter(estudiante=pedro).count()
    total_calificaciones = Calificacion.objects.filter(estudiante=pedro).count()
    total_entregas = EntregaTarea.objects.filter(estudiante=pedro).count()
    
    print("\n  📈 RESUMEN FINAL - Pedro González Contreras:")
    print("  " + "="*58)
    print(f"    Total Asistencias: {total_asistencias}")
    print(f"    Total Calificaciones: {total_calificaciones}")
    print(f"    Total Entregas de Tareas: {total_entregas}")
    print(f"    Clases Inscritas: {clases.count()}")
    
    # Calcular estadísticas de asistencia
    if total_asistencias > 0:
        presentes = Asistencia.objects.filter(estudiante=pedro, estado='P').count()
        tardanzas = Asistencia.objects.filter(estudiante=pedro, estado='T').count()
        ausentes = Asistencia.objects.filter(estudiante=pedro, estado='A').count()
        justificadas = Asistencia.objects.filter(estudiante=pedro, estado='J').count()
        
        porcentaje = round((presentes / total_asistencias) * 100, 1)
        
        print(f"\n    Estadísticas de Asistencia:")
        print(f"      Presentes: {presentes} ({porcentaje}%)")
        print(f"      Tardanzas: {tardanzas}")
        print(f"      Ausentes: {ausentes}")
        print(f"      Justificadas: {justificadas}")
    
    # Calcular promedio de notas
    if total_calificaciones > 0:
        from django.db.models import Avg
        promedio = Calificacion.objects.filter(estudiante=pedro).aggregate(Avg('nota'))['nota__avg']
        print(f"\n    Promedio de Notas: {promedio:.2f}")
    
    print("\n✅ Datos exhaustivos de Pedro González completados\n")

def poblar_datos_especificos_usuarios_clave():
    """
    Poblar datos específicos y completos para los usuarios clave mencionados.
    Esta función se ejecuta al final para completar datos específicos.
    """
    print("🎯 Poblando datos específicos para usuarios clave...")
    print("=" * 60)

    # Verificar si las tablas Fase 3 existen
    from django.db import connection
    tablas_fase3 = ['ciclo_academico', 'estado_matricula', 'matricula_mejorada']
    tablas_faltantes = []

    # Usar Django's table introspection en lugar de raw SQL
    with connection.cursor() as cursor:
        for tabla in tablas_fase3:
            try:
                # Intentar una consulta simple en la tabla
                cursor.execute(f"SELECT 1 FROM {tabla} LIMIT 1;")
                # Si no hay error, la tabla existe
            except Exception:
                # Si hay error, la tabla no existe
                tablas_faltantes.append(tabla)

    if tablas_faltantes:
        print(f"  ⚠️  Tablas Fase 3 faltantes: {', '.join(tablas_faltantes)}")
        print("  💡 Esta función requiere que se ejecuten las migraciones Fase 3 primero.")
        print("  💡 Ejecuta 'python manage.py migrate core' para crear las tablas Fase 3.")
        print("  ⏭️  Saltando poblamiento de datos específicos de usuarios clave...\n")
        return

    print("  ✅ Tablas Fase 3 disponibles. Procediendo con datos específicos...\n")

    # Aquí iría el código para poblar datos específicos cuando las tablas Fase 3 estén disponibles
    # Por ahora, solo mostrar que la función se ejecutó correctamente
    print("  📝 Función de datos específicos ejecutada (tablas Fase 3 disponibles)")
    print("  💡 Los datos específicos se pueden agregar aquí cuando sea necesario\n")

def main():
    """Función principal"""
    print("\n" + "="*60)
    print("🚀 INICIANDO AUTOPOBLADO DE BASE DE DATOS")
    print("="*60 + "\n")
    
    try:
        limpiar_base_datos()
        poblar_roles()
        poblar_regiones_comunas()
        poblar_catalogos()
        poblar_estados_matricula()  # NUEVO: Fase 3
        poblar_colegios()
        poblar_usuarios()
        poblar_ciclos_academicos()  # NUEVO: Fase 3 - Movido después de usuarios
        poblar_perfil_asesor_financiero()
        poblar_disponibilidades_profesores()
        poblar_cursos_asignaturas()
        poblar_clases()
        poblar_horarios()
        poblar_matriculas()  # ACTUALIZADO: Ahora usa MatriculaMejorada
        poblar_matriculas_clases()  # NUEVO: Vincular estudiantes con clases específicas
        poblar_perfiles_estudiantes()
        poblar_apoderados()
        poblar_evaluaciones_calificaciones()
        poblar_asistencia()
        poblar_tareas()
        poblar_materiales()
        poblar_anuncios()
        poblar_comunicados()
        poblar_notificaciones()
        poblar_planificaciones()
        poblar_firmas_digitales()
        poblar_planes()  # Crear planes de suscripción
        poblar_suscripciones()  # Asignar planes de suscripción
        poblar_datos_financieros()  # Datos financieros de prueba
        poblar_datos_especificos_usuarios_clave()  # Verificar y completar datos de usuarios clave
        poblar_datos_pedro_gonzalez()  # NUEVO: Datos exhaustivos para Pedro González
        
        print("\n" + "="*60)
        print("✅ AUTOPOBLADO COMPLETADO EXITOSAMENTE")
        print("="*60)
        print("\n📌 DATOS DE ACCESO:")
        print("-" * 60)
        print("Administrador General:")
        print("  Email: carlos.perez@colegio.cl")
        print("  Contraseña: Admin#2025*Seg!")
        print()
        print("Administrador Escolar:")
        print("  Email: maria.lopez@colegio.cl")
        print("  Contraseña: Escolar@2025#!")
        print()
        print("Profesor:")
        print("  Email: javier.torres@colegio.cl")
        print("  Contraseña: Prof*2025&Seg!")
        print()
        print("Asesor Financiero:")
        print("  Email: laura.mendez@colegio.cl")
        print("  Contraseña: Finan#2025$Seg!")
        print("  [Acceso completo a módulo financiero]")
        print()
        print("Coordinador Académico:")
        print("  Email: paula.rios@colegio.cl")
        print("  Contraseña: Coord#2025!Seg")
        print()
        print("Inspector Convivencia:")
        print("  Email: oscar.leiva@colegio.cl")
        print("  Contraseña: Insp#2025!Seg+")
        print()
        print("Psicólogo Orientador:")
        print("  Email: daniela.reyes@colegio.cl")
        print("  Contraseña: Psico#2025!Seg")
        print()
        print("Soporte Técnico Escolar:")
        print("  Email: nicolas.araya@colegio.cl")
        print("  Contraseña: Soport#2025!Seg")
        print()
        print("Bibliotecario Digital:")
        print("  Email: elena.poblete@colegio.cl")
        print("  Contraseña: Biblio#2025!Seg")
        print()
        print("Apoderado:")
        print("  Email: carmen.silva@gmail.com")
        print("  RUT: 15.555.666-7")
        print("  Contraseña: Apod#2025!Seg*")
        print("  [Tiene 2 estudiantes a cargo]")
        print()
        print("Estudiantes (30 en 1° Medio A):")
        print("  Email: alumno1@colegio.cl hasta alumno30@colegio.cl")
        print("  Contraseña: Estud#2025*01! (alumno1), Estud#2025*02! (alumno2), etc.")
        print("  [6 estudiantes tienen NEE asignadas]")
        print()
        print("Otros Apoderados (15 en total):")
        print("  Emails: carmen.silva@gmail.com, roberto.munoz@gmail.com, etc.")
        print("  Contraseña: Apod#2025!Seg*")
        print("  [Cada apoderado tiene 2 estudiantes, total 30 relaciones]")
        print()
        print("🚀 NUEVAS CARACTERÍSTICAS FASE 3:")
        print("-" * 60)
        print("✅ Ciclos Académicos: Concepto temporal fundamental (2025-2026)")
        print("✅ Estados Explícitos: Transiciones validadas (ACTIVO, SUSPENDIDO, RETIRADO)")
        print("✅ Constraints BD: Validaciones preventivas a nivel de base de datos")
        print("✅ Audit Trails: Trazabilidad completa de cambios")
        print("✅ Matrículas Mejoradas: Con ciclo académico y estados")
        print("✅ 28 matrículas ACTIVAS + 1 SUSPENDIDA + 1 RETIRADA (ejemplos)")
        print()
        print("Suscripciones:")
        print("  Colegio Santa María (RBD 10001): Plan TESTER (Ilimitado)")
        print("  Liceo Técnico Industrial (RBD 10002): Plan STANDARD (30 días)")
        print()
        print("Datos Financieros (Colegio Santa María):")
        print("  ✓ 300 cuotas mensuales (10 meses × 30 estudiantes)")
        print("  ✓ Pagos con múltiples métodos (Efectivo, Transferencia, Webpay, etc.)")
        print("  ✓ Estados de cuenta generados (Enero-Agosto 2026)")
        print("  ✓ 10 becas otorgadas (Académica, Socioeconómica, Deportiva, etc.)")
        print("  ✓ Boletas electrónicas generadas para pagos aprobados")
        print("  ✓ Morosidad simulada (20-80% según mes)")
        print("  → URL: http://127.0.0.1:8000/dashboard/?pagina=pagos")
        print("  → URL: http://127.0.0.1:8000/dashboard/?pagina=boletas")
        print("="*60 + "\n")
        
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
