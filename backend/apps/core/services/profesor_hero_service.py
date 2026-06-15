"""
Configuración del hero unificado del portal docente por página.
"""
from __future__ import annotations

from datetime import date
from typing import Any, Dict, Optional

from django.db.models import Count, Q


def _hero(
    *,
    eyebrow: str,
    title: str,
    subtitle: str = '',
    hint: str = '',
    aria: str = '',
    metrics_aria: str = 'Resumen',
    greeting: bool = False,
    hide_metrics: bool = False,
    m1_value='0', m1_label='—', m1_mod='clases', m1_alert=False,
    m2_value='0', m2_label='—', m2_mod='tareas', m2_alert=False,
    m3_value='0', m3_label='—', m3_mod='riesgo', m3_alert=False,
    m4_value='0', m4_label='—', m4_mod='asistencia', m4_alert=False,
) -> Dict[str, Any]:
    return {
        'eyebrow': eyebrow,
        'title': title,
        'subtitle': subtitle,
        'hint': hint,
        'aria': aria or title,
        'metrics_aria': metrics_aria,
        'greeting': greeting,
        'hide_metrics': hide_metrics,
        'm1_value': m1_value,
        'm1_label': m1_label,
        'm1_mod': m1_mod,
        'm1_alert': m1_alert,
        'm2_value': m2_value,
        'm2_label': m2_label,
        'm2_mod': m2_mod,
        'm2_alert': m2_alert,
        'm3_value': m3_value,
        'm3_label': m3_label,
        'm3_mod': m3_mod,
        'm3_alert': m3_alert,
        'm4_value': m4_value,
        'm4_label': m4_label,
        'm4_mod': m4_mod,
        'm4_alert': m4_alert,
    }


