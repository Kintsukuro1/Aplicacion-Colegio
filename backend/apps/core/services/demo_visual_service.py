"""
Datos de ejemplo solo para la UI (desarrollo / vista previa).
No persiste en base de datos. Solo activo con DEBUG=True.
"""
from __future__ import annotations

from datetime import date, timedelta
from types import SimpleNamespace
from typing import Any, Dict, List, Optional

from django.urls import reverse
from django.utils import timezone


class _DemoEstudiante:
    """Objeto mínimo compatible con templates de asistencia."""

    def __init__(self, pk: int, nombre: str, apellido_paterno: str, apellido_materno: str, email: str):
        self.id = pk
        self.nombre = nombre
        self.apellido_paterno = apellido_paterno
        self.apellido_materno = apellido_materno
        self.email = email
        self.is_active = True

    def get_full_name(self):
        partes = [self.nombre, self.apellido_paterno, self.apellido_materno]
        return ' '.join(p for p in partes if p)


_DEMO_ALUMNOS = [
    ('Ana', 'González', 'López'),
    ('Pedro', 'Contreras', 'Muñoz'),
    ('Sofía', 'Martínez', 'Ríos'),
    ('Diego', 'Silva', 'Torres'),
    ('Valentina', 'Pérez', 'Soto'),
    ('Matías', 'Ramírez', 'Vega'),
    ('Camila', 'Fuentes', 'Díaz'),
    ('Benjamín', 'Morales', 'Castro'),
    ('Javiera', 'Herrera', 'Núñez'),
    ('Tomás', 'Vargas', 'Ortiz'),
    ('Isidora', 'Reyes', 'Campos'),
    ('Lucas', 'Araya', 'Poblete'),
    ('Emilia', 'Carrasco', 'Bravo'),
    ('Maximiliano', 'Sepúlveda', 'Flores'),
]

# Estados de muestra para que el hero y la lista se vean realistas
_DEMO_ESTADOS = ('P', 'P', 'P', 'P', 'P', 'P', 'P', 'T', 'T', 'A', 'J', 'P', 'P', 'P')


def demo_visual_enabled(request) -> bool:
    """
    En desarrollo muestra datos de prueba por defecto.
    ?datos_reales=1 fuerza pantalla vacía/real; ?vista_previa=0 igual.
    """
    from django.conf import settings

    if not getattr(settings, 'DEBUG', False):
        return False
    if request.GET.get('datos_reales') == '1' or request.GET.get('vista_previa') == '0':
        return False
    if request.GET.get('vista_previa') == '1' or request.POST.get('vista_previa') == '1':
        return True
    return True


def use_demo_when_empty(request, tiene_datos_reales: bool) -> bool:
    return demo_visual_enabled(request) and not tiene_datos_reales


def build_demo_asistencia_estudiantes(clase, cantidad: int = 14) -> List[dict]:
    """
    Lista con la misma forma que AttendanceService.get_students_with_attendance.
    IDs negativos para no colisionar con usuarios reales.
    """
    curso = getattr(getattr(clase, 'curso', None), 'nombre', 'el curso')
    items = []
    for idx, (nombre, ap, am) in enumerate(_DEMO_ALUMNOS[:cantidad]):
        pk = -(9000 + idx)
        email = f'demo.{idx + 1}@vista-previa.colegio.cl'
        estudiante = _DemoEstudiante(pk, nombre, ap, am, email)
        estado = _DEMO_ESTADOS[idx % len(_DEMO_ESTADOS)]
        items.append({
            'estudiante': estudiante,
            'asistencia': None,
            'estado': estado,
            'observaciones': 'Ejemplo — sin inscripción en BD' if idx == 0 else '',
            'es_demo': True,
        })
    if items and not items[0]['observaciones']:
        items[0]['observaciones'] = f'Vista previa · {curso}'
    return items


class _DemoPreguntas:
    def count(self):
        return 2


