from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
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
    """Formulario de inserción manual integrado en Importar / Exportar."""
    return redirect(f"{reverse('importar_datos')}?vista=insertar&tipo=estudiante")


@login_required
def insertar_profesor_manual(request):
    """Formulario de inserción manual integrado en Importar / Exportar."""
    return redirect(f"{reverse('importar_datos')}?vista=insertar&tipo=profesor")


@login_required
def insertar_apoderado_manual(request):
    """Formulario de inserción manual integrado en Importar / Exportar."""
    return redirect(f"{reverse('importar_datos')}?vista=insertar&tipo=apoderado")


@login_required
def importar_estudiantes_csv(request):
    """Vista para importar estudiantes desde CSV."""
    if not _has_admin_escolar_access(request.user):
        messages.error(request, "No tienes permisos para acceder a esta sección")
        return redirect("dashboard")

    from backend.apps.core.views.school_context import resolve_request_rbd
    from backend.apps.institucion.models import Colegio

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

    return redirect(f"{reverse('importar_datos')}?vista=csv&tipo=estudiantes")


@login_required
def importar_profesores_csv(request):
    """Vista para importar profesores desde CSV."""
    if not _has_admin_escolar_access(request.user):
        messages.error(request, "No tienes permisos para acceder a esta sección")
        return redirect("dashboard")

    from backend.apps.core.views.school_context import resolve_request_rbd
    from backend.apps.institucion.models import Colegio

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

    return redirect(f"{reverse('importar_datos')}?vista=csv&tipo=profesores")


@login_required
def importar_apoderados_csv(request):
    """Vista para importar apoderados desde CSV."""
    if not _has_admin_escolar_access(request.user):
        messages.error(request, "No tienes permisos para acceder a esta sección")
        return redirect("dashboard")

    from backend.apps.core.views.school_context import resolve_request_rbd
    from backend.apps.institucion.models import Colegio

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

    return redirect(f"{reverse('importar_datos')}?vista=csv&tipo=apoderados")


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
    return _redirect_dashboard("gestionar_apoderados", extra_query=f"editar={apoderado_id}")


@login_required
def eliminar_usuario(request, usuario_id: int):
    from backend.apps.accounts.models import User

    if not _has_admin_escolar_access(request.user):
        messages.error(request, "No tienes permisos para realizar esta acción")
        return redirect("importar_datos")

    try:
        usuario = User.objects.get(pk=usuario_id)
    except User.DoesNotExist:
        messages.error(request, "Usuario no encontrado")
        return redirect("importar_datos")

    if usuario.id == request.user.id:
        messages.error(request, "No puedes desactivar tu propia cuenta")
        return redirect("importar_datos")

    usuario.is_active = False
    usuario.save(update_fields=['is_active'])
    messages.success(request, f"Usuario {usuario.email} desactivado correctamente")
    return redirect("importar_datos")
