"""Vistas de Gestión de Datos (Importar/Insertar).

Migrado de forma mínima desde `sistema_antiguo/core/views.py::importar_datos`.
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from backend.apps.core.services.import_csv_service import ImportacionCSVService
from backend.common.services.policy_service import PolicyService


@login_required(login_url="accounts:login")
def importar_datos(request):
    """Página principal de gestión de datos (admin escolar)."""

    can_configure_school = PolicyService.has_capability(request.user, 'SYSTEM_CONFIGURE')
    is_system_admin = PolicyService.has_capability(request.user, 'SYSTEM_ADMIN')

    # Permitir tanto Admin Escolar (SYSTEM_CONFIGURE) como Admin General (SYSTEM_ADMIN).
    if not (can_configure_school or is_system_admin):
        messages.error(request, "No tienes permisos para acceder a esta sección")
        return redirect("dashboard")

    from backend.apps.core.views.school_context import resolve_request_rbd
    from backend.apps.institucion.models import Colegio
    from backend.common.utils.dashboard_helpers import build_dashboard_context

    if is_system_admin:
        # Administrador General debe haber seleccionado un colegio explícitamente en la sesión
        rbd = request.session.get('admin_rbd_activo')
        if not rbd:
            messages.warning(request, "Debe seleccionar un colegio primero para gestionar e importar datos.")
            return redirect('seleccionar_escuela')
    else:
        rbd = resolve_request_rbd(request)

    colegio = None
    if rbd:
        try:
            colegio = Colegio.objects.get(rbd=rbd)
        except Colegio.DoesNotExist:
            pass

    if colegio is None:
        messages.error(request, "No se pudo determinar el colegio del usuario o no existe.")
        return redirect("seleccionar_escuela" if is_system_admin else "dashboard")

    dashboard_data = ImportacionCSVService.get_importar_datos_dashboard(colegio.rbd)

    context, redirect_response = build_dashboard_context(
        request,
        pagina_actual="importar_datos",
        content_template="admin_escolar/importar_datos.html"
    )
    if redirect_response:
        return redirect_response

    context.update({
        "colegio": colegio,
        "estudiantes": dashboard_data["estudiantes"],
        "profesores": dashboard_data["profesores"],
        "apoderados": dashboard_data["apoderados"],
        "total_estudiantes": dashboard_data["total_estudiantes"],
        "total_profesores": dashboard_data["total_profesores"],
        "total_apoderados": dashboard_data["total_apoderados"],
    })

    return render(request, "dashboard.html", context)