class _DemoActividad:
    def get_modalidad_display(self):
        return 'Mixta'

    @property
    def preguntas(self):
        return _DemoPreguntas()


class _DemoTarea:
    def __init__(self, id_tarea: int, titulo: str, instrucciones: str, fecha_entrega, vencida: bool = False):
        self.id_tarea = id_tarea
        self.titulo = titulo
        self.instrucciones = instrucciones
        self.fecha_entrega = fecha_entrega
        self.archivo_instrucciones = None
        self._vencida = vencida

    def esta_vencida(self):
        return self._vencida


def build_demo_tareas_items(clase, total_estudiantes: int = 18) -> List[dict]:
    """Ítems con la misma forma que _build_item_tarea (ids negativos)."""
    now = timezone.now()
    asignatura = getattr(getattr(clase, 'asignatura', None), 'nombre', 'la asignatura')
    specs = [
        ('Tarea 1 — Vocabulario unidad 3', 'Estudiar vocabulario y preparar oral.', 5, 12, 1, 0, False),
        ('Tarea 2 — Comprensión lectora', 'Leer el cuento y responder preguntas guía.', 8, 14, 2, 1, False),
        ('Prueba formativa — Listening', 'Escuchar el audio y completar la ficha.', 3, 6, 0, -4, True),
    ]
    items = []
    for idx, (titulo, instr, entregas, revisadas, pendientes, dias, vencida) in enumerate(specs):
        fecha = now + timedelta(days=dias)
        tarea = _DemoTarea(-(9100 + idx), titulo, instr, fecha, vencida=vencida)
        porcentaje = round((entregas / total_estudiantes) * 100) if total_estudiantes else 0
        items.append({
            'tarea': tarea,
            'actividad_resoluble': _DemoActividad() if idx < 2 else None,
            'total_entregas': entregas,
            'entregas_revisadas': revisadas,
            'entregas_pendientes': pendientes,
            'porcentaje_entrega': min(porcentaje, 100),
            'alumnos_sin_entrega': max(total_estudiantes - entregas, 0),
            'requiere_atencion': pendientes > 0,
            'es_demo': True,
        })
    return items


def build_demo_tareas_inteligencia(clase, tareas_items: List[dict]) -> dict:
    asignatura = getattr(getattr(clase, 'asignatura', None), 'nombre', 'la asignatura')
    curso = getattr(getattr(clase, 'curso', None), 'nombre', '')
    total_entregas = sum(i['total_entregas'] for i in tareas_items)
    total_pendientes = sum(i['entregas_pendientes'] for i in tareas_items)
    total_revisadas = sum(i['entregas_revisadas'] for i in tareas_items)
    return {
        'gt_intel_resumen': (
            f'Vista previa: {len(tareas_items)} actividades de ejemplo en {asignatura}. '
            f'{total_pendientes} entrega(s) simuladas por revisar.'
        ),
        'gt_intel_alertas': [
            {
                'tipo': 'warn',
                'icono': '⏳',
                'titulo': 'Datos de prueba',
                'texto': 'Estos números son solo para ver el diseño. No se guardan en la base de datos.',
            },
        ] if total_pendientes else [],
        'gt_intel_sugerencias': [
            {'icono': '👥', 'texto': f'{18} estudiantes simulados en {curso}.'},
            {'icono': '📋', 'texto': 'Crea una actividad real con el botón «Crear actividad híbrida».'},
        ],
        'gt_total_estudiantes': 18,
        'gt_tareas_vencidas': sum(1 for i in tareas_items if i['tarea'].esta_vencida()),
        'gt_tareas_activas': sum(1 for i in tareas_items if not i['tarea'].esta_vencida()),
        'gt_tasa_revision': round((total_revisadas / max(total_entregas, 1)) * 100) if total_entregas else 0,
        'gt_tarea_prioritaria_id': None,
        'demo_total_entregas': total_entregas,
        'demo_total_pendientes': total_pendientes,
        'demo_total_revisadas': total_revisadas,
    }


