from __future__ import annotations

from django.db import transaction

from backend.apps.accounts.models import PerfilEstudiante, Role


class StudentApiService:
    """Encapsula logica de dominio de estudiantes usada por la capa API."""

    @staticmethod
    @transaction.atomic
    def create_student(*, serializer, school_id: int) -> None:
        role, _ = Role.objects.get_or_create(nombre='Estudiante')
        serializer.save(role=role, rbd_colegio=school_id)

    @staticmethod
    @transaction.atomic
    def soft_delete_student(*, student) -> None:
        student.is_active = False
        student.save(update_fields=['is_active'])

    @staticmethod
    @transaction.atomic
    def update_student_profile(*, student, payload: dict, serializer_class):
        profile, _ = PerfilEstudiante.objects.get_or_create(user=student)
        serializer = serializer_class(profile, data=payload, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return serializer.data

    @staticmethod
    @transaction.atomic
    def bulk_deactivate_students(*, queryset, ids: list) -> dict:
        success = 0
        failed_ids = []
        details = []

        for raw_id in ids:
            try:
                student_id = int(raw_id)
                student = queryset.filter(pk=student_id).first()
                if not student:
                    failed_ids.append(student_id)
                    details.append({'id': student_id, 'status': 'error', 'detail': 'Estudiante no encontrado.'})
                    continue

                if not student.is_active:
                    details.append({'id': student_id, 'status': 'skipped', 'detail': 'Estudiante ya inactivo.'})
                    continue

                student.is_active = False
                student.save(update_fields=['is_active'])
                success += 1
                details.append({'id': student_id, 'status': 'ok'})
            except (TypeError, ValueError):
                failed_ids.append(raw_id)
                details.append({'id': raw_id, 'status': 'error', 'detail': 'ID invalido.'})

        return {
            'success': success,
            'failed': len(failed_ids),
            'failed_ids': failed_ids,
            'results': details,
        }
