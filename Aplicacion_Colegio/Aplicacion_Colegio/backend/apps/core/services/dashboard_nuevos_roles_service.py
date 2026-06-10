"""
Servicios de dashboard para los 5 nuevos roles.

Cada rol tiene un servicio que proporciona el contexto necesario para sus
vistas de dashboard, siguiendo el mismo patrón que DashboardAsesorService.
"""

import logging
from datetime import date, timedelta

from django.db.models import Avg, Count, Q
from django.utils import timezone

logger = logging.getLogger(__name__)


class DashboardCoordinadorService:
    """Dashboard del Coordinador Académico / Jefe UTP."""

    @staticmethod
    def get_context(user, pagina_solicitada, escuela_rbd):
        """Retorna el contexto según la página solicitada."""
        handlers = {
            'inicio': DashboardCoordinadorService._get_inicio_context,
            'rendimiento': DashboardCoordinadorService._get_rendimiento_context,
            'profesores': DashboardCoordinadorService._get_profesores_context,
            'planificacion': DashboardCoordinadorService._get_planificacion_context,
        }
        handler = handlers.get(pagina_solicitada, DashboardCoordinadorService._get_inicio_context)
        try:
            return handler(user, escuela_rbd)
        except Exception as exc:
            logger.error("Error en dashboard coordinador [%s]: %s", pagina_solicitada, exc)
            return {'error_context': str(exc)}

    @staticmethod
    def _get_inicio_context(user, escuela_rbd):
        from backend.apps.academico.models import Calificacion, Evaluacion, Asistencia, Planificacion
        from backend.apps.cursos.models import Curso

        cursos = Curso.objects.filter(colegio_id=escuela_rbd, activo=True)
        total_evaluaciones = Evaluacion.objects.filter(colegio_id=escuela_rbd, activa=True).count()
        promedio_global = Calificacion.objects.filter(
            colegio_id=escuela_rbd,
        ).aggregate(avg=Avg('nota'))['avg']

        # Tasa de reprobación (nota < 4.0 en escala chilena)
        total_calificaciones = Calificacion.objects.filter(colegio_id=escuela_rbd).count()
        reprobadas = Calificacion.objects.filter(
            colegio_id=escuela_rbd, nota__lt=4.0,
        ).count()
        tasa_reprobacion = 0
        if total_calificaciones:
            tasa_reprobacion = round((reprobadas / total_calificaciones) * 100, 1)

        # Planificaciones pendientes de revisión
        planificaciones_pendientes = Planificacion.objects.filter(
            colegio_id=escuela_rbd, activa=True, estado='ENVIADA',
        ).count()

        hoy = date.today()
        semana_inicio = hoy - timedelta(days=hoy.weekday())
        asistencia_semana = Asistencia.objects.filter(
            colegio_id=escuela_rbd,
            fecha__gte=semana_inicio,
        ).aggregate(
            total=Count('id_asistencia'),
            presentes=Count('id_asistencia', filter=Q(estado='P')),
        )
        tasa_asistencia = 0
        if asistencia_semana['total']:
            tasa_asistencia = round(
                (asistencia_semana['presentes'] / asistencia_semana['total']) * 100, 1
            )

        return {
            'total_cursos': cursos.count(),
            'total_evaluaciones': total_evaluaciones,
            'promedio_global': round(promedio_global, 1) if promedio_global else None,
            'tasa_reprobacion': tasa_reprobacion,
            'planificaciones_pendientes': planificaciones_pendientes,
            'tasa_asistencia_semanal': tasa_asistencia,
        }

    @staticmethod
    def _get_rendimiento_context(user, escuela_rbd):
        from backend.apps.academico.models import Calificacion
        from backend.apps.cursos.models import Curso, Asignatura

        cursos = Curso.objects.filter(
            colegio_id=escuela_rbd, activo=True,
        ).select_related('ciclo_academico', 'nivel')

        rendimiento_por_curso = []
        for curso in cursos:
            promedio = Calificacion.objects.filter(
                evaluacion__clase__curso=curso,
                colegio_id=escuela_rbd,
            ).aggregate(avg=Avg('nota'))['avg']
            rendimiento_por_curso.append({
                'curso': curso,
                'promedio': round(promedio, 1) if promedio else None,
            })

        asignaturas = Asignatura.objects.filter(colegio_id=escuela_rbd, activa=True)
        rendimiento_por_asignatura = []
        for asig in asignaturas:
            promedio = Calificacion.objects.filter(
                evaluacion__clase__asignatura=asig,
                colegio_id=escuela_rbd,
            ).aggregate(avg=Avg('nota'))['avg']
            rendimiento_por_asignatura.append({
                'asignatura': asig,
                'promedio': round(promedio, 1) if promedio else None,
            })

        return {
            'rendimiento_por_curso': rendimiento_por_curso,
            'rendimiento_por_asignatura': rendimiento_por_asignatura,
        }

    @staticmethod
    def _get_profesores_context(user, escuela_rbd):
        from backend.apps.accounts.models import User
        from backend.apps.academico.models import Evaluacion
        from backend.apps.cursos.models import Clase

        profesores = User.objects.filter(
            rbd_colegio=escuela_rbd,
            role__nombre__iexact='Profesor',
            is_active=True,
        ).select_related('role')

        profesores_data = []
        for prof in profesores:
            clases_count = Clase.objects.filter(
                profesor=prof, colegio_id=escuela_rbd, activo=True,
            ).count()
            ultima_evaluacion = Evaluacion.objects.filter(
                clase__profesor=prof, colegio_id=escuela_rbd,
            ).order_by('-fecha_creacion').first()
            profesores_data.append({
                'profesor': prof,
                'clases_activas': clases_count,
                'ultima_actividad': ultima_evaluacion.fecha_creacion if ultima_evaluacion else None,
            })

        return {'profesores': profesores_data}

    @staticmethod
    def _get_planificacion_context(user, escuela_rbd):
        from backend.apps.academico.models import Planificacion

        planificaciones = Planificacion.objects.filter(
            colegio_id=escuela_rbd,
            activa=True,
        ).select_related('clase', 'clase__curso', 'clase__asignatura', 'clase__profesor')\
         .order_by('-fecha_creacion')

        pendientes = planificaciones.filter(estado='ENVIADA').count()
        aprobadas = planificaciones.filter(estado='APROBADA').count()
        rechazadas = planificaciones.filter(estado='RECHAZADA').count()

        return {
            'planificaciones': planificaciones[:50],
            'planificaciones_pendientes': pendientes,
            'planificaciones_aprobadas': aprobadas,
            'planificaciones_rechazadas': rechazadas,
        }


