from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse

from backend.apps.core.services.import_csv_service import ImportacionCSVService
from backend.common.services.policy_service import PolicyService


def _redirect_dashboard(pagina: str, extra_query: str | None = None):
    base = reverse("dashboard")
    url = f"{base}?pagina={pagina}"
    if extra_query:
        joiner = "&" if "?" in url else "?"
        url = f"{url}{joiner}{extra_query}"
    return redirect(url)


def _has_admin_escolar_access(user) -> bool:
    can_configure = PolicyService.has_capability(user, "SYSTEM_CONFIGURE")
    is_system_admin = PolicyService.has_capability(user, "SYSTEM_ADMIN")
    return can_configure or is_system_admin


@login_required
def insertar_estudiante_manual(request):
    """Redirige al módulo de gestionar estudiantes con modal de creación abierto."""
    return _redirect_dashboard("gestionar_estudiantes", extra_query="abrir_modal=crear")


@login_required
def insertar_profesor_manual(request):
    """Redirige al módulo de gestionar profesores (pendiente de implementación completa)."""
    messages.info(
        request,
        "⚠️ La inserción manual de profesores está en desarrollo. "
        "Por ahora, puedes usar la importación CSV masiva desde el módulo de Importar Datos."
    )
    return redirect("importar_datos")


@login_required
def insertar_apoderado_manual(request):
    """Redirige al módulo de gestionar apoderados con modal de creación abierto."""
    return _redirect_dashboard("gestionar_apoderados", extra_query="abrir_modal=crear")


@login_required
def importar_estudiantes_csv(request):
    """Vista para importar estudiantes desde CSV."""
    if not _has_admin_escolar_access(request.user):
        messages.error(request, "No tienes permisos para acceder a esta sección")
        return redirect("dashboard")

    from backend.apps.core.views.school_context import resolve_request_rbd
    from backend.apps.institucion.models import Colegio
    from backend.common.utils.dashboard_helpers import build_dashboard_context

    is_system_admin = PolicyService.has_capability(request.user, 'SYSTEM_ADMIN')
    if is_system_admin:
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

    if request.method == "POST":
        archivo = request.FILES.get("archivo_csv")
        
        if not archivo:
            messages.error(request, "No se seleccionó ningún archivo")
            return redirect("importar_estudiantes_csv")

        exitosos, fallidos, errores = ImportacionCSVService.importar_estudiantes(
            archivo, colegio.rbd
        )

        if exitosos > 0:
            messages.success(
                request,
                f"✅ Se importaron {exitosos} estudiante(s) exitosamente"
            )
        
        if fallidos > 0:
            messages.warning(
                request,
                f"⚠️ {fallidos} registro(s) fallaron al importar"
            )
        
        if errores:
            for error in errores[:10]:  # Mostrar máximo 10 errores
                messages.error(request, error)
            if len(errores) > 10:
                messages.error(request, f"... y {len(errores) - 10} errores más")

        return redirect("importar_datos")

    # GET request - mostrar formulario
    context, redirect_response = build_dashboard_context(
        request,
        pagina_actual="importar_datos",
        content_template="admin_escolar/importar_csv.html"
    )
    if redirect_response:
        return redirect_response

    context.update({
        "colegio": colegio,
        "tipo_usuario": "Estudiantes",
        "plantilla_csv": ImportacionCSVService.generar_plantilla_estudiantes(),
    })
    return render(request, "dashboard.html", context)