def is_demo_tarea_id(tarea_id: Optional[str]) -> bool:
    try:
        return int(tarea_id) < 0
    except (TypeError, ValueError):
        return False


def is_demo_pk(pk) -> bool:
    try:
        return int(pk) < 0
    except (TypeError, ValueError):
        return False


class _DemoMaterial:
    es_demo = True

    def __init__(self, pk: int, titulo: str, descripcion: str, subido_por, *, es_publico: bool = True):
        self.id_material = pk
        self.titulo = titulo
        self.descripcion = descripcion
        self.es_publico = es_publico
        self.fecha_creacion = timezone.now()
        self.subido_por = subido_por
        self.archivo = None

    def get_icono(self):
        return '📄'

    def get_tamanio_legible(self):
        return '1,2 MB'


class _DemoAnuncio:
    es_demo = True

    def __init__(self, pk: int, titulo: str, contenido: str, *, anclado: bool = False):
        self.id_anuncio = pk
        self.titulo = titulo
        self.contenido = contenido
        self.fecha_creacion = timezone.now()
        self.anclado = anclado
        self.archivo_adjunto = None


class _DemoEvaluacion:
    es_demo = True

    def __init__(self, nombre: str, fecha_eval: date, tipo: str = 'Prueba escrita'):
        self.nombre = nombre
        self.titulo = nombre
        self.fecha_evaluacion = fecha_eval
        self._tipo = tipo

    def get_tipo_evaluacion_display(self):
        return self._tipo


class _DemoEntrega:
    es_demo = True

    def __init__(self, estudiante: _DemoEstudiante, tarea: _DemoTarea, fecha_entrega):
        self.estudiante = estudiante
        self.tarea = tarea
        self.fecha_entrega = fecha_entrega
        self.archivo = None


def _demo_estudiantes_sample(n: int = 6) -> List[_DemoEstudiante]:
    out = []
    for idx, (nombre, ap, am) in enumerate(_DEMO_ALUMNOS[:n]):
        out.append(_DemoEstudiante(-(9000 + idx), nombre, ap, am, f'demo.{idx + 1}@vista-previa.colegio.cl'))
    return out