class DashboardInspectorService:
    """Dashboard del Inspector de Convivencia."""

    @staticmethod
    def get_context(user, pagina_solicitada, escuela_rbd):
        handlers = {
            'inicio': DashboardInspectorService._get_inicio_context,
            'anotaciones': DashboardInspectorService._get_anotaciones_context,
            'justificativos': DashboardInspectorService._get_justificativos_context,
            'asistencia': DashboardInspectorService._get_asistencia_context,
        }
        handler = handlers.get(pagina_solicitada, DashboardInspectorService._get_inicio_context)
        try:
            return handler(user, escuela_rbd)
        except Exception as exc:
            logger.error("Error en dashboard inspector [%s]: %s", pagina_solicitada, exc)
            return {'error_context': str(exc)}

    @staticmethod
    def _get_inicio_context(user, escuela_rbd):
        from backend.apps.academico.models import Asistencia
        from backend.apps.core.models import AnotacionConvivencia, JustificativoInasistencia

        hoy = date.today()
        atrasos_hoy = Asistencia.objects.filter(
            colegio_id=escuela_rbd, fecha=hoy, estado='T',
        ).count()
        ausencias_hoy = Asistencia.objects.filter(
            colegio_id=escuela_rbd, fecha=hoy, estado='A',
        ).count()
        anotaciones_hoy = AnotacionConvivencia.objects.filter(
            colegio_id=escuela_rbd, fecha__date=hoy,
        ).count()
        justificativos_pendientes = JustificativoInasistencia.objects.filter(
            colegio_id=escuela_rbd, estado='PENDIENTE',
        ).count()

        return {
            'atrasos_hoy': atrasos_hoy,
            'ausencias_hoy': ausencias_hoy,
            'anotaciones_hoy': anotaciones_hoy,
            'justificativos_pendientes': justificativos_pendientes,
        }

    @staticmethod
    def _get_anotaciones_context(user, escuela_rbd):
        from backend.apps.core.models import AnotacionConvivencia

        anotaciones = AnotacionConvivencia.objects.filter(
            colegio_id=escuela_rbd,
        ).select_related('estudiante', 'registrado_por').order_by('-fecha')[:50]

        conteo = AnotacionConvivencia.objects.filter(
            colegio_id=escuela_rbd,
        ).aggregate(
            positivas=Count('id_anotacion', filter=Q(tipo='POSITIVA')),
            negativas=Count('id_anotacion', filter=Q(tipo='NEGATIVA')),
            neutras=Count('id_anotacion', filter=Q(tipo='NEUTRA')),
            total=Count('id_anotacion'),
        )

        return {
            'anotaciones': anotaciones,
            'conteo_positivas': conteo['positivas'],
            'conteo_negativas': conteo['negativas'],
            'conteo_neutras': conteo['neutras'],
            'conteo_total': conteo['total'],
        }

    @staticmethod
    def _get_justificativos_context(user, escuela_rbd):
        from backend.apps.core.models import JustificativoInasistencia

        justificativos = JustificativoInasistencia.objects.filter(
            colegio_id=escuela_rbd,
        ).select_related('estudiante', 'presentado_por', 'revisado_por')\
         .order_by('-fecha_creacion')[:50]

        pendientes = JustificativoInasistencia.objects.filter(
            colegio_id=escuela_rbd, estado='PENDIENTE',
        ).count()

        return {
            'justificativos': justificativos,
            'justificativos_pendientes': pendientes,
        }

    @staticmethod
    def _get_asistencia_context(user, escuela_rbd):
        from backend.apps.academico.models import Asistencia
        from backend.apps.accounts.models import User
        from backend.apps.cursos.models import Clase

        hoy = date.today()
        asistencia_hoy = Asistencia.objects.filter(
            colegio_id=escuela_rbd, fecha=hoy,
        ).select_related('estudiante', 'clase', 'clase__curso')

        estudiantes = User.objects.filter(
            rbd_colegio=escuela_rbd, role__nombre__in=['Alumno', 'Estudiante'], is_active=True
        ).order_by('apellido_paterno', 'nombre')

        clases = Clase.objects.filter(
            curso__colegio_id=escuela_rbd, activo=True
        ).select_related('curso', 'asignatura').order_by('curso__nombre', 'asignatura__nombre')

        return {
            'asistencia_hoy': asistencia_hoy,
            'fecha_consulta': hoy,
            'estudiantes': estudiantes,
            'clases': clases,
        }


