from __future__ import annotations

import re
from decimal import Decimal
from typing import Any, Dict, List

from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.utils import timezone

try:
    from pypdf import PdfReader
except ImportError:  # pragma: no cover - fallback only
    PdfReader = None

from backend.apps.academico.models import (
    ActividadResoluble,
    Calificacion,
    Evaluacion,
    IntentoResoluble,
    OpcionPreguntaResoluble,
    PreguntaResoluble,
    RespuestaResoluble,
)
from backend.apps.institucion.models import ConfiguracionAcademica


class ResolubleService:
    @staticmethod
    def _normalize_text(value: str) -> str:
        return ' '.join((value or '').strip().lower().split())

    @staticmethod
    def _extract_text_from_pdf(file_obj) -> str:
        if PdfReader is None:
            return ''
        if file_obj is None:
            return ''

        try:
            if hasattr(file_obj, 'open'):
                file_obj.open('rb')
            if hasattr(file_obj, 'seek'):
                file_obj.seek(0)
            reader = PdfReader(file_obj)
            pages_text: List[str] = []
            for page in reader.pages[:10]:
                try:
                    pages_text.append(page.extract_text() or '')
                except Exception:
                    continue
            return '\n'.join(pages_text)
        finally:
            try:
                if hasattr(file_obj, 'seek'):
                    file_obj.seek(0)
            except Exception:
                pass

    @staticmethod
    def _infer_questions_from_pdf_text(pdf_text: str) -> List[Dict[str, Any]]:
        lines = [line.strip() for line in (pdf_text or '').splitlines()]
        lines = [line for line in lines if line]
        if not lines:
            return []

        question_headers = []
        current_block: List[str] = []

        def flush_block():
            if current_block:
                question_headers.append(list(current_block))
                current_block.clear()

        for line in lines:
            if re.match(r'^(\d+|[ivxlcdm]+)[\).\-:]\s+', line, re.IGNORECASE) or line.endswith('?'):
                flush_block()
                current_block.append(line)
            elif current_block:
                current_block.append(line)

        flush_block()

        if not question_headers:
            question_headers = [[line] for line in lines[:4]]

        preguntas: List[Dict[str, Any]] = []
        for orden, block in enumerate(question_headers[:4], 1):
            header = block[0]
            body = block[1:]
            question_text = re.sub(r'^(\d+|[ivxlcdm]+)[\).\-:]\s+', '', header, flags=re.IGNORECASE).strip()
            if not question_text:
                question_text = header

            opciones = []
            clave_detectada = ''
            for line in body:
                option_match = re.match(r'^([A-Da-d]|[1-4])[\).\-:]\s*(.+)$', line)
                if option_match:
                    opciones.append(
                        {
                            'texto': option_match.group(2).strip(),
                            'es_correcta': False,
                            'orden': len(opciones) + 1,
                        }
                    )
                    continue
                answer_match = re.search(r'(?:respuesta\s*correcta|clave|alternativa\s*correcta)\s*[:\-]\s*(.+)$', line, re.IGNORECASE)
                if answer_match:
                    clave_detectada = answer_match.group(1).strip()

            if opciones:
                clave_norm = clave_detectada.strip().upper()
                if clave_norm:
                    letter_match = re.match(r'^([A-D])\b', clave_norm)
                    if letter_match:
                        target_letter = letter_match.group(1)
                        for index, opcion in enumerate(opciones):
                            if chr(65 + index) == target_letter:
                                opcion['es_correcta'] = True
                    else:
                        for opcion in opciones:
                            if ResolubleService._normalize_text(opcion['texto']) == ResolubleService._normalize_text(clave_detectada):
                                opcion['es_correcta'] = True
                preguntas.append(
                    {
                        'tipo': 'opcion_multiple',
                        'enunciado': question_text,
                        'orden': orden,
                        'puntaje_maximo': '1.0',
                        'respuesta_correcta_texto': clave_detectada,
                        'respuesta_correcta_normalizada': clave_detectada,
                        'requiere_revision_docente': not any(opcion['es_correcta'] for opcion in opciones),
                        'activa': True,
                        'opciones': opciones,
                    }
                )
            else:
                preguntas.append(
                    {
                        'tipo': 'respuesta_corta',
                        'enunciado': question_text,
                        'orden': orden,
                        'puntaje_maximo': '1.0',
                        'respuesta_correcta_texto': clave_detectada,
                        'respuesta_correcta_normalizada': clave_detectada,
                        'requiere_revision_docente': True,
                        'activa': True,
                    }
                )

        return preguntas

    @staticmethod
    def build_questions_from_pdf(file_obj) -> List[Dict[str, Any]]:
        return ResolubleService._infer_questions_from_pdf_text(ResolubleService._extract_text_from_pdf(file_obj))

    @staticmethod
    def _resolve_content_type(origen_tipo: str):
        origen_tipo = (origen_tipo or '').strip().lower()
        if origen_tipo == 'tarea':
            from backend.apps.academico.models import Tarea

            return ContentType.objects.get_for_model(Tarea), Tarea
        if origen_tipo == 'evaluacion':
            from backend.apps.academico.models import Evaluacion

            return ContentType.objects.get_for_model(Evaluacion), Evaluacion
        raise ValueError('tipo_origen debe ser tarea o evaluacion')

    @staticmethod
    def _calculate_grade(colegio, score: Decimal, max_score: Decimal) -> Decimal:
        escala = ConfiguracionAcademica.get_escala_para_colegio(colegio)
        nota_minima = Decimal(str(escala['nota_minima']))
        nota_maxima = Decimal(str(escala['nota_maxima']))
        if not max_score or max_score <= 0:
            return nota_minima
        ratio = score / max_score
        nota = nota_minima + ((nota_maxima - nota_minima) * ratio)
        return nota.quantize(Decimal('0.1'))

    @staticmethod
    def _grade_option_response(response: RespuestaResoluble) -> None:
        pregunta = response.pregunta
        option = response.opcion_seleccionada
        correct_option = pregunta.opciones.filter(es_correcta=True).order_by('orden', 'id_opcion').first()
        response.es_correcta = bool(option and correct_option and option_id_matches(option, correct_option))
        response.puntaje_obtenido = pregunta.puntaje_maximo if response.es_correcta else Decimal('0.00')
        response.observaciones = '' if response.es_correcta else 'Respuesta incorrecta.'

    @staticmethod
    def _grade_short_response(response: RespuestaResoluble) -> None:
        pregunta = response.pregunta
        expected = ResolubleService._normalize_text(
            pregunta.respuesta_correcta_normalizada or pregunta.respuesta_correcta_texto
        )
        received = ResolubleService._normalize_text(response.respuesta_texto)
        response.es_correcta = bool(expected and received == expected)
        response.puntaje_obtenido = pregunta.puntaje_maximo if response.es_correcta else Decimal('0.00')
        response.observaciones = '' if response.es_correcta else 'Respuesta no coincide con la clave.'

    @staticmethod
    def create_or_update_activity(*, actor, payload: Dict[str, Any]) -> ActividadResoluble:
        content_type, model_class = ResolubleService._resolve_content_type(payload.get('origen_tipo'))
        origen_id = payload.get('origen_id')
        if not origen_id:
            raise ValueError('origen_id es requerido')

        try:
            origen = model_class.objects.select_related('clase').get(
                pk=origen_id,
                colegio_id=getattr(actor, 'rbd_colegio', None),
            )
        except model_class.DoesNotExist as exc:
            raise ValueError('No se encontró la actividad origen.') from exc

        actor_school_id = getattr(actor, 'rbd_colegio', None)
        if actor_school_id and origen.colegio_id != actor_school_id:
            raise ValueError('La actividad origen no pertenece al colegio del usuario.')

        role_name = getattr(getattr(actor, 'role', None), 'nombre', '')
        if 'prof' in role_name.lower() or 'docent' in role_name.lower():
            clase = getattr(origen, 'clase', None)
            if clase and clase.profesor_id != getattr(actor, 'id', None):
                raise ValueError('La actividad origen no pertenece al profesor actual.')

        preguntas_data = payload.get('preguntas', None)
        modalidad = (payload.get('modalidad') or 'PDF').upper()
        estado = (payload.get('estado') or 'BORRADOR').upper()
        archivo_pdf = payload.get('archivo_pdf')

        inferir_desde_pdf = bool(payload.get('inferir_desde_pdf', False))

        if modalidad == 'PDF' and archivo_pdf and inferir_desde_pdf and preguntas_data is None:
            preguntas_data = ResolubleService.build_questions_from_pdf(archivo_pdf)
        elif modalidad == 'PDF' and archivo_pdf and inferir_desde_pdf and preguntas_data == []:
            preguntas_data = ResolubleService.build_questions_from_pdf(archivo_pdf)

        actividad, created = ActividadResoluble.objects.get_or_create(
            content_type=content_type,
            object_id=origen.pk,
            defaults={
                'colegio': origen.colegio,
                'titulo': payload.get('titulo') or getattr(origen, 'titulo', '') or getattr(origen, 'nombre', ''),
                'modalidad': modalidad,
                'archivo_pdf': payload.get('archivo_pdf') or None,
                'requiere_aprobacion_docente': payload.get('requiere_aprobacion_docente', True),
                'auto_correccion_activa': payload.get('auto_correccion_activa', True),
                'estado': estado,
                'activa': payload.get('activa', True),
            },
        )

        if not created:
            if 'titulo' in payload:
                actividad.titulo = payload.get('titulo') or actividad.titulo
            if 'modalidad' in payload:
                actividad.modalidad = modalidad
            if 'archivo_pdf' in payload:
                actividad.archivo_pdf = payload.get('archivo_pdf')
            if 'requiere_aprobacion_docente' in payload:
                actividad.requiere_aprobacion_docente = bool(payload.get('requiere_aprobacion_docente'))
            if 'auto_correccion_activa' in payload:
                actividad.auto_correccion_activa = bool(payload.get('auto_correccion_activa'))
            if 'estado' in payload:
                actividad.estado = estado
            if 'activa' in payload:
                actividad.activa = bool(payload.get('activa'))
            actividad.save()

        if preguntas_data is not None:
            actividad.preguntas.all().delete()
            for index, pregunta_data in enumerate(preguntas_data, 1):
                pregunta = PreguntaResoluble.objects.create(
                    actividad_resoluble=actividad,
                    tipo=pregunta_data.get('tipo', 'opcion_multiple'),
                    enunciado=pregunta_data.get('enunciado', ''),
                    orden=pregunta_data.get('orden') or index,
                    puntaje_maximo=Decimal(str(pregunta_data.get('puntaje_maximo', '1.00'))),
                    respuesta_correcta_texto=pregunta_data.get('respuesta_correcta_texto', ''),
                    respuesta_correcta_normalizada=pregunta_data.get('respuesta_correcta_normalizada', ''),
                    requiere_revision_docente=bool(pregunta_data.get('requiere_revision_docente', False)),
                    activa=bool(pregunta_data.get('activa', True)),
                )
                for opt_index, option_data in enumerate(pregunta_data.get('opciones') or [], 1):
                    OpcionPreguntaResoluble.objects.create(
                        pregunta=pregunta,
                        texto=option_data.get('texto', ''),
                        es_correcta=bool(option_data.get('es_correcta', False)),
                        orden=option_data.get('orden') or opt_index,
                    )

        return actividad

    @staticmethod
    @transaction.atomic
    def submit_attempt(*, actividad: ActividadResoluble, estudiante, responses: List[Dict[str, Any]]) -> IntentoResoluble:
        if not responses:
            raise ValueError('Debe enviar al menos una respuesta.')

        intento, _created = IntentoResoluble.objects.get_or_create(
            actividad_resoluble=actividad,
            estudiante=estudiante,
            defaults={
                'estado': 'ENVIADO',
            },
        )

        intento.respuestas.all().delete()

        total = Decimal('0.00')
        maximo = Decimal('0.00')
        requiere_revision = False

        preguntas_por_id = {
            pregunta.id_pregunta: pregunta
            for pregunta in actividad.preguntas.filter(activa=True).prefetch_related('opciones')
        }

        for raw_response in responses:
            pregunta = preguntas_por_id.get(int(raw_response.get('pregunta_id') or 0))
            if not pregunta:
                raise ValueError('Pregunta no encontrada.')

            respuesta = RespuestaResoluble(
                intento=intento,
                pregunta=pregunta,
                respuesta_texto=raw_response.get('respuesta_texto', ''),
            )

            opcion_id = raw_response.get('opcion_id') or raw_response.get('opcion_seleccionada_id')
            if opcion_id:
                respuesta.opcion_seleccionada = pregunta.opciones.filter(pk=opcion_id).first()

            if actividad.auto_correccion_activa and pregunta.tipo == 'opcion_multiple':
                ResolubleService._grade_option_response(respuesta)
            elif actividad.auto_correccion_activa and pregunta.tipo == 'respuesta_corta' and not pregunta.requiere_revision_docente:
                ResolubleService._grade_short_response(respuesta)
            else:
                respuesta.puntaje_obtenido = Decimal('0.00')
                respuesta.es_correcta = False
                respuesta.observaciones = 'Pendiente de revisión docente.'
                requiere_revision = True

            if pregunta.requiere_revision_docente or pregunta.tipo == 'abierta':
                requiere_revision = True
                if not respuesta.observaciones:
                    respuesta.observaciones = 'Pendiente de revisión docente.'

            respuesta.save()
            total += respuesta.puntaje_obtenido or Decimal('0.00')
            maximo += pregunta.puntaje_maximo or Decimal('0.00')

        intento.puntaje_maximo = maximo
        intento.puntaje_obtenido = total
        intento.nota_sugerida = ResolubleService._calculate_grade(actividad.colegio, total, maximo)
        intento.requiere_revision_docente = requiere_revision or actividad.requiere_aprobacion_docente
        intento.estado = 'PENDIENTE_APROBACION' if intento.requiere_revision_docente else 'AUTOCORREGIDO'
        intento.fecha_envio = timezone.now()
        intento.save()
        return intento

    @staticmethod
    @transaction.atomic
    def approve_attempt(*, intento: IntentoResoluble, profesor, retroalimentacion: str = '') -> Calificacion:
        intento.aprobado_por = profesor
        intento.retroalimentacion = retroalimentacion or intento.retroalimentacion
        intento.estado = 'APROBADO'
        intento.fecha_revision = timezone.now()
        intento.fecha_aprobacion = intento.fecha_revision
        intento.save(update_fields=['aprobado_por', 'retroalimentacion', 'estado', 'fecha_revision', 'fecha_aprobacion', 'fecha_actualizacion'])

        actividad = intento.actividad_resoluble
        origen = actividad.actividad
        clase = origen.clase
        if isinstance(origen, Evaluacion):
            evaluacion = origen
        else:
            evaluacion, _created = Evaluacion.objects.get_or_create(
                colegio=actividad.colegio,
                clase=clase,
                nombre=f'Tarea: {getattr(origen, "titulo", getattr(origen, "nombre", "Actividad"))}',
                defaults={
                    'fecha_evaluacion': getattr(origen, 'fecha_entrega', timezone.now()).date(),
                    'ponderacion': Decimal('100.00'),
                    'tipo_evaluacion': 'formativa',
                    'activa': True,
                },
            )

        nota = intento.nota_sugerida or ResolubleService._calculate_grade(actividad.colegio, intento.puntaje_obtenido or Decimal('0.00'), intento.puntaje_maximo or Decimal('0.00'))
        calificacion, created = Calificacion.objects.get_or_create(
            colegio=actividad.colegio,
            evaluacion=evaluacion,
            estudiante=intento.estudiante,
            defaults={
                'nota': nota,
                'registrado_por': profesor,
                'actualizado_por': profesor,
            },
        )
        if not created:
            calificacion.nota = nota
            calificacion.actualizado_por = profesor
            calificacion.save(update_fields=['nota', 'actualizado_por', 'fecha_actualizacion'])

        intento.resultado_publicado = calificacion
        intento.save(update_fields=['resultado_publicado'])
        return calificacion


def option_id_matches(option: OpcionPreguntaResoluble, correct_option: OpcionPreguntaResoluble) -> bool:
    return option.pk == correct_option.pk