def build_demo_detalle_clase_patches(clase, user) -> Dict[str, Any]:
    """Datos de ejemplo para pestañas del detalle de clase (profesor)."""
    now = timezone.now()
    hoy = date.today()
    estudiantes = _demo_estudiantes_sample(6)
    prof = user

    materiales = [
        _DemoMaterial(-9201, 'Guía unidad 3 — Vocabulario', 'Lista de palabras y ejercicios de repaso.', prof),
        _DemoMaterial(-9202, 'Presentación oral — Tips', 'Diapositivas para la evaluación oral.', prof, es_publico=True),
        _DemoMaterial(-9203, 'Audio listening (borrador)', 'Solo visible para el profesor.', prof, es_publico=False),
    ]

    total_est = 18
    tareas = []
    specs = [
        ('Tarea 1 — Vocabulario unit', 'Estudiar vocabulario de la unidad y preparar oral.', 12, 1, 0, -2, False, True),
        ('Tarea 2 — Comprensión lectora', 'Leer el texto y responder en el cuaderno.', 14, 2, 1, 5, False, False),
        ('Prueba formativa — Listening', 'Completar la ficha después del audio.', 6, 0, 0, -5, True, False),
    ]
    for idx, (titulo, instr, ent, pend, pct_extra, dias, vencida, pronto) in enumerate(specs):
        fecha = now + timedelta(days=dias)
        tarea = _DemoTarea(-(9100 + idx), titulo, instr, fecha, vencida=vencida)
        entregas_count = ent
        pct = min(100, round((entregas_count / total_est) * 100))
        tareas.append({
            'tarea': tarea,
            'entregas_count': entregas_count,
            'pendientes_corregir': pend,
            'pct_entrega': pct,
            'vence_pronto': pronto and not vencida,
            'es_demo': True,
        })

    entregas_pendientes = [
        _DemoEntrega(estudiantes[0], tareas[1]['tarea'], now - timedelta(hours=5)),
        _DemoEntrega(estudiantes[2], tareas[0]['tarea'], now - timedelta(days=1)),
        _DemoEntrega(estudiantes[4], tareas[2]['tarea'], now - timedelta(hours=20)),
    ]

    anuncios = [
        _DemoAnuncio(-9301, 'Recordatorio evaluación oral', 'Traer guía impresa y llegar 5 min antes.', anclado=True),
        _DemoAnuncio(-9302, 'Material nuevo en la pestaña Materiales', 'Revisen la presentación de tips antes del viernes.'),
    ]

    evaluaciones = [
        _DemoEvaluacion('Evaluación oral — Unidad 3', hoy + timedelta(days=7)),
        _DemoEvaluacion('Prueba escrita — Vocabulario', hoy + timedelta(days=14)),
        _DemoEvaluacion('Trabajo grupal — Cartel', hoy + timedelta(days=21), 'Trabajo'),
    ]

    proximas_fechas = []
    for ev in evaluaciones:
        proximas_fechas.append({
            'tipo': 'evaluacion',
            'fecha': ev.fecha_evaluacion,
            'titulo': ev.nombre,
            'subtipo': ev.get_tipo_evaluacion_display(),
        })
    for item in tareas:
        t = item['tarea']
        proximas_fechas.append({
            'tipo': 'tarea',
            'fecha': t.fecha_entrega.date(),
            'titulo': t.titulo,
            'subtipo': 'Entrega',
        })
    proximas_fechas.sort(key=lambda x: x['fecha'])

    horarios_por_dia = {
        'Lunes': {
            'bloques': [{'bloque_numero': 1, 'hora_inicio': '08:00', 'hora_fin': '08:45'}],
            'hora_inicio': '08:00',
            'hora_fin': '08:45',
        },
        'Miércoles': {
            'bloques': [{'bloque_numero': 3, 'hora_inicio': '10:15', 'hora_fin': '11:00'}],
            'hora_inicio': '10:15',
            'hora_fin': '11:00',
        },
    }

    mensajes_contactos = []
    previews = [
        '¿Puedo entregar la tarea mañana?',
        'Gracias por el material de vocabulario',
        None,
        'Consulta sobre la evaluación oral',
        None,
        None,
    ]
    no_leidos_list = [2, 0, 1, 0, 0, 0]
    for idx, est in enumerate(estudiantes):
        mensajes_contactos.append({
            'estudiante': est,
            'tiene_conversacion': idx < 4,
            'conversacion_id': -(9400 + idx) if idx < 4 else None,
            'no_leidos': no_leidos_list[idx],
            'ultimo_preview': previews[idx],
            'es_demo': True,
        })

    return {
        'materiales': materiales,
        'total_materiales': len(materiales),
        'tareas': tareas,
        'total_tareas': len(tareas),
        'entregas_pendientes': entregas_pendientes,
        'total_entregas_pendientes': len(entregas_pendientes),
        'anuncios': anuncios,
        'total_anuncios': len(anuncios),
        'evaluaciones_proximas': evaluaciones,
        'total_estudiantes': total_est,
        'total_bloques': 2,
        'horarios_por_dia': horarios_por_dia,
        'mensajes_clase_contactos': mensajes_contactos,
        'mensajes_clase_no_leidos': sum(no_leidos_list),
        'mensajes_clase_sin_conversar': 2,
        'prof_metricas': {
            'estudiantes': total_est,
            'entregas_pendientes': len(entregas_pendientes),
            'tareas_activas': len(tareas),
            'alumnos_riesgo': 2,
            'materiales': len(materiales),
        },
        'prof_intel': {
            'estado': 'atencion',
            'estado_label': 'Vista previa del curso',
            'estado_hint': 'Datos de ejemplo para diseñar la pantalla — no están en la base de datos.',
            'alertas': [
                '3 entrega(s) de ejemplo esperan calificación.',
                '2 estudiante(s) en seguimiento (simulado).',
            ],
            'accion_sugerida': {
                'titulo': 'Revisar entrega (ejemplo)',
                'detalle': f'{estudiantes[0].get_full_name()} · «{tareas[0]["tarea"].titulo}»',
                'url': None,
                'tab': 'entregas',
                'icono': '✓',
            },
            'proximas_fechas': proximas_fechas,
            'horario_resumen': ['Lunes 08:00–08:45', 'Miércoles 10:15–11:00'],
            'alumnos_riesgo': 2,
            'tareas_vencen_pronto': 1,
            'tareas_vencidas': 1,
            'asistencia_curso_pct': 92,
            'ultimo_material': {'titulo': materiales[0].titulo, 'hace_dias': 2},
            'entregas_urgente': True,
            'tareas_urgente': True,
        },
    }