class DashboardPsicologoService:
    """Dashboard del Psicólogo Orientador."""

    @staticmethod
    def get_context(user, pagina_solicitada, escuela_rbd, get_params=None):
        handlers = {
            'inicio': DashboardPsicologoService._get_inicio_context,
            'entrevistas': DashboardPsicologoService._get_entrevistas_context,
            'derivaciones': DashboardPsicologoService._get_derivaciones_context,
            'ficha_estudiante': DashboardPsicologoService._get_ficha_estudiante_context,
            'citaciones_casos': DashboardPsicologoService._get_citaciones_casos_context,
        }
        handler = handlers.get(pagina_solicitada, DashboardPsicologoService._get_inicio_context)
        try:
            if pagina_solicitada == 'ficha_estudiante':
                return handler(user, escuela_rbd, get_params)
            return handler(user, escuela_rbd)
        except Exception as exc:
            logger.error("Error en dashboard psicólogo [%s]: %s", pagina_solicitada, exc)
            return {'error_context': str(exc)}

    @staticmethod
    def _get_inicio_context(user, escuela_rbd):
        from backend.apps.core.models import (
            EntrevistaOrientacion, DerivacionExterna, AnotacionConvivencia,
            CitacionApoderado, CasoBullyingConvivencia,
        )
        from backend.apps.academico.models import Asistencia, Calificacion
        from backend.apps.accounts.models import User

        hoy = date.today()
        mes_atras = hoy - timedelta(days=30)

        entrevistas_semana = EntrevistaOrientacion.objects.filter(
            colegio_id=escuela_rbd, fecha__date__gte=hoy - timedelta(days=7),
        ).count()
        seguimientos_pendientes = EntrevistaOrientacion.objects.filter(
            colegio_id=escuela_rbd,
            seguimiento_requerido=True,
            fecha_siguiente_sesion__lte=hoy,
        ).count()
        derivaciones_activas = DerivacionExterna.objects.filter(
            colegio_id=escuela_rbd,
            estado__in=['PENDIENTE', 'EN_PROCESO'],
        ).count()
        citaciones_pendientes = CitacionApoderado.objects.filter(
            colegio_id=escuela_rbd,
            estado='PENDIENTE',
        ).count()
        casos_bullying_abiertos = CasoBullyingConvivencia.objects.filter(
            colegio_id=escuela_rbd,
            estado__in=['ABIERTO', 'EN_INVESTIGACION'],
        ).count()

        # Alertas tempranas: alumnos con muchas inasistencias en el último mes
        alumnos_inasistencia = Asistencia.objects.filter(
            colegio_id=escuela_rbd,
            fecha__gte=mes_atras,
            estado='A',
        ).values(
            'estudiante',
            'estudiante__nombre',
            'estudiante__apellido_paterno',
            'estudiante__apellido_materno',
        ).annotate(
            ausencias=Count('id_asistencia'),
        ).filter(ausencias__gte=3).order_by('-ausencias')

        # Alertas: alumnos con atrasos reiterados en el último mes
        alumnos_atrasos = Asistencia.objects.filter(
            colegio_id=escuela_rbd,
            fecha__gte=mes_atras,
            estado='T',
        ).values(
            'estudiante',
            'estudiante__nombre',
            'estudiante__apellido_paterno',
            'estudiante__apellido_materno',
        ).annotate(
            atrasos=Count('id_asistencia'),
        ).filter(atrasos__gte=3).order_by('-atrasos')

        # Alertas: alumnos con anotaciones negativas recientes
        alumnos_anotaciones = AnotacionConvivencia.objects.filter(
            colegio_id=escuela_rbd,
            tipo='NEGATIVA',
            fecha__date__gte=mes_atras,
        ).values(
            'estudiante',
            'estudiante__nombre',
            'estudiante__apellido_paterno',
            'estudiante__apellido_materno',
        ).annotate(
            negativas=Count('id_anotacion'),
        ).filter(negativas__gte=2).order_by('-negativas')

        # Rendimiento académico: promedio de notas y reprobadas por estudiante
        alumnos_rendimiento = Calificacion.objects.filter(
            colegio_id=escuela_rbd,
        ).values(
            'estudiante',
        ).annotate(
            promedio=Avg('nota'),
            reprobadas=Count('id_calificacion', filter=Q(nota__lt=4.0)),
        ).filter(Q(promedio__lt=4.5) | Q(reprobadas__gte=2))

        rendimiento_dict = {
            r['estudiante']: {
                'promedio': round(r['promedio'], 1) if r['promedio'] else None,
                'reprobadas': r['reprobadas']
            } for r in alumnos_rendimiento
        }

        # Cruzar para obtener Riesgo Crítico (Bajo rendimiento Y alta inasistencia/atrasos)
        estudiantes_inasistencia_set = {a['estudiante'] for a in alumnos_inasistencia}
        estudiantes_atrasos_set = {a['estudiante'] for a in alumnos_atrasos}
        estudiantes_asistencia_atrasos_set = estudiantes_inasistencia_set.union(estudiantes_atrasos_set)

        alumnos_riesgo_critico = []
        estudiantes_criticos_ids = estudiantes_asistencia_atrasos_set.intersection(rendimiento_dict.keys())
        
        if estudiantes_criticos_ids:
            usuarios_criticos = User.objects.filter(id__in=estudiantes_criticos_ids).values(
                'id', 'nombre', 'apellido_paterno', 'apellido_materno'
            )
            for u in usuarios_criticos:
                est_id = u['id']
                ausencias = next((a['ausencias'] for a in alumnos_inasistencia if a['estudiante'] == est_id), 0)
                atrasos = next((a['atrasos'] for a in alumnos_atrasos if a['estudiante'] == est_id), 0)
                
                alumnos_riesgo_critico.append({
                    'estudiante_id': est_id,
                    'nombre_completo': f"{u['apellido_paterno']} {u['apellido_materno'] or ''}, {u['nombre']}".strip(),
                    'ausencias': ausencias,
                    'atrasos': atrasos,
                    'promedio': rendimiento_dict[est_id]['promedio'],
                    'reprobadas': rendimiento_dict[est_id]['reprobadas']
                })
        
        # Ordenar alumnos en riesgo por promedio de forma ascendente
        alumnos_riesgo_critico.sort(key=lambda x: x['promedio'] if x['promedio'] is not None else 7.0)

        return {
            'entrevistas_semana': entrevistas_semana,
            'seguimientos_pendientes': seguimientos_pendientes,
            'derivaciones_activas': derivaciones_activas,
            'citaciones_pendientes': citaciones_pendientes,
            'casos_bullying_abiertos': casos_bullying_abiertos,
            'alumnos_inasistencia': list(alumnos_inasistencia[:10]),
            'alumnos_atrasos': list(alumnos_atrasos[:10]),
            'alumnos_anotaciones': list(alumnos_anotaciones[:10]),
            'alumnos_riesgo_critico': alumnos_riesgo_critico[:10],
            'total_alertas': len(alumnos_inasistencia) + len(alumnos_anotaciones) + len(alumnos_atrasos),
        }


    @staticmethod
    def _get_entrevistas_context(user, escuela_rbd):
        from backend.apps.core.models import EntrevistaOrientacion

        entrevistas = EntrevistaOrientacion.objects.filter(
            colegio_id=escuela_rbd,
        ).select_related('estudiante', 'psicologo').order_by('-fecha')[:50]

        return {'entrevistas': entrevistas}

    @staticmethod
    def _get_derivaciones_context(user, escuela_rbd):
        from backend.apps.core.models import DerivacionExterna

        derivaciones = DerivacionExterna.objects.filter(
            colegio_id=escuela_rbd,
        ).select_related('estudiante', 'derivado_por').order_by('-fecha_derivacion')[:50]

        activas = DerivacionExterna.objects.filter(
            colegio_id=escuela_rbd,
            estado__in=['PENDIENTE', 'EN_PROCESO'],
        ).count()

        return {
            'derivaciones': derivaciones,
            'derivaciones_activas': activas,
        }

    @staticmethod
    def _get_citaciones_casos_context(user, escuela_rbd):
        from backend.apps.core.models import CitacionApoderado, CasoBullyingConvivencia
        from backend.apps.accounts.models import User

        # Lista de estudiantes activos del colegio para el selector
        estudiantes = User.objects.filter(
            rbd_colegio=escuela_rbd,
            role__nombre__in=['Alumno', 'Estudiante'],
            is_active=True,
        ).order_by('apellido_paterno', 'nombre')[:200]

        citaciones = CitacionApoderado.objects.filter(
            colegio_id=escuela_rbd,
        ).select_related('estudiante', 'solicitado_por').order_by('-fecha_citacion')[:50]

        casos = CasoBullyingConvivencia.objects.filter(
            colegio_id=escuela_rbd,
        ).select_related('estudiante_implicado', 'registrado_por').order_by('-fecha_registro')[:50]

        return {
            'estudiantes': estudiantes,
            'citaciones': citaciones,
            'casos': casos,
            'tipos_falta_choices': CasoBullyingConvivencia.TIPOS,
            'estados_caso_choices': CasoBullyingConvivencia.ESTADOS,
            'estados_citacion_choices': CitacionApoderado.ESTADOS,
        }

    @staticmethod
    def _get_ficha_estudiante_context(user, escuela_rbd, get_params=None):
        """Vista 360° del estudiante: notas + asistencia + anotaciones + entrevistas."""
        from backend.apps.core.models import (
            EntrevistaOrientacion, AnotacionConvivencia, DerivacionExterna,
        )
        from backend.apps.academico.models import Calificacion, Asistencia
        from backend.apps.accounts.models import User

        # Lista de estudiantes para seleccionar
        estudiantes = User.objects.filter(
            rbd_colegio=escuela_rbd,
            role__nombre__iexact='Alumno',
            is_active=True,
        ).select_related('role').order_by('apellido_paterno', 'nombre')[:200]

        estudiante_seleccionado = None
        ficha = {}

        estudiante_id = (get_params or {}).get('estudiante_id')
        if estudiante_id:
            try:
                estudiante_seleccionado = User.objects.get(
                    id=estudiante_id,
                    rbd_colegio=escuela_rbd,
                    is_active=True,
                )

                # Calificaciones
                calificaciones_qs = Calificacion.objects.filter(
                    estudiante=estudiante_seleccionado,
                    colegio_id=escuela_rbd,
                )
                total_notas = calificaciones_qs.count()
                promedio_raw = calificaciones_qs.aggregate(p=Avg('nota'))['p']
                promedio = round(promedio_raw, 1) if promedio_raw else None

                # Asistencia
                asistencia_qs = Asistencia.objects.filter(
                    estudiante=estudiante_seleccionado,
                    colegio_id=escuela_rbd,
                )
                total_clases = asistencia_qs.count()
                presentes = asistencia_qs.filter(estado='P').count()
                tasa_asistencia = round(presentes / total_clases * 100, 1) if total_clases > 0 else 0

                # Registros psicológicos
                from backend.apps.core.models import CitacionApoderado, CasoBullyingConvivencia

                anotaciones = AnotacionConvivencia.objects.filter(
                    estudiante=estudiante_seleccionado,
                    colegio_id=escuela_rbd,
                ).order_by('-fecha')[:20]

                entrevistas = EntrevistaOrientacion.objects.filter(
                    estudiante=estudiante_seleccionado,
                    colegio_id=escuela_rbd,
                ).order_by('-fecha')[:20]

                derivaciones = DerivacionExterna.objects.filter(
                    estudiante=estudiante_seleccionado,
                    colegio_id=escuela_rbd,
                ).order_by('-fecha_derivacion')[:20]

                citaciones = CitacionApoderado.objects.filter(
                    estudiante=estudiante_seleccionado,
                    colegio_id=escuela_rbd,
                ).order_by('-fecha_citacion')[:20]

                casos = CasoBullyingConvivencia.objects.filter(
                    estudiante_implicado=estudiante_seleccionado,
                    colegio_id=escuela_rbd,
                ).order_by('-fecha_registro')[:20]

                ficha = {
                    'total_notas': total_notas,
                    'promedio': promedio,
                    'tasa_asistencia': tasa_asistencia,
                    'total_anotaciones': anotaciones.count(),
                    'total_entrevistas': entrevistas.count(),
                    'anotaciones': anotaciones,
                    'entrevistas': entrevistas,
                    'derivaciones': derivaciones,
                    'citaciones': citaciones,
                    'casos_bullying': casos,
                    'es_pie': getattr(estudiante_seleccionado, 'perfil_estudiante', None) and estudiante_seleccionado.perfil_estudiante.requiere_pie,
                }
            except User.DoesNotExist:
                pass

        return {
            'estudiantes': estudiantes,
            'estudiante_seleccionado': estudiante_seleccionado,
            'ficha': ficha,
        }


