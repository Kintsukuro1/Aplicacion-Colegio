from __future__ import annotations

from django.db import transaction
from rest_framework.exceptions import PermissionDenied, ValidationError

from backend.common.services.policy_service import PolicyService


def _is_global_admin(user) -> bool:
    return PolicyService.has_capability(user, 'SYSTEM_ADMIN')


def _is_teacher_user(user) -> bool:
    role_name = getattr(getattr(user, 'role', None), 'nombre', '') or ''
    return role_name.strip().lower() == 'profesor'


def _ensure_same_school(user, school_id) -> None:
    if _is_global_admin(user):
        return
    if getattr(user, 'rbd_colegio', None) != school_id:
        raise PermissionDenied('No puede operar recursos de otro colegio.')


def _ensure_teacher_owns_class(user, clase) -> None:
    if _is_global_admin(user):
        return
    if _is_teacher_user(user) and clase.profesor_id != user.id:
        raise PermissionDenied('No puede operar una clase asignada a otro profesor.')


class AcademicBatchApiService:
    """Logica de dominio para operaciones batch de endpoints profesor."""

    @staticmethod
    @transaction.atomic
    def bulk_update_attendance_state(*, actor, queryset, ids, target_state, serializer_class) -> dict:
        if not isinstance(ids, list) or not ids:
            raise ValidationError({'ids': 'Debe enviar una lista no vacia de IDs.'})
        if not target_state:
            raise ValidationError({'estado': 'Debe indicar el estado destino.'})

        success = 0
        failed_ids = []
        details = []

        for raw_id in ids:
            try:
                attendance_id = int(raw_id)
                attendance = queryset.filter(pk=attendance_id).first()
                if not attendance:
                    failed_ids.append(attendance_id)
                    details.append({'id': attendance_id, 'status': 'error', 'detail': 'Asistencia no encontrada.'})
                    continue

                _ensure_same_school(actor, attendance.clase.colegio_id)
                _ensure_teacher_owns_class(actor, attendance.clase)

                serializer = serializer_class(attendance, data={'estado': target_state}, partial=True)
                if not serializer.is_valid():
                    failed_ids.append(attendance_id)
                    details.append({'id': attendance_id, 'status': 'error', 'detail': serializer.errors})
                    continue

                serializer.save()
                success += 1
                details.append({'id': attendance_id, 'status': 'ok'})
            except (TypeError, ValueError):
                failed_ids.append(raw_id)
                details.append({'id': raw_id, 'status': 'error', 'detail': 'ID invalido.'})
            except (PermissionDenied, ValidationError) as exc:
                failed_ids.append(raw_id)
                details.append({'id': raw_id, 'status': 'error', 'detail': getattr(exc, 'detail', str(exc))})

        return {
            'success': success,
            'failed': len(failed_ids),
            'failed_ids': failed_ids,
            'results': details,
        }

    @staticmethod
    @transaction.atomic
    def bulk_toggle_evaluation_active(*, queryset, ids, target_active) -> dict:
        if not isinstance(ids, list) or not ids:
            raise ValidationError({'ids': 'Debe enviar una lista no vacia de IDs.'})
        if target_active is None:
            raise ValidationError({'activa': 'Debe indicar si la evaluacion queda activa o inactiva.'})

        if isinstance(target_active, str):
            normalized = target_active.strip().lower()
            if normalized in {'true', '1', 'si', 'yes'}:
                target_active = True
            elif normalized in {'false', '0', 'no'}:
                target_active = False
            else:
                raise ValidationError({'activa': 'Valor invalido para activa.'})
        else:
            target_active = bool(target_active)

        success = 0
        failed_ids = []
        details = []

        for raw_id in ids:
            try:
                evaluation_id = int(raw_id)
                evaluation = queryset.filter(pk=evaluation_id).first()
                if not evaluation:
                    failed_ids.append(evaluation_id)
                    details.append({'id': evaluation_id, 'status': 'error', 'detail': 'Evaluacion no encontrada.'})
                    continue

                if evaluation.activa == target_active:
                    details.append({'id': evaluation_id, 'status': 'skipped', 'detail': 'Sin cambios.'})
                    continue

                evaluation.activa = target_active
                evaluation.save(update_fields=['activa'])
                success += 1
                details.append({'id': evaluation_id, 'status': 'ok'})
            except (TypeError, ValueError):
                failed_ids.append(raw_id)
                details.append({'id': raw_id, 'status': 'error', 'detail': 'ID invalido.'})

        return {
            'success': success,
            'failed': len(failed_ids),
            'failed_ids': failed_ids,
            'results': details,
        }

    @staticmethod
    @transaction.atomic
    def bulk_delete_grades(*, queryset, ids) -> dict:
        if not isinstance(ids, list) or not ids:
            raise ValidationError({'ids': 'Debe enviar una lista no vacia de IDs.'})

        success = 0
        failed_ids = []
        details = []

        for raw_id in ids:
            try:
                grade_id = int(raw_id)
                grade = queryset.filter(pk=grade_id).first()
                if not grade:
                    failed_ids.append(grade_id)
                    details.append({'id': grade_id, 'status': 'error', 'detail': 'Calificacion no encontrada.'})
                    continue

                grade.delete()
                success += 1
                details.append({'id': grade_id, 'status': 'ok'})
            except (TypeError, ValueError):
                failed_ids.append(raw_id)
                details.append({'id': raw_id, 'status': 'error', 'detail': 'ID invalido.'})

        return {
            'success': success,
            'failed': len(failed_ids),
            'failed_ids': failed_ids,
            'results': details,
        }