class ProfesorHeroService:
    @staticmethod
    def operational_kpis(user, colegio=None) -> Dict[str, int]:
        from backend.apps.cursos.models import Clase, BloqueHorario
        from backend.apps.academico.models import Asistencia, Tarea, EntregaTarea

        hoy = date.today()
        dia = hoy.weekday() + 1
        clases_qs = Clase.objects.filter(profesor=user, activo=True)
        if colegio is not None:
            clases_qs = clases_qs.filter(colegio=colegio)

        total_clases = clases_qs.count()
        clases_hoy_ids = list(
            BloqueHorario.objects.filter(
                clase__in=clases_qs,
                dia_semana=dia,
                activo=True,
            ).values_list('clase_id', flat=True).distinct()
        )
        asist_reg = set(
            Asistencia.objects.filter(clase_id__in=clases_hoy_ids, fecha=hoy).values_list(
                'clase_id', flat=True
            )
        )
        tareas_prof = Tarea.objects.filter(clase__in=clases_qs, activa=True)
        por_corregir = EntregaTarea.objects.filter(
            tarea__in=tareas_prof, calificacion__isnull=True
        ).count()

        return {
            'total_clases': total_clases,
            'clases_hoy': len(clases_hoy_ids),
            'asistencias_pendientes': sum(1 for cid in clases_hoy_ids if cid not in asist_reg),
            'por_corregir': por_corregir,
        }

    @staticmethod
    def build(
        pagina: str,
        user,
        colegio=None,
        page_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        ctx = page_context or {}
        kpi = ProfesorHeroService.operational_kpis(user, colegio)
        builders = {
            'inicio': ProfesorHeroService._inicio,
            'mis_clases': ProfesorHeroService._mis_clases,
            'asistencia': ProfesorHeroService._asistencia,
            'notas': ProfesorHeroService._notas,
            'libro_clases': ProfesorHeroService._libro_clases,
            'reportes': ProfesorHeroService._reportes,
            'disponibilidad': ProfesorHeroService._disponibilidad,
            'tareas_consolidado': ProfesorHeroService._tareas_consolidado,
            'mis_planificaciones': ProfesorHeroService._planificaciones,
            'comunicados': ProfesorHeroService._comunicados,
            'calendario_eventos': ProfesorHeroService._calendario,
            'mensajes': ProfesorHeroService._mensajes,
            'perfil': ProfesorHeroService._perfil,
            'solicitud_reuniones': ProfesorHeroService._reuniones,
        }
        builder = builders.get(pagina)
        if builder:
            return builder(user, colegio, ctx, kpi)
        return ProfesorHeroService._generic(pagina, ctx, kpi)

    @staticmethod
    def _inicio(user, colegio, ctx, kpi):
        return _hero(
            eyebrow='Portal docente',
            title='Inicio',
            subtitle='Resumen del día: clases, pendientes y alertas de tus cursos.',
            aria='Inicio docente',
            metrics_aria='Resumen del día',
            greeting=True,
            m1_value=ctx.get('clases_hoy', kpi['clases_hoy']),
            m1_label='Clases hoy',
            m1_mod='clases',
            m2_value=ctx.get('tareas_por_corregir', kpi['por_corregir']),
            m2_label='Por corregir',
            m2_mod='tareas',
            m2_alert=bool(ctx.get('tareas_por_corregir', kpi['por_corregir'])),
            m3_value=ctx.get('estudiantes_riesgo', 0),
            m3_label='En riesgo',
            m3_mod='riesgo',
            m3_alert=bool(ctx.get('estudiantes_riesgo', 0)),
            m4_value=ctx.get('asistencias_pendientes', kpi['asistencias_pendientes']),
            m4_label='Sin pasar lista',
            m4_mod='asistencia',
            m4_alert=bool(ctx.get('asistencias_pendientes', kpi['asistencias_pendientes'])),
        )

    @staticmethod
    def _mis_clases(user, colegio, ctx, kpi):
        return _hero(
            eyebrow='Portal docente',
            title='Mis Clases',
            subtitle='Prioriza pendientes, registra asistencia y entra al detalle de cada curso.',
            aria='Mis Clases',
            metrics_aria='Resumen operativo',
            m1_value=ctx.get('total_clases', kpi['total_clases']),
            m1_label='Clases activas',
            m1_mod='clases',
            m2_value=ctx.get('total_entregas_pendientes', kpi['por_corregir']),
            m2_label='Por corregir',
            m2_mod='tareas',
            m2_alert=bool(ctx.get('total_entregas_pendientes', 0)),
            m3_value=ctx.get('total_alumnos_riesgo', 0),
            m3_label='En riesgo',
            m3_mod='riesgo',
            m3_alert=bool(ctx.get('total_alumnos_riesgo', 0)),
            m4_value=ctx.get('clases_requieren_atencion', 0),
            m4_label='Requieren atención',
            m4_mod='neutral',
            m4_alert=bool(ctx.get('clases_requieren_atencion', 0)),
        )

    @staticmethod
    def _asistencia(user, colegio, ctx, kpi):
        stats = ctx.get('stats_clase') or {}
        clase = ctx.get('clase_seleccionada')
        if clase:
            sub = f"{clase.curso.nombre} · {clase.asignatura.nombre}"
            hint = 'Resumen de los últimos 30 días para la clase seleccionada.'
            if stats.get('periodo_ancorado') and stats.get('periodo_desde'):
                hint = (
                    f"Período {stats['periodo_desde'].strftime('%d/%m/%Y')} – "
                    f"{stats['periodo_hasta'].strftime('%d/%m/%Y')} "
                    '(último historial guardado). Hoy puede no haber registros nuevos.'
                )
        else:
            sub = 'Selecciona clase y fecha para registrar o revisar asistencia.'
            hint = ''
        lista = ctx.get('estudiantes_con_asistencia') or []
        return _hero(
            eyebrow='Académico',
            title='Registro de Asistencia',
            subtitle=sub,
            hint=hint,
            aria='Registro de asistencia',
            metrics_aria='Resumen de asistencia (30 días)',
            m1_value=stats.get('presentes', 0) if stats else '—',
            m1_label='Presentes (30 días)',
            m1_mod='asistencia',
            m2_value=stats.get('ausentes', 0) if stats else '—',
            m2_label='Ausentes',
            m2_mod='riesgo',
            m3_value=stats.get('tardanzas', 0) if stats else '—',
            m3_label='Atrasos',
            m3_mod='warn',
            m4_value=(
                f"{stats.get('porcentaje_asistencia', 0)}%"
                if stats and stats.get('total_registros')
                else (len(lista) if lista else kpi['total_clases'])
            ),
            m4_label='% Asistencia' if stats and stats.get('total_registros') else (
                'En listado' if lista else 'Clases'
            ),
            m4_mod='clases' if not (stats and stats.get('total_registros')) else 'asistencia',
        )

    @staticmethod
    def _notas(user, colegio, ctx, kpi):
        ingresar = ctx.get('modo') == 'calificar'
        title = 'Ingresar calificaciones' if ingresar else 'Evaluaciones y notas'
        return _hero(
            eyebrow='Portal docente',
            title=title,
            subtitle=ctx.get('notas_intel_resumen', 'Gestiona evaluaciones y el registro de calificaciones.'),
            aria=title,
            metrics_aria='Resumen académico',
            m1_value=ctx.get('notas_hero_evaluaciones', 0),
            m1_label='Evaluaciones activas',
            m1_mod='clases',
            m2_value=ctx.get('notas_hero_calificaciones', 0),
            m2_label='Calificaciones',
            m2_mod='tareas',
            m3_value=ctx.get('notas_hero_promedio', '—'),
            m3_label='Promedio',
            m3_mod='neutral',
            m4_value=ctx.get('notas_hero_pendientes', 0),
            m4_label='Por completar',
            m4_mod='riesgo',
            m4_alert=bool(ctx.get('notas_hero_pendientes', 0)),
        )

    @staticmethod
    def _libro_clases(user, colegio, ctx, kpi):
        clases = ctx.get('clases') or []
        n = len(clases) if hasattr(clases, '__len__') else 0
        return _hero(
            eyebrow='Académico',
            title='Libro de Clases',
            subtitle='Matriz de calificaciones y seguimiento por curso.',
            aria='Libro de clases',
            m1_value=n or kpi['total_clases'],
            m1_label='Clases',
            m1_mod='clases',
            m2_value=ctx.get('libro_evaluaciones_count', '—'),
            m2_label='Evaluaciones',
            m2_mod='tareas',
            m3_value=ctx.get('libro_estudiantes_count', '—'),
            m3_label='Estudiantes',
            m3_mod='neutral',
            m4_value=kpi['por_corregir'],
            m4_label='Entregas pend.',
            m4_mod='riesgo',
            m4_alert=bool(kpi['por_corregir']),
        )

    @staticmethod
    def _reportes_metrics(ctx: Dict[str, Any]) -> Dict[str, Any]:
        """Métricas del hero según reporte generado o resumen global del contexto."""
        tipo = ctx.get('tipo_reporte') or 'asistencia'
        data = ctx.get('reporte_data')

        if data and tipo == 'asistencia' and isinstance(data, dict):
            stats = data.get('estadisticas_generales') or {}
            total_reg = stats.get('total_registros') or 0
            if total_reg:
                en_riesgo = sum(
                    1
                    for item in (data.get('asistencia_por_estudiante') or [])
                    if (item.get('porcentaje') or 100) < 70 and (item.get('total_clases') or 0) > 0
                )
                return {
                    'm2_value': f"{stats.get('porcentaje_asistencia', 0)}%",
                    'm2_label': '% Asistencia',
                    'm2_mod': 'asistencia',
                    'm3_value': en_riesgo,
                    'm3_label': 'En riesgo',
                    'm3_mod': 'riesgo',
                    'm3_alert': bool(en_riesgo),
                    'm4_value': total_reg,
                    'm4_label': 'Registros',
                    'm4_mod': 'tareas',
                    'm4_alert': False,
                }

        if data and tipo == 'academico' and isinstance(data, dict):
            if (data.get('total_evaluaciones') or 0) > 0 or (data.get('total_estudiantes') or 0) > 0:
                promedio = data.get('promedio_curso')
                pct_apr = data.get('porcentaje_aprobacion', 0)
                reprobados = data.get('reprobados') or 0
                return {
                    'm2_value': promedio if promedio is not None else '—',
                    'm2_label': 'Promedio curso',
                    'm2_mod': 'neutral',
                    'm2_alert': isinstance(promedio, (int, float)) and promedio < 4.0,
                    'm3_value': data.get('total_evaluaciones', 0),
                    'm3_label': 'Evaluaciones',
                    'm3_mod': 'tareas',
                    'm3_alert': False,
                    'm4_value': f"{pct_apr}%",
                    'm4_label': 'Aprobación',
                    'm4_mod': 'asistencia',
                    'm4_alert': pct_apr < 75 or reprobados > 0,
                }

        return {
            'm2_value': ctx.get('reportes_hero_m2', '—'),
            'm2_label': ctx.get('reportes_hero_m2_label', '% Asistencia'),
            'm2_mod': 'asistencia',
            'm3_value': ctx.get('reportes_hero_m3', '—'),
            'm3_label': ctx.get('reportes_hero_m3_label', 'Evaluaciones'),
            'm3_mod': 'tareas',
            'm3_alert': False,
            'm4_value': ctx.get('reportes_hero_m4', '—'),
            'm4_label': ctx.get('reportes_hero_m4_label', 'Estudiantes'),
            'm4_mod': 'neutral',
            'm4_alert': False,
        }

    @staticmethod
    def _reportes(user, colegio, ctx, kpi):
        clases = ctx.get('clases') or []
        n = len(clases) if hasattr(clases, '__len__') else kpi['total_clases']
        metrics = ProfesorHeroService._reportes_metrics(ctx)
        clase = ctx.get('clase_seleccionada')
        subtitle = (
            f"{clase.curso.nombre} · {clase.asignatura.nombre} — "
            f"{'asistencia del período' if ctx.get('tipo_reporte') == 'asistencia' else 'rendimiento académico'}."
            if clase
            else 'Asistencia y rendimiento por clase. Elige filtros y genera el reporte.'
        )
        return _hero(
            eyebrow='Académico',
            title='Reportes y Estadísticas',
            subtitle=subtitle,
            aria='Reportes',
            metrics_aria='Resumen de reportes',
            m1_value=n,
            m1_label='Clases',
            m1_mod='clases',
            **metrics,
        )

    @staticmethod
    def _disponibilidad(user, colegio, ctx, kpi):
        est = ctx.get('estadisticas') or {}
        return _hero(
            eyebrow='Configuración',
            title='Mi Disponibilidad Horaria',
            subtitle='Bloques en los que puedes dictar clases esta semana.',
            aria='Disponibilidad horaria',
            metrics_aria='Resumen de disponibilidad',
            m1_value=est.get('bloques_disponibles', 0),
            m1_label='Bloques disponibles',
            m1_mod='clases',
            m2_value=est.get('bloques_con_clases', 0),
            m2_label='Con clases',
            m2_mod='tareas',
            m3_value=est.get('bloques_libres', 0),
            m3_label='Bloques libres',
            m3_mod='asistencia',
            m4_value=f"{est.get('porcentaje_disponibilidad', 0)}%",
            m4_label='Disponibilidad',
            m4_mod='neutral',
        )

    @staticmethod
    def _tareas_consolidado(user, colegio, ctx, kpi):
        tareas = ctx.get('tareas') or []
        vencidas = sum(1 for t in tareas if t.get('vencida'))
        baja_entrega = sum(1 for t in tareas if (t.get('porcentaje_entrega') or 0) < 50)
        return _hero(
            eyebrow='Académico',
            title='Tareas Consolidadas',
            subtitle='Estado de entregas en todos tus cursos.',
            aria='Tareas consolidadas',
            m1_value=len(tareas),
            m1_label='Actividades',
            m1_mod='tareas',
            m2_value=vencidas,
            m2_label='Vencidas',
            m2_mod='riesgo',
            m2_alert=vencidas > 0,
            m3_value=baja_entrega,
            m3_label='Baja entrega',
            m3_mod='warn',
            m4_value=kpi['por_corregir'],
            m4_label='Por corregir',
            m4_mod='asistencia',
            m4_alert=bool(kpi['por_corregir']),
        )

    @staticmethod
    def _planificaciones(user, colegio, ctx, kpi):
        stats = ctx.get('stats') or {}
        total = sum(stats.values()) if stats else len(ctx.get('planificaciones') or [])
        return _hero(
            eyebrow='Académico',
            title='Planificación Curricular',
            subtitle='Diseña unidades, rubricas y experiencias de aprendizaje.',
            aria='Planificaciones',
            m1_value=total,
            m1_label='Planificaciones',
            m1_mod='clases',
            m2_value=stats.get('APROBADA', 0),
            m2_label='Aprobadas',
            m2_mod='asistencia',
            m3_value=stats.get('BORRADOR', 0),
            m3_label='Borradores',
            m3_mod='warn',
            m4_value=stats.get('ENVIADA', 0),
            m4_label='En revisión',
            m4_mod='tareas',
        )

    @staticmethod
    def _comunicados(user, colegio, ctx, kpi):
        items = ctx.get('comunicados') or []
        urgentes = sum(
            1 for c in items
            if getattr(c, 'es_urgente', False) or (isinstance(c, dict) and c.get('es_urgente'))
        )
        return _hero(
            eyebrow='Comunicación',
            title='Comunicados y Circulares',
            subtitle='Avisos oficiales y circulares del colegio.',
            aria='Comunicados',
            m1_value=len(items),
            m1_label='Comunicados',
            m1_mod='mensajes',
            m2_value=urgentes,
            m2_label='Urgentes',
            m2_mod='riesgo',
            m2_alert=urgentes > 0,
            m3_value=kpi['total_clases'],
            m3_label='Tus clases',
            m3_mod='clases',
            m4_value=kpi['por_corregir'],
            m4_label='Por corregir',
            m4_mod='tareas',
        )

    @staticmethod
    def _calendario(user, colegio, ctx, kpi):
        eventos = ctx.get('eventos') or ctx.get('eventos_calendario') or []
        n = len(eventos) if hasattr(eventos, '__len__') else 0
        return _hero(
            eyebrow='Académico',
            title='Calendario Escolar',
            subtitle='Eventos académicos, feriados y actividades del colegio.',
            aria='Calendario escolar',
            m1_value=n,
            m1_label='Eventos',
            m1_mod='clases',
            m2_value=kpi['clases_hoy'],
            m2_label='Clases hoy',
            m2_mod='tareas',
            m3_value=kpi['asistencias_pendientes'],
            m3_label='Lista pendiente',
            m3_mod='asistencia',
            m3_alert=bool(kpi['asistencias_pendientes']),
            m4_value=kpi['total_clases'],
            m4_label='Mis clases',
            m4_mod='neutral',
        )

    @staticmethod
    def _mensajes(user, colegio, ctx, kpi):
        no_leidos = ctx.get('no_leidos_count', 0)
        return _hero(
            eyebrow='Comunicación',
            title='Mensajes',
            subtitle=ctx.get(
                'hero_subtitle_mensajes',
                'Comunícate con estudiantes y apoderados de tus clases.',
            ),
            aria='Mensajes profesor',
            metrics_aria='Resumen de mensajería',
            m1_value=no_leidos,
            m1_label='No leídos',
            m1_mod='mensajes',
            m1_alert=bool(no_leidos),
            m2_value=ctx.get('conversaciones_count', 0),
            m2_label='Conversaciones',
            m2_mod='clases',
            m3_value=ctx.get('estudiantes_sin_chat', 0),
            m3_label='Sin chat',
            m3_mod='warn',
            m4_value=ctx.get('total_mensajes_count', 0),
            m4_label='Mensajes',
            m4_mod='neutral',
        )

    @staticmethod
    def _perfil(user, colegio, ctx, kpi):
        return _hero(
            eyebrow='Configuración',
            title='Mi Perfil',
            subtitle='Información personal y preferencias de tu cuenta.',
            aria='Mi perfil',
            hide_metrics=True,
            m1_value=kpi['total_clases'],
            m1_label='Clases',
            m1_mod='clases',
        )

    @staticmethod
    def _reuniones(user, colegio, ctx, kpi):
        pend = ctx.get('reuniones_pendientes', ctx.get('solicitudes_pendientes', 0))
        return _hero(
            eyebrow='Académico',
            title='Solicitud de Reuniones',
            subtitle='Gestiona reuniones con apoderados y equipo del colegio.',
            aria='Solicitud de reuniones',
            m1_value=pend,
            m1_label='Pendientes',
            m1_mod='riesgo',
            m1_alert=bool(pend),
            m2_value=ctx.get('reuniones_confirmadas', 0),
            m2_label='Confirmadas',
            m2_mod='asistencia',
            m3_value=kpi['total_clases'],
            m3_label='Tus clases',
            m3_mod='clases',
            m4_value=kpi['por_corregir'],
            m4_label='Por corregir',
            m4_mod='tareas',
        )

    @staticmethod
    def _generic(pagina, ctx, kpi):
        title = pagina.replace('_', ' ').title()
        return _hero(
            eyebrow='Portal docente',
            title=title,
            subtitle='Gestión académica y comunicación escolar.',
            aria=title,
            m1_value=kpi['total_clases'],
            m1_label='Clases',
            m1_mod='clases',
            m2_value=kpi['por_corregir'],
            m2_label='Por corregir',
            m2_mod='tareas',
            m3_value=kpi['clases_hoy'],
            m3_label='Clases hoy',
            m3_mod='neutral',
            m4_value=kpi['asistencias_pendientes'],
            m4_label='Lista hoy',
            m4_mod='asistencia',
        )

    @staticmethod
    def for_clase_page(clase, page_context: Optional[Dict] = None) -> Dict[str, Any]:
        """Hero para vistas por clase (detalle, registro asistencia, actividades, reporte)."""
        ctx = page_context or {}
        intel = ctx.get('prof_intel') or {}
        metricas = ctx.get('prof_metricas') or {}
        curso = getattr(clase, 'curso', None)
        asig = getattr(clase, 'asignatura', None)
        eyebrow = curso.nombre if curso else 'Clase'
        title = asig.nombre if asig else 'Detalle de clase'
        subtitle = intel.get('estado_hint') or ctx.get(
            'hero_sub_clase',
            f"{curso.nombre if curso else ''} · {asig.nombre if asig else ''}".strip(' ·'),
        )
        if ctx.get('pagina_hero') == 'registro_asistencia':
            return _hero(
                eyebrow='Académico',
                title='Registro de asistencia',
                subtitle=subtitle,
                aria='Registro de asistencia',
                metrics_aria='Resumen del día',
                m1_value=ctx.get('total_estudiantes', 0),
                m1_label='Estudiantes',
                m1_mod='clases',
                m2_value=ctx.get('resumen_presentes', 0),
                m2_label='Presentes',
                m2_mod='asistencia',
                m3_value=ctx.get('resumen_ausentes', 0),
                m3_label='Ausentes',
                m3_mod='riesgo',
                m4_value=ctx.get('resumen_fecha', '—'),
                m4_label='Fecha',
                m4_mod='neutral',
            )
        if ctx.get('pagina_hero') == 'gestionar_tareas':
            return _hero(
                eyebrow='Portal docente · Actividades',
                title='Gestionar actividades',
                subtitle=ctx.get('gt_intel_resumen', 'Tareas y entregas de esta clase.'),
                aria='Gestionar actividades',
                metrics_aria='Resumen de actividades',
                m1_value=ctx.get('gt_total_estudiantes', 0),
                m1_label='Estudiantes',
                m1_mod='clases',
                m2_value=ctx.get('total_tareas', 0),
                m2_label='Actividades',
                m2_mod='tareas',
                m3_value=ctx.get('total_pendientes', 0),
                m3_label='Por revisar',
                m3_mod='riesgo',
                m3_alert=bool(ctx.get('total_pendientes', 0)),
                m4_value=ctx.get('gt_tasa_revision', 0),
                m4_label='% Revisadas',
                m4_mod='asistencia',
            )
        if ctx.get('pagina_hero') == 'entregas_tarea':
            tarea = ctx.get('tarea')
            titulo = getattr(tarea, 'titulo', 'Entregas de la actividad')
            return _hero(
                eyebrow=eyebrow,
                title=titulo[:80],
                subtitle=subtitle,
                aria='Entregas de actividad',
                metrics_aria='Resumen de entregas',
                m1_value=ctx.get('total_estudiantes', 0),
                m1_label='Estudiantes',
                m1_mod='clases',
                m2_value=ctx.get('total_entregas', 0),
                m2_label='Entregas',
                m2_mod='tareas',
                m3_value=ctx.get('entregas_pendientes', 0),
                m3_label='Por calificar',
                m3_mod='riesgo',
                m3_alert=bool(ctx.get('entregas_pendientes', 0)),
                m4_value=ctx.get('entregas_calificadas', 0),
                m4_label='Calificadas',
                m4_mod='asistencia',
            )
        if ctx.get('pagina_hero') == 'reporte_asistencia':
            sg = ctx.get('stats_generales') or {}
            return _hero(
                eyebrow='Académico',
                title='Reporte de asistencia',
                subtitle=subtitle,
                aria='Reporte de asistencia',
                metrics_aria='Resumen del período',
                m1_value=sg.get('total_estudiantes', 0),
                m1_label='Estudiantes',
                m1_mod='clases',
                m2_value=sg.get('promedio_asistencia', 0),
                m2_label='% Asistencia',
                m2_mod='asistencia',
                m3_value=sg.get('total_ausencias', 0),
                m3_label='Ausencias',
                m3_mod='riesgo',
                m4_value=sg.get('total_tardanzas', 0),
                m4_label='Atrasos',
                m4_mod='warn',
            )
        if intel or metricas:
            return _hero(
                eyebrow=eyebrow,
                title=title,
                subtitle=subtitle,
                aria=title,
                metrics_aria='Resumen de la clase',
                m1_value=metricas.get('estudiantes', 0),
                m1_label='Estudiantes',
                m1_mod='clases',
                m2_value=metricas.get('entregas_pendientes', 0),
                m2_label='Por corregir',
                m2_mod='tareas',
                m2_alert=bool(intel.get('entregas_urgente')),
                m3_value=metricas.get('alumnos_riesgo', 0),
                m3_label='En seguimiento',
                m3_mod='riesgo',
                m4_value=intel.get('asistencia_curso_pct', '—'),
                m4_label='Asistencia %',
                m4_mod='asistencia',
            )
        return _hero(
            eyebrow=eyebrow,
            title=title,
            subtitle='Gestiona materiales, tareas, asistencia y mensajes del curso.',
            aria=title,
            hide_metrics=True,
        )