def apply_demo_detalle_clase_context(request, context: Dict[str, Any], clase) -> Dict[str, Any]:
    """Rellena secciones vacías con datos de prueba (solo DEBUG, profesor)."""
    if not context.get('es_profesor') or context.get('ver_como_alumno'):
        return context
    if not demo_visual_enabled(request):
        return context

    user = request.user
    patches = build_demo_detalle_clase_patches(clase, user)
    applied = False

    if context.get('total_materiales', 0) == 0:
        context['materiales'] = patches['materiales']
        context['total_materiales'] = patches['total_materiales']
        applied = True
    if context.get('total_tareas', 0) == 0:
        context['tareas'] = patches['tareas']
        context['total_tareas'] = patches['total_tareas']
        applied = True
    if context.get('total_entregas_pendientes', 0) == 0:
        context['entregas_pendientes'] = patches['entregas_pendientes']
        context['total_entregas_pendientes'] = patches['total_entregas_pendientes']
        applied = True
    if context.get('total_anuncios', 0) == 0:
        context['anuncios'] = patches['anuncios']
        context['total_anuncios'] = patches['total_anuncios']
        applied = True
    if not context.get('evaluaciones_proximas'):
        context['evaluaciones_proximas'] = patches['evaluaciones_proximas']
        applied = True
    if not context.get('horarios_por_dia'):
        context['horarios_por_dia'] = patches['horarios_por_dia']
        context['total_bloques'] = patches['total_bloques']
        applied = True
    if not context.get('mensajes_clase_contactos'):
        context['mensajes_clase_contactos'] = patches['mensajes_clase_contactos']
        context['mensajes_clase_no_leidos'] = patches['mensajes_clase_no_leidos']
        context['mensajes_clase_sin_conversar'] = patches['mensajes_clase_sin_conversar']
        applied = True
    if context.get('total_estudiantes', 0) == 0:
        context['total_estudiantes'] = patches['total_estudiantes']
        applied = True

    if applied:
        context['prof_metricas'] = {
            **patches['prof_metricas'],
            'materiales': context['total_materiales'],
            'tareas_activas': context['total_tareas'],
            'entregas_pendientes': context['total_entregas_pendientes'],
        }
        intel = dict(patches['prof_intel'])
        intel['entregas_urgente'] = context['total_entregas_pendientes'] > 0
        intel['tareas_urgente'] = context['total_tareas'] > 0
        context['prof_intel'] = intel
        context['detalle_clase_vista_previa'] = True
        context['detalle_clase_salir_demo_url'] = (
            reverse('ver_detalle_clase', kwargs={'clase_id': clase.id}) + '?datos_reales=1'
        )

    return context