@login_required
def importar_profesores_csv(request):
    """Vista para importar profesores desde CSV."""
    if not _has_admin_escolar_access(request.user):
        messages.error(request, "No tienes permisos para acceder a esta sección")
        return redirect("dashboard")

    from backend.apps.core.views.school_context import resolve_request_rbd
    from backend.apps.institucion.models import Colegio
    from backend.common.utils.dashboard_helpers import build_dashboard_context

    is_system_admin = PolicyService.has_capability(request.user, 'SYSTEM_ADMIN')
    if is_system_admin:
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

    if request.method == "POST":
        archivo = request.FILES.get("archivo_csv")
        
        if not archivo:
            messages.error(request, "No se seleccionó ningún archivo")
            return redirect("importar_profesores_csv")

        exitosos, fallidos, errores = ImportacionCSVService.importar_profesores(
            archivo, colegio.rbd
        )

        if exitosos > 0:
            messages.success(
                request,
                f"✅ Se importaron {exitosos} profesor(es) exitosamente"
            )
        
        if fallidos > 0:
            messages.warning(
                request,
                f"⚠️ {fallidos} registro(s) fallaron al importar"
            )
        
        if errores:
            for error in errores[:10]:  # Mostrar máximo 10 errores
                messages.error(request, error)
            if len(errores) > 10:
                messages.error(request, f"... y {len(errores) - 10} errores más")

        return redirect("importar_datos")

    # GET request - mostrar formulario
    context, redirect_response = build_dashboard_context(
        request,
        pagina_actual="importar_datos",
        content_template="admin_escolar/importar_csv.html"
    )
    if redirect_response:
        return redirect_response

    context.update({
        "colegio": colegio,
        "tipo_usuario": "Profesores",
        "plantilla_csv": ImportacionCSVService.generar_plantilla_profesores(),
    })
    return render(request, "dashboard.html", context)


@login_required
def importar_apoderados_csv(request):
    """Vista para importar apoderados desde CSV."""
    if not _has_admin_escolar_access(request.user):
        messages.error(request, "No tienes permisos para acceder a esta sección")
        return redirect("dashboard")

    from backend.apps.core.views.school_context import resolve_request_rbd
    from backend.apps.institucion.models import Colegio
    from backend.common.utils.dashboard_helpers import build_dashboard_context

    is_system_admin = PolicyService.has_capability(request.user, 'SYSTEM_ADMIN')
    if is_system_admin:
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

    if request.method == "POST":
        archivo = request.FILES.get("archivo_csv")
        
        if not archivo:
            messages.error(request, "No se seleccionó ningún archivo")
            return redirect("importar_apoderados_csv")

        exitosos, fallidos, errores = ImportacionCSVService.importar_apoderados(
            archivo, colegio.rbd
        )

        if exitosos > 0:
            messages.success(
                request,
                f"✅ Se importaron {exitosos} apoderado(s) exitosamente"
            )
        
        if fallidos > 0:
            messages.warning(
                request,
                f"⚠️ {fallidos} registro(s) fallaron al importar"
            )
        
        if errores:
            for error in errores[:10]:  # Mostrar máximo 10 errores
                messages.error(request, error)
            if len(errores) > 10:
                messages.error(request, f"... y {len(errores) - 10} errores más")

        return redirect("importar_datos")

    # GET request - mostrar formulario
    context, redirect_response = build_dashboard_context(
        request,
        pagina_actual="importar_datos",
        content_template="admin_escolar/importar_csv.html"
    )
    if redirect_response:
        return redirect_response

    context.update({
        "colegio": colegio,
        "tipo_usuario": "Apoderados",
        "plantilla_csv": ImportacionCSVService.generar_plantilla_apoderados(),
    })
    return render(request, "dashboard.html", context)


@login_required
def editar_estudiante(request, estudiante_id: int):
    messages.info(request, "Edita al estudiante desde 'Gestionar Estudiantes'.")
    return _redirect_dashboard("gestionar_estudiantes", extra_query=f"editar={estudiante_id}")


@login_required
def editar_profesor(request, profesor_id: int):
    messages.info(request, "Edita al profesor desde 'Gestionar Profesores'.")
    return _redirect_dashboard("gestionar_profesores", extra_query=f"editar={profesor_id}")


@login_required
def editar_apoderado(request, apoderado_id: int):
    messages.info(request, "Edición de apoderados: pendiente de migración.")
    return redirect("importar_datos")


@login_required
def eliminar_usuario(request, usuario_id: int):
    messages.warning(
        request,
        "Eliminación desde esta pantalla: pendiente de migración. Usa el módulo correspondiente.",
    )
    return redirect("importar_datos")
