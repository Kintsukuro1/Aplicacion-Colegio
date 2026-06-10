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

    vista = (request.GET.get("vista") or "").strip().lower()
    tipo = (request.GET.get("tipo") or "").strip().lower()
    insert_tipo = ""
    if vista == "insertar" and tipo in {"estudiante", "profesor", "apoderado"}:
        insert_tipo = tipo

    csv_post_url = ""
    tipo_usuario = ""
    plantilla_csv = ""
    if vista == "csv":
        csv_map = {
            "estudiantes": (
                "Estudiantes",
                "importar_estudiantes_csv",
                ImportacionCSVService.generar_plantilla_estudiantes,
            ),
            "profesores": (
                "Profesores",
                "importar_profesores_csv",
                ImportacionCSVService.generar_plantilla_profesores,
            ),
            "apoderados": (
                "Apoderados",
                "importar_apoderados_csv",
                ImportacionCSVService.generar_plantilla_apoderados,
            ),
        }
        csv_entry = csv_map.get(tipo)
        if csv_entry:
            tipo_usuario, csv_url_name, plantilla_fn = csv_entry
            from django.urls import reverse
            csv_post_url = reverse(csv_url_name)
            plantilla_csv = plantilla_fn()

    context, redirect_response = build_dashboard_context(
        request,
        pagina_actual="importar_datos",
        content_template="admin_escolar/importar_datos.html"
    )
    if redirect_response:
        return redirect_response

    hero_subtitle_import = (
        f"Carga manual o masiva de estudiantes, profesores y apoderados de {colegio.nombre}"
    )

    context.update({
        "colegio": colegio,
        "estudiantes": dashboard_data["estudiantes"],
        "profesores": dashboard_data["profesores"],
        "apoderados": dashboard_data["apoderados"],
        "total_estudiantes": dashboard_data["total_estudiantes"],
        "total_profesores": dashboard_data["total_profesores"],
        "total_apoderados": dashboard_data["total_apoderados"],
        "vista": vista,
        "insert_tipo": insert_tipo,
        "csv_tipo": tipo if vista == "csv" else "",
        "tipo_usuario": tipo_usuario,
        "csv_post_url": csv_post_url,
        "plantilla_csv": plantilla_csv,
        "hero_subtitle_import": hero_subtitle_import,
        "adm_portal": context.get("rol") in {"admin_general", "Administrador general"},
    })

    return render(request, "dashboard.html", context)
