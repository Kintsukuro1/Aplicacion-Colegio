"""
Core view: gestionar profesores (Admin escolar)

Endpoint POST utilizado por el template admin_escolar/gestionar_profesores.html.
Se encarga de procesar las acciones: crear, editar, eliminar (desactivar) y resetear_password.
"""

from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect

from backend.apps.core.views.admin_escolar._access import can_manage_school_data
from backend.apps.accounts.services.teacher_service import TeacherService
from backend.apps.core.services.dashboard_service import DashboardService


@login_required(login_url="login")
def gestionar_profesores(request):
    if request.method != "POST":
        return redirect("dashboard")

    user_context = DashboardService.get_user_context(request.user, request.session)
    if user_context is None:
        messages.error(request, "Sesión inválida")
        return redirect("accounts:login")

    user_data = user_context.get('data', {})
    rol = user_data.get('rol')
    escuela_rbd = user_data.get('escuela_rbd')

    if not can_manage_school_data(rol, request.user):
        messages.error(request, "Acceso denegado")
        return redirect("dashboard")

    if not escuela_rbd:
        messages.error(request, "No hay escuela asignada")
        return redirect("dashboard")

    accion = (request.POST.get("accion") or "").strip()

    try:
        if accion == "crear":
            success, message, password_temp = TeacherService.create_teacher(
                user=request.user,
                data=request.POST,
                escuela_rbd=escuela_rbd
            )
            if success:
                messages.success(request, f"{message} Contraseña temporal: <strong>{password_temp}</strong>")
            else:
                messages.error(request, message)

        elif accion == "editar":
            profesor_id = int(request.POST.get("id") or 0)
            success, message = TeacherService.update_teacher(
                user=request.user,
                profesor_id=profesor_id,
                data=request.POST,
                escuela_rbd=escuela_rbd
            )
            if success:
                messages.success(request, message)
            else:
                messages.error(request, message)

        elif accion == "eliminar":
            profesor_id = int(request.POST.get("id") or 0)
            success, message = TeacherService.deactivate_teacher(
                user=request.user,
                profesor_id=profesor_id,
                escuela_rbd=escuela_rbd
            )
            if success:
                messages.success(request, message)
            else:
                messages.error(request, message)

        elif accion == "resetear_password":
            profesor_id = int(request.POST.get("id") or 0)
            success, message, password_temp = TeacherService.reset_password(
                user=request.user,
                profesor_id=profesor_id,
                escuela_rbd=escuela_rbd
            )
            if success:
                messages.success(request, f"{message} Nueva contraseña temporal: <strong>{password_temp}</strong>")
            else:
                messages.error(request, message)

        else:
            messages.error(request, "Acción no reconocida")

    except ValueError:
        messages.error(request, "Parámetros inválidos")
    except Exception as e:
        messages.error(request, f"No se pudo procesar la solicitud: {str(e)}")

    if request.POST.get("origen") == "importar_datos":
        return redirect("importar_datos")
    return redirect("/dashboard/?pagina=gestionar_profesores")
