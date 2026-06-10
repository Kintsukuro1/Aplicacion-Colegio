from __future__ import annotations

from backend.apps.accounts.models import DisponibilidadProfesor
from backend.apps.core.services.integrity_service import IntegrityService
from backend.apps.core.services.school_query_service import SchoolQueryService
from backend.apps.cursos.models import BloqueHorario
from backend.common.services.policy_service import PolicyService


class TeacherAvailabilityService:
    @staticmethod
    def save_weekly_availability(*, professor, school_rbd: int, post_data) -> dict:
        can_view_class = PolicyService.has_capability(professor, 'CLASS_VIEW')
        can_manage_class = (
            PolicyService.has_capability(professor, 'CLASS_EDIT')
            or PolicyService.has_capability(professor, 'CLASS_TAKE_ATTENDANCE')
        )
        if not (can_view_class and can_manage_class):
            raise ValueError('Solo los profesores pueden modificar disponibilidad horaria.')

        IntegrityService.validate_school_integrity_or_raise(
            school_id=school_rbd,
            action='TEACHER_AVAILABILITY_UPSERT',
        )

        colegio = SchoolQueryService.get_required_by_rbd(school_rbd)

        bloques_qs = BloqueHorario.objects.filter(
            colegio=colegio,
            activo=True,
        ).order_by('bloque_numero', 'hora_inicio')

        bloques_map: dict[int, tuple] = {}
        for bloque in bloques_qs:
            if bloque.bloque_numero not in bloques_map:
                bloques_map[bloque.bloque_numero] = (bloque.hora_inicio, bloque.hora_fin)

        total_updated = 0
        for dia in range(1, 6):
            for bloque_numero, (hora_inicio, hora_fin) in bloques_map.items():
                campo = f'disponible_{dia}_{bloque_numero}'
                disponible = post_data.get(campo) == 'on'

                disponibilidad, created = DisponibilidadProfesor.objects.get_or_create(
                    profesor=professor,
                    dia_semana=dia,
                    bloque_numero=bloque_numero,
                    defaults={
                        'hora_inicio': hora_inicio,
                        'hora_fin': hora_fin,
                        'disponible': disponible,
                    },
                )

                if created:
                    total_updated += 1
                    continue

                changed = False
                if disponibilidad.disponible != disponible:
                    disponibilidad.disponible = disponible
                    changed = True
                if disponibilidad.hora_inicio != hora_inicio:
                    disponibilidad.hora_inicio = hora_inicio
                    changed = True
                if disponibilidad.hora_fin != hora_fin:
                    disponibilidad.hora_fin = hora_fin
                    changed = True

                if changed:
                    disponibilidad.save(update_fields=['disponible', 'hora_inicio', 'hora_fin'])
                    total_updated += 1

        return {
            'updated': total_updated,
            'slots': len(bloques_map) * 5,
        }
