"""Core view: gestionar estudiantes (Admin escolar)

Endpoint POST utilizado por el template admin_escolar/gestionar_estudiantes.html.
Se mantiene en core para no depender de namespacing (`accounts:...`) mientras dura la migración.

Acciones soportadas (POST): crear, editar, eliminar, asignar_curso, resetear_password.
"""

from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect

from backend.apps.accounts.models import PerfilEstudiante, Role, User
from backend.apps.accounts.services.student_service import StudentService
from backend.apps.core.services.dashboard_service import DashboardService
from backend.apps.cursos.models import Curso


@login_required(login_url="login")
def gestionar_estudiantes(request):
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
        if accion == "crear":
            success, message, _password = StudentService.create_student(
                user=request.user,
                data=request.POST,
                escuela_rbd=escuela_rbd,
                User=User,
                Role=Role,
                PerfilEstudiante=PerfilEstudiante,
            )
            messages.success(request, message) if success else messages.error(request, message)

        elif accion == "editar":
            estudiante_id = int(request.POST.get("id") or 0)
            success, message = StudentService.update_student(
                user=request.user,
                estudiante_id=estudiante_id,
                data=request.POST,
                escuela_rbd=escuela_rbd,
                User=User,
                PerfilEstudiante=PerfilEstudiante,
            )
            messages.success(request, message) if success else messages.error(request, message)

        elif accion == "eliminar":
            estudiante_id = int(request.POST.get("id") or 0)
            success, message = StudentService.deactivate_student(
                user=request.user,
                estudiante_id=estudiante_id,
                escuela_rbd=escuela_rbd,
                User=User,
            )
            messages.success(request, message) if success else messages.error(request, message)

        elif accion == "asignar_curso":
            estudiante_id = int(request.POST.get("estudiante_id") or 0)
            curso_id = int(request.POST.get("curso_id") or 0)
            success, message = StudentService.assign_to_course(
                user=request.user,
                estudiante_id=estudiante_id,
                curso_id=curso_id,
                escuela_rbd=escuela_rbd,
                User=User,
                Curso=Curso,
                PerfilEstudiante=PerfilEstudiante,
            )
            messages.success(request, message) if success else messages.error(request, message)

        elif accion == "resetear_password":
            estudiante_id = int(request.POST.get("id") or 0)
            success, message, _password = StudentService.reset_password(
                user=request.user,
                estudiante_id=estudiante_id,
                escuela_rbd=escuela_rbd,
                User=User,
            )
            messages.success(request, message) if success else messages.error(request, message)

        else:
            messages.error(request, "Acción no reconocida")

    except ValueError:
        messages.error(request, "Parámetros inválidos")
    except Exception:
        messages.error(request, "No se pudo procesar la solicitud")

    return redirect("/dashboard/?pagina=gestionar_estudiantes")
