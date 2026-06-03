"""Core view: gestionar apoderados (Admin escolar)

Endpoint POST utilizado por el template admin_escolar/gestionar_apoderados.html.
Se mantiene en core para consistencia con otros módulos de gestión.

Acciones soportadas (POST): crear, editar, eliminar, resetear_password.
"""

from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect

from backend.apps.accounts.models import Apoderado, Role, User
from backend.apps.accounts.services.apoderado_service import ApoderadoService
from backend.apps.core.services.dashboard_service import DashboardService


@login_required(login_url="login")
def gestionar_apoderados(request):
    if request.method != "POST":
        return redirect("dashboard")

    user_context = DashboardService.get_user_context(request.user, request.session)
    if user_context is None:
        messages.error(request, "Sesión inválida")
        return redirect("accounts:login")

    user_data = user_context.get('data', {})
    rol = user_data.get('rol')
    escuela_rbd = user_data.get('escuela_rbd')

    if rol not in ["admin", "admin_escolar"]:
        messages.error(request, "Acceso denegado")
        return redirect("dashboard")

    if not escuela_rbd:
        messages.error(request, "No hay escuela asignada")
        return redirect("dashboard")

    accion = (request.POST.get("accion") or "").strip()

    try:
        if accion == "crear":
            success, message, _password = ApoderadoService.create_apoderado(
                user=request.user,
                data=request.POST,
                escuela_rbd=escuela_rbd,
                User=User,
                Role=Role,
                Apoderado=Apoderado,
            )
            messages.success(request, message) if success else messages.error(request, message)

        elif accion == "editar":
            apoderado_id = int(request.POST.get("id") or 0)
            success, message = ApoderadoService.update_apoderado(
                user=request.user,
                apoderado_id=apoderado_id,
                data=request.POST,
                escuela_rbd=escuela_rbd,
                User=User,
                Apoderado=Apoderado,
            )
            messages.success(request, message) if success else messages.error(request, message)

        elif accion == "eliminar":
            apoderado_id = int(request.POST.get("id") or 0)
            success, message = ApoderadoService.deactivate_apoderado(
                user=request.user,
                apoderado_id=apoderado_id,
                escuela_rbd=escuela_rbd,
                User=User,
                Apoderado=Apoderado,
            )
            messages.success(request, message) if success else messages.error(request, message)

        elif accion == "resetear_password":
            apoderado_id = int(request.POST.get("id") or 0)
            success, message, _password = ApoderadoService.reset_password(
                user=request.user,
                apoderado_id=apoderado_id,
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

    return redirect("/dashboard/?pagina=gestionar_apoderados")