class DashboardSoporteService:
    """Dashboard del Soporte Técnico Escolar."""

    @staticmethod
    def get_context(user, pagina_solicitada, escuela_rbd):
        handlers = {
            'inicio': DashboardSoporteService._get_inicio_context,
            'tickets': DashboardSoporteService._get_tickets_context,
            'usuarios': DashboardSoporteService._get_usuarios_context,
            'actividad': DashboardSoporteService._get_actividad_context,
        }
        handler = handlers.get(pagina_solicitada, DashboardSoporteService._get_inicio_context)
        try:
            return handler(user, escuela_rbd)
        except Exception as exc:
            logger.error("Error en dashboard soporte [%s]: %s", pagina_solicitada, exc)
            return {'error_context': str(exc)}

    @staticmethod
    def _get_inicio_context(user, escuela_rbd):
        from backend.apps.core.models import TicketSoporte
        from backend.apps.accounts.models import User

        tickets_abiertos = TicketSoporte.objects.filter(
            colegio_id=escuela_rbd,
            estado__in=['ABIERTO', 'EN_PROGRESO'],
        ).count()
        tickets_urgentes = TicketSoporte.objects.filter(
            colegio_id=escuela_rbd,
            estado__in=['ABIERTO', 'EN_PROGRESO'],
            prioridad='URGENTE',
        ).count()
        usuarios_activos = User.objects.filter(
            rbd_colegio=escuela_rbd, is_active=True,
        ).count()
        usuarios_inactivos = User.objects.filter(
            rbd_colegio=escuela_rbd, is_active=False,
        ).count()

        return {
            'tickets_abiertos': tickets_abiertos,
            'tickets_urgentes': tickets_urgentes,
            'usuarios_activos': usuarios_activos,
            'usuarios_inactivos': usuarios_inactivos,
        }

    @staticmethod
    def _get_tickets_context(user, escuela_rbd):
        from backend.apps.core.models import TicketSoporte

        tickets = TicketSoporte.objects.filter(
            colegio_id=escuela_rbd,
        ).select_related('reportado_por', 'asignado_a').order_by('-fecha_creacion')[:50]

        return {'tickets': tickets}

    @staticmethod
    def _get_usuarios_context(user, escuela_rbd):
        from backend.apps.accounts.models import User

        usuarios = User.objects.filter(
            rbd_colegio=escuela_rbd,
        ).select_related('role').order_by('-last_login')[:100]

        return {'usuarios': usuarios}

    @staticmethod
    def _get_actividad_context(user, escuela_rbd):
        """Log de actividad reciente: últimos logins de usuarios del colegio."""
        from backend.apps.accounts.models import User

        hoy = date.today()
        semana_atras = hoy - timedelta(days=7)

        # Últimos logins
        logins_recientes = User.objects.filter(
            rbd_colegio=escuela_rbd,
            last_login__isnull=False,
        ).select_related('role').order_by('-last_login')[:30]

        # Usuarios sin login en >30 días
        hace_30_dias = hoy - timedelta(days=30)
        usuarios_inactivos = User.objects.filter(
            rbd_colegio=escuela_rbd,
            is_active=True,
        ).filter(
            Q(last_login__lt=hace_30_dias) | Q(last_login__isnull=True),
        ).select_related('role').order_by('last_login')[:30]

        # Resumen por rol
        actividad_por_rol = User.objects.filter(
            rbd_colegio=escuela_rbd,
            last_login__gte=semana_atras,
        ).values('role__nombre').annotate(
            activos_semana=Count('id'),
        ).order_by('-activos_semana')

        return {
            'logins_recientes': logins_recientes,
            'usuarios_inactivos': usuarios_inactivos,
            'actividad_por_rol': list(actividad_por_rol),
        }


