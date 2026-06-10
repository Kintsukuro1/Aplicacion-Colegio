"""Core view: gestionar cursos (Admin escolar)

Endpoint POST utilizado por el template admin_escolar/gestionar_cursos.html.
Se implementa en core (URL global) para evitar problemas de namespace durante la migración.

Acciones soportadas (POST):
- crear
- editar
- eliminar (soft delete)
- asignar_estudiantes
- asignar_profesor
"""

from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import redirect

from backend.apps.accounts.models import PerfilEstudiante, User
from backend.apps.core.services.clase_service import ClaseService
from backend.apps.core.services.curso_service import CursoService
from backend.apps.core.services.dashboard_service import DashboardService
from backend.apps.core.services.orm_access_service import ORMAccessService
from backend.apps.core.services.school_query_service import SchoolQueryService
from backend.apps.cursos.models import Asignatura, Clase, Curso
from backend.common.services.onboarding_service import OnboardingService
from backend.common.exceptions import PrerequisiteException


@login_required(login_url="login")
def gestionar_cursos(request):
    if request.method != "POST":
        return redirect("dashboard")

    user_context = DashboardService.get_user_context(request.user, request.session)
    if user_context is None:
        messages.error(request, "Sesión inválida")
        return redirect("accounts:login")

    user_data = user_context.get('data', {})
    rol = user_data.get('rol')
    escuela_rbd = user_data.get('escuela_rbd')

    if rol not in ["admin_general", "admin_escolar"]:
        messages.error(request, "Acceso denegado")
        return redirect("dashboard")

    if not escuela_rbd:
        messages.error(request, "No hay escuela asignada")
        return redirect("dashboard")

    accion = (request.POST.get("accion") or "").strip()

    try:
        colegio = SchoolQueryService.get_required_by_rbd(escuela_rbd)
    except Exception:
        messages.error(request, "No se encontró la escuela")
        return redirect("dashboard")

    try:
        if accion == "crear":
            # Validar prerequisito: Debe existir ciclo académico activo
            validation = OnboardingService.validate_prerequisite('CREATE_CURSO', escuela_rbd)
            if not validation['valid']:
                error = validation['error']
                redirect_url = error['action_url']
                messages.error(request, error['user_message'])
                return redirect(redirect_url)
            
            nombre = (request.POST.get("nombre") or "").strip()
            nivel_id = int(request.POST.get("nivel_id") or 0)
            anio_escolar = int(request.POST.get("anio_escolar") or 0)

            if not nombre or not nivel_id or not anio_escolar:
                messages.error(request, "Faltan campos obligatorios")
                return redirect("/dashboard/?pagina=gestionar_cursos")

            try:
                CursoService.create(
                    user=request.user,
                    school_rbd=escuela_rbd,
                    nombre=nombre,
                    nivel_id=nivel_id,
                )
                messages.success(request, "Curso creado exitosamente")
            except (PrerequisiteException, ValueError) as exc:
                messages.error(request, str(exc))
            except Exception:
                messages.error(request, "No se pudo crear el curso")

        elif accion == "editar":
            curso_id = int(request.POST.get("id") or 0)
            nombre = (request.POST.get("nombre") or "").strip()
            nivel_id = int(request.POST.get("nivel_id") or 0)
            anio_escolar = int(request.POST.get("anio_escolar") or 0)

            if not curso_id or not nombre or not nivel_id or not anio_escolar:
                messages.error(request, "Faltan campos obligatorios")
                return redirect("/dashboard/?pagina=gestionar_cursos")

            try:
                CursoService.update(
                    user=request.user,
                    school_rbd=escuela_rbd,
                    curso_id=curso_id,
                    nombre=nombre,
                    nivel_id=nivel_id,
                )
                messages.success(request, "Curso actualizado")
            except Exception:
                messages.error(request, "No se pudo actualizar el curso")

        elif accion == "eliminar":
            curso_id = int(request.POST.get("id") or 0)
            if not curso_id:
                messages.error(request, "Curso inválido")
                return redirect("/dashboard/?pagina=gestionar_cursos")

            with transaction.atomic():
                curso = CursoService.delete(
                    user=request.user,
                    school_rbd=escuela_rbd,
                    curso_id=curso_id,
                )

            messages.success(request, "Curso desactivado y estudiantes desvinculados")

        elif accion == "asignar_estudiantes":
            # Validar prerequisito: Deben existir cursos creados
            validation = OnboardingService.validate_prerequisite('ASSIGN_ESTUDIANTE', escuela_rbd)
            if not validation['valid']:
                error = validation['error']
                redirect_url = error['action_url']
                messages.error(request, error['user_message'])
                return redirect(redirect_url)
            
            curso_id = int(request.POST.get("curso_id") or 0)
            estudiantes_ids = request.POST.getlist("estudiantes_ids")

            if not curso_id:
                messages.error(request, "Curso inválido")
                return redirect("/dashboard/?pagina=gestionar_cursos")

            try:
                curso = ORMAccessService.get(Curso, id_curso=curso_id, colegio=colegio, activo=True)
            except Exception:
                messages.error(request, "Curso inválido")
                return redirect("/dashboard/?pagina=gestionar_cursos")

            # Solo asigna estudiantes de la escuela actual
            ids_int = []
            for raw in estudiantes_ids:
                try:
                    ids_int.append(int(raw))
                except ValueError:
                    continue

            if not ids_int:
                messages.error(request, "No seleccionaste estudiantes")
                return redirect("/dashboard/?pagina=gestionar_cursos")

            with transaction.atomic():
                CursoService.assign_students(
                    user=request.user,
                    school_rbd=escuela_rbd,
                    curso_id=curso_id,
                    estudiantes_ids=ids_int,
                )

            messages.success(request, f"Estudiantes asignados a {curso.nombre}")

        elif accion == "asignar_profesor":
            # Validar prerequisito: Deben existir cursos creados
            validation = OnboardingService.validate_prerequisite('ASSIGN_PROFESOR', escuela_rbd)
            if not validation['valid']:
                error = validation['error']
                redirect_url = error['action_url']
                messages.error(request, error['user_message'])
                return redirect(redirect_url)
            
            curso_id = int(request.POST.get("curso_id") or 0)
            asignatura_id = int(request.POST.get("asignatura_id") or 0)
            profesor_id = int(request.POST.get("profesor_id") or 0)

            if not curso_id or not asignatura_id or not profesor_id:
                messages.error(request, "Faltan datos para asignar profesor")
                return redirect("/dashboard/?pagina=gestionar_cursos")

            try:
                ClaseService.create(
                    school_rbd=escuela_rbd,
                    curso_id=curso_id,
                    asignatura_id=asignatura_id,
                    profesor_id=profesor_id,
                )
                messages.success(request, "Profesor asignado a la asignatura")
            except Exception:
                messages.error(request, "No se pudo asignar el profesor")

        else:
            messages.error(request, "Acción no reconocida")

    except ValueError:
        messages.error(request, "Parámetros inválidos")
    except Exception:
        messages.error(request, "No se pudo procesar la solicitud")

    return redirect("/dashboard/?pagina=gestionar_cursos")
