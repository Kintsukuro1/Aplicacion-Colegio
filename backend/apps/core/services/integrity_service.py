"""
Servicio de auditoría y validación de integridad del dominio.

Este servicio es de solo consulta: no modifica datos ni lanza exceptions.
Su objetivo es detectar estados inválidos para prevenir propagación de corrupción.
"""

from backend.apps.accounts.models import User
from backend.apps.cursos.models import Clase, Curso
from backend.apps.institucion.models import CicloAcademico
from backend.apps.matriculas.models import Matricula
from backend.common.constants import CICLO_ESTADO_ACTIVO
from backend.common.exceptions import PrerequisiteException


class IntegrityService:
    """Validaciones estructurales de integridad por colegio y globales."""

    @staticmethod
    def _build_repair_guidance(school_id):
        guidance = {
            'repair_service': 'DataRepairService',
            'repair_dry_run_available': True,
            'repair_operation': 'repair_all',
            'repair_params': {
                'rbd_colegio': str(school_id),
                'dry_run': True,
            },
            'estimated_corrections': None,
            'estimated_corrections_by_category': {},
        }

        try:
            from backend.apps.core.services.data_repair_service import DataRepairService

            dry_run_report = DataRepairService().repair_all(
                rbd_colegio=str(school_id),
                dry_run=True,
            )
            categories = dry_run_report.get('categories', {})
            guidance['estimated_corrections'] = dry_run_report.get('total_corrections', 0)
            guidance['estimated_corrections_by_category'] = {
                category: values.get('count', 0)
                for category, values in categories.items()
                if isinstance(values, dict)
            }
        except Exception as exc:
            guidance['repair_preview_error'] = str(exc)

        return guidance

    @staticmethod
    def _resolve_school_id(colegio_or_school_id):
        if hasattr(colegio_or_school_id, 'rbd'):
            return int(colegio_or_school_id.rbd)
        return int(colegio_or_school_id)

    @staticmethod
    def _validate_critical_operation(colegio_or_school_id, action: str):
        school_id = IntegrityService._resolve_school_id(colegio_or_school_id)
        IntegrityService.validate_school_integrity_or_raise(
            school_id=school_id,
            action=action,
        )

    @staticmethod
    def _raise_integrity_exception(school_id, action, errors):
        repair_guidance = IntegrityService._build_repair_guidance(school_id)
        raise PrerequisiteException(
            error_type='DATA_INCONSISTENCY',
            context={
                'school_id': school_id,
                'action': action,
                'integrity_errors': errors,
                'message': 'Se detectaron inconsistencias de datos. Corrige la integridad antes de continuar.',
                **repair_guidance,
            }
        )

    @staticmethod
    def _validate_critical_operation_allowing_bootstrap(
        colegio_or_school_id,
        action: str,
        *,
        ignored_errors: tuple[str, ...],
    ):
        school_id = IntegrityService._resolve_school_id(colegio_or_school_id)
        errors = IntegrityService.validate_school_integrity(school_id)
        blocking_errors = [
            error for error in errors
            if not any(error.startswith(ignored) for ignored in ignored_errors)
        ]
        if blocking_errors:
            IntegrityService._raise_integrity_exception(school_id, action, blocking_errors)

    @staticmethod
    def execute(operation, params=None):
        if params is None:
            params = {}
        IntegrityService.validate(operation, params)
        return IntegrityService._execute(operation, params)

    @staticmethod
    def validate(operation, params):
        if not isinstance(operation, str) or not operation.strip():
            raise ValueError('Parámetro requerido: operation')
        if not isinstance(params, dict):
            raise ValueError('Parámetro inválido: params debe ser dict')

    @staticmethod
    def _execute(operation, params):
        handler = getattr(IntegrityService, f'_execute_{operation}', None)
        if callable(handler):
            return handler(params)
        raise ValueError(f'Operación no soportada: {operation}')

    # Per-request cache for integrity validation results.
    # Cleared at the start of each request by middleware or manually.
    # Key: school_id, Value: list of errors (empty = valid)
    _integrity_cache: dict = {}

    @staticmethod
    def validate_school_integrity_or_raise(school_id, action='UNSPECIFIED_ACTION'):
        """
        Valida integridad de colegio y lanza error estructurado si hay inconsistencias.

        Uses per-request cache to avoid running the full integrity report multiple
        times for the same school_id within a single request (~8 queries saved).

        Args:
            school_id (int): RBD del colegio
            action (str): Acción de negocio que se intenta ejecutar

        Raises:
            PrerequisiteException: Si se detectan inconsistencias de integridad
        """
        cache_key = int(school_id) if school_id is not None else None
        if cache_key in IntegrityService._integrity_cache:
            errors = IntegrityService._integrity_cache[cache_key]
        else:
            errors = IntegrityService.validate_school_integrity(school_id)
            IntegrityService._integrity_cache[cache_key] = errors

        if not errors:
            return
        IntegrityService._raise_integrity_exception(school_id, action, errors)

    @staticmethod
    def clear_cache():
        """Clear the per-request integrity cache. Call at request start or end."""
        IntegrityService._integrity_cache.clear()

    @staticmethod
    def validate_curso_creation(colegio_or_school_id):
        IntegrityService._validate_critical_operation_allowing_bootstrap(
            colegio_or_school_id,
            'CURSO_CREATE',
            ignored_errors=(
                'No active academic cycle',
                'No courses exist',
            ),
        )

    @staticmethod
    def validate_curso_update(colegio_or_school_id):
        IntegrityService._validate_critical_operation(colegio_or_school_id, 'CURSO_UPDATE')

    @staticmethod
    def validate_curso_deletion(colegio_or_school_id):
        IntegrityService._validate_critical_operation(colegio_or_school_id, 'CURSO_DELETE')

    @staticmethod
    def validate_ciclo_creation(colegio_or_school_id):
        IntegrityService._validate_critical_operation_allowing_bootstrap(
            colegio_or_school_id,
            'CICLO_CREATE',
            ignored_errors=(
                'No active academic cycle',
                'No courses exist',
            ),
        )

    @staticmethod
    def validate_ciclo_update(colegio_or_school_id):
        IntegrityService._validate_critical_operation(colegio_or_school_id, 'CICLO_UPDATE')

    @staticmethod
    def validate_ciclo_deletion(colegio_or_school_id):
        IntegrityService._validate_critical_operation(colegio_or_school_id, 'CICLO_DELETE')

    @staticmethod
    def validate_clase_creation(colegio_or_school_id):
        IntegrityService._validate_critical_operation(colegio_or_school_id, 'CLASE_CREATE')

    @staticmethod
    def validate_clase_update(colegio_or_school_id):
        IntegrityService._validate_critical_operation(colegio_or_school_id, 'CLASE_UPDATE')

    @staticmethod
    def validate_clase_deletion(colegio_or_school_id):
        IntegrityService._validate_critical_operation(colegio_or_school_id, 'CLASE_DELETE')

    @staticmethod
    def validate_matricula_creation(colegio_or_school_id):
        IntegrityService._validate_critical_operation(colegio_or_school_id, 'MATRICULA_CREATE')

    @staticmethod
    def validate_matricula_update(colegio_or_school_id):
        IntegrityService._validate_critical_operation(colegio_or_school_id, 'MATRICULA_UPDATE')

    @staticmethod
    def validate_matricula_deletion(colegio_or_school_id):
        IntegrityService._validate_critical_operation(colegio_or_school_id, 'MATRICULA_DELETE')

    @staticmethod
    def validate_usuario_creation(colegio_or_school_id):
        IntegrityService._validate_critical_operation(colegio_or_school_id, 'USUARIO_CREATE')

    @staticmethod
    def validate_usuario_update(colegio_or_school_id):
        IntegrityService._validate_critical_operation(colegio_or_school_id, 'USUARIO_UPDATE')

    @staticmethod
    def validate_usuario_deletion(colegio_or_school_id):
        IntegrityService._validate_critical_operation(colegio_or_school_id, 'USUARIO_DELETE')

    @staticmethod
    def validate_estudiante_creation(colegio_or_school_id):
        IntegrityService._validate_critical_operation(colegio_or_school_id, 'ESTUDIANTE_CREATE')

    @staticmethod
    def validate_estudiante_update(colegio_or_school_id):
        IntegrityService._validate_critical_operation(colegio_or_school_id, 'ESTUDIANTE_UPDATE')

    @staticmethod
    def validate_estudiante_deletion(colegio_or_school_id):
        IntegrityService._validate_critical_operation(colegio_or_school_id, 'ESTUDIANTE_DELETE')

    @staticmethod
    def validate_profesor_creation(colegio_or_school_id):
        IntegrityService._validate_critical_operation(colegio_or_school_id, 'PROFESOR_CREATE')

    @staticmethod
    def validate_profesor_update(colegio_or_school_id):
        IntegrityService._validate_critical_operation(colegio_or_school_id, 'PROFESOR_UPDATE')

    @staticmethod
    def validate_profesor_deletion(colegio_or_school_id):
        IntegrityService._validate_critical_operation(colegio_or_school_id, 'PROFESOR_DELETE')

    @staticmethod
    def validate_asistencia_creation(colegio_or_school_id):
        IntegrityService._validate_critical_operation(colegio_or_school_id, 'ASISTENCIA_CREATE')

    @staticmethod
    def validate_asistencia_update(colegio_or_school_id):
        IntegrityService._validate_critical_operation(colegio_or_school_id, 'ASISTENCIA_UPDATE')

    @staticmethod
    def validate_asistencia_deletion(colegio_or_school_id):
        IntegrityService._validate_critical_operation(colegio_or_school_id, 'ASISTENCIA_DELETE')

    @staticmethod
    def validate_calificaciones_creation(colegio_or_school_id):
        IntegrityService._validate_critical_operation(colegio_or_school_id, 'CALIFICACIONES_CREATE')

    @staticmethod
    def validate_calificaciones_update(colegio_or_school_id):
        IntegrityService._validate_critical_operation(colegio_or_school_id, 'CALIFICACIONES_UPDATE')

    @staticmethod
    def validate_calificaciones_deletion(colegio_or_school_id):
        IntegrityService._validate_critical_operation(colegio_or_school_id, 'CALIFICACIONES_DELETE')

    @staticmethod
    def validate_colegio_update(colegio_or_school_id):
        IntegrityService._validate_critical_operation(colegio_or_school_id, 'COLEGIO_UPDATE')

    @staticmethod
    def validate_colegio_deletion(colegio_or_school_id):
        IntegrityService._validate_critical_operation(colegio_or_school_id, 'COLEGIO_DELETE')

    @staticmethod
    def validate_school_integrity(school_id):
        """
        Retorna lista de errores de integridad de alto nivel para un colegio.

        Args:
            school_id (int): RBD del colegio

        Returns:
            list[str]: Lista de errores detectados
        """
        report = IntegrityService.get_school_integrity_report(school_id)
        return report["errors"]

    @staticmethod
    def get_school_integrity_report(school_id):
        """
        Genera reporte detallado de integridad para un colegio.

        Checks incluidos:
        - Ciclo académico activo
        - Existencia de cursos
        - Cursos sin ciclo
        - Clases sin profesor
        - Matrículas inválidas
        - Relaciones rotas entre entidades
        """
        errors = []
        details = {
            "courses_without_cycle": 0,
            "classes_without_teacher": 0,
            "invalid_enrollments": 0,
            "broken_relationships": 0,
        }

        has_active_cycle = CicloAcademico.objects.filter(
            colegio_id=school_id,
            estado=CICLO_ESTADO_ACTIVO,
        ).exists()
        if not has_active_cycle:
            errors.append("No active academic cycle")

        courses_qs = Curso.objects.filter(colegio_id=school_id)
        if not courses_qs.exists():
            errors.append("No courses exist")

        courses_without_cycle_count = courses_qs.filter(ciclo_academico__isnull=True).count()
        if courses_without_cycle_count > 0:
            errors.append(f"Courses without academic cycle: {courses_without_cycle_count}")
            details["courses_without_cycle"] = courses_without_cycle_count

        classes_without_teacher_count = Clase.objects.filter(
            colegio_id=school_id,
            activo=True,
            profesor__isnull=True,
        ).count()
        if classes_without_teacher_count > 0:
            errors.append(f"Active classes without assigned teacher: {classes_without_teacher_count}")
            details["classes_without_teacher"] = classes_without_teacher_count

        invalid_enrollment_count = IntegrityService._count_invalid_enrollments(school_id)
        if invalid_enrollment_count > 0:
            errors.append(f"Invalid enrollments detected: {invalid_enrollment_count}")
            details["invalid_enrollments"] = invalid_enrollment_count

        broken_relationship_count = IntegrityService._count_broken_relationships(school_id)
        if broken_relationship_count > 0:
            errors.append(f"Broken relationships detected: {broken_relationship_count}")
            details["broken_relationships"] = broken_relationship_count

        return {
            "school_id": school_id,
            "is_valid": len(errors) == 0,
            "errors": errors,
            "details": details,
        }

    @staticmethod
    def get_system_integrity_report():
        """
        Genera reporte de integridad para todo el sistema agrupado por colegio.
        """
        school_ids = set(
            Curso.objects.values_list("colegio_id", flat=True)
        ) | set(
            Clase.objects.values_list("colegio_id", flat=True)
        ) | set(
            Matricula.objects.values_list("colegio_id", flat=True)
        ) | set(
            CicloAcademico.objects.values_list("colegio_id", flat=True)
        )

        per_school_reports = []
        invalid_schools = 0

        for school_id in sorted(school_ids):
            school_report = IntegrityService.get_school_integrity_report(school_id)
            if not school_report["is_valid"]:
                invalid_schools += 1
            per_school_reports.append(school_report)

        return {
            "total_schools_analyzed": len(per_school_reports),
            "invalid_schools": invalid_schools,
            "valid_schools": len(per_school_reports) - invalid_schools,
            "schools": per_school_reports,
        }

    @staticmethod
    def _count_invalid_enrollments(school_id):
        """Cuenta matrículas inválidas para un colegio."""
        invalid_count = 0

        enrollments = Matricula.objects.filter(
            colegio_id=school_id,
        ).select_related("curso", "ciclo_academico")

        for enrollment in enrollments:
            if enrollment.estado == "ACTIVA" and enrollment.curso is None:
                invalid_count += 1
                continue

            if enrollment.curso and not enrollment.curso.activo and enrollment.estado == "ACTIVA":
                invalid_count += 1
                continue

            if enrollment.curso and enrollment.curso.colegio_id != school_id:
                invalid_count += 1
                continue

            if enrollment.ciclo_academico and enrollment.ciclo_academico.colegio_id != school_id:
                invalid_count += 1
                continue

            if enrollment.curso and enrollment.ciclo_academico:
                if enrollment.curso.ciclo_academico_id != enrollment.ciclo_academico_id:
                    invalid_count += 1

        return invalid_count

    @staticmethod
    def _count_broken_relationships(school_id):
        """Cuenta relaciones inválidas entre entidades de dominio."""
        broken_count = 0

        classes = Clase.objects.filter(
            colegio_id=school_id,
        ).select_related("curso", "asignatura", "profesor")

        for clase in classes:
            if clase.curso and clase.curso.colegio_id != school_id:
                broken_count += 1

            if clase.asignatura and clase.asignatura.colegio_id != school_id:
                broken_count += 1

            if clase.profesor and clase.profesor.rbd_colegio != school_id:
                broken_count += 1

        profesor_ids = (
            User.objects.filter(
                rbd_colegio=school_id,
                perfil_profesor__isnull=False,
            )
            .values_list("id", flat=True)
        )

        classes_with_teacher_not_profesor = Clase.objects.filter(
            colegio_id=school_id,
            profesor__isnull=False,
        ).exclude(profesor_id__in=profesor_ids)

        broken_count += classes_with_teacher_not_profesor.count()

        return broken_count