class DashboardBibliotecarioService:
    """Dashboard del Bibliotecario Digital."""

    @staticmethod
    def get_context(user, pagina_solicitada, escuela_rbd):
        handlers = {
            'inicio': DashboardBibliotecarioService._get_inicio_context,
            'catalogo': DashboardBibliotecarioService._get_catalogo_context,
            'prestamos': DashboardBibliotecarioService._get_prestamos_context,
        }
        handler = handlers.get(pagina_solicitada, DashboardBibliotecarioService._get_inicio_context)
        try:
            return handler(user, escuela_rbd)
        except Exception as exc:
            logger.error("Error en dashboard bibliotecario [%s]: %s", pagina_solicitada, exc)
            return {'error_context': str(exc)}

    @staticmethod
    def _get_inicio_context(user, escuela_rbd):
        from backend.apps.core.models import RecursoDigital, PrestamoRecurso

        total_recursos = RecursoDigital.objects.filter(
            colegio_id=escuela_rbd,
        ).count()
        recursos_publicados = RecursoDigital.objects.filter(
            colegio_id=escuela_rbd, publicado=True,
        ).count()
        prestamos_activos = PrestamoRecurso.objects.filter(
            colegio_id=escuela_rbd, estado='ACTIVO',
        ).count()
        hoy = date.today()
        prestamos_vencidos = PrestamoRecurso.objects.filter(
            colegio_id=escuela_rbd,
            estado='ACTIVO',
            fecha_devolucion_esperada__lt=hoy,
        ).count()

        return {
            'total_recursos': total_recursos,
            'recursos_publicados': recursos_publicados,
            'prestamos_activos': prestamos_activos,
            'prestamos_vencidos': prestamos_vencidos,
        }

    @staticmethod
    def _get_catalogo_context(user, escuela_rbd):
        from backend.apps.core.models import RecursoDigital

        recursos = RecursoDigital.objects.filter(
            colegio_id=escuela_rbd,
        ).select_related('asignatura', 'nivel', 'publicado_por')\
         .order_by('-fecha_creacion')[:50]

        return {'recursos': recursos}

    @staticmethod
    def _get_prestamos_context(user, escuela_rbd):
        from backend.apps.core.models import PrestamoRecurso

        prestamos = PrestamoRecurso.objects.filter(
            colegio_id=escuela_rbd,
        ).select_related('recurso', 'usuario').order_by('-fecha_prestamo')[:50]

        activos = PrestamoRecurso.objects.filter(
            colegio_id=escuela_rbd, estado='ACTIVO',
        ).count()

        return {
            'prestamos': prestamos,
            'prestamos_activos': activos,
        }
