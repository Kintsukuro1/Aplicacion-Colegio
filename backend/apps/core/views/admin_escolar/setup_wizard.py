"""
Vista del wizard guiado para configuración inicial del colegio
Guía paso a paso para completar: Ciclo Académico → Cursos → Profesores → Estudiantes

Utiliza Django Forms para validación robusta de todos los datos.
"""
import logging
from datetime import datetime
from decimal import Decimal
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction

from backend.apps.core.services.ciclo_academico_service import CicloAcademicoService
from backend.apps.core.services.curso_service import CursoService
from backend.apps.core.services.school_query_service import SchoolQueryService
from backend.apps.core.services.setup_wizard_query_service import SetupWizardQueryService
from backend.apps.accounts.services.user_service import UserService
from backend.apps.accounts.services.academic_profile_service import AcademicProfileService
from backend.apps.accounts.services.apoderado_service import ApoderadoService
from backend.common.services import PermissionService
from backend.common.services.policy_service import PolicyService
from backend.apps.institucion.models import Colegio
from backend.apps.cursos.models import Asignatura
from backend.common.services.onboarding_service import OnboardingService
from backend.common.constants import (
    CICLO_ESTADO_ACTIVO,
    ROL_PROFESOR,
    ROL_ESTUDIANTE,
    ROL_APODERADO
)
from backend.apps.core.forms.setup_forms import (
    CicloAcademicoForm,
    CursoCreationForm,
    ProfesorCreationForm,
    EstudianteApoderadoForm
)

logger = logging.getLogger(__name__)


@login_required
def setup_wizard(request):
    """
    Vista principal del wizard de configuración
    GET: Muestra el paso actual del wizard
    POST: Procesa el formulario del paso actual y avanza al siguiente
    """
    # Validar permisos
    can_access = PolicyService.has_capability(request.user, 'SYSTEM_ADMIN') or PolicyService.has_capability(
        request.user, 'SYSTEM_CONFIGURE'
    )
    if not can_access:
        can_access = PermissionService.has_permission(
            request.user,
            'ADMINISTRATIVO',
            'MANAGE_SYSTEM',
        )
    if not can_access:
        messages.error(request, "No tienes permisos para acceder al wizard de configuración")
        return redirect('dashboard')
    
    if not request.user.rbd_colegio:
        messages.error(request, "No hay escuela asignada")
        return redirect('dashboard')
    
    escuela_rbd = request.user.rbd_colegio
    colegio = SchoolQueryService.get_by_rbd(escuela_rbd)
    if not colegio:
        messages.error(request, "No se encontró la escuela")
        return redirect('dashboard')
    
    # Obtener estado de configuración
    setup_status = OnboardingService.get_setup_status(escuela_rbd)
    
    # Determinar paso actual (primer paso incompleto)
    current_step = None
    for step in setup_status['steps']:
        if not step['completado']:
            current_step = step
            break
    
    # Si todo está completo, redirigir al checklist
    if not current_step:
        messages.success(request, "¡Felicidades! La configuración inicial está completa.")
        return redirect('setup_checklist')
    
    # Procesar POST según el paso actual
    if request.method == 'POST':
        step_key = current_step['key']
        
        if step_key == 'ciclo_academico':
            return _process_ciclo_step(request, colegio, escuela_rbd)
        elif step_key == 'cursos':
            return _process_cursos_step(request, colegio, escuela_rbd)
        elif step_key == 'profesores':
            return _process_profesores_step(request, colegio, escuela_rbd)
        elif step_key == 'estudiantes':
            return _process_estudiantes_step(request, colegio, escuela_rbd)
    
    # Preparar contexto para el paso actual
    context = _get_step_context(current_step, colegio, setup_status)
    
    return render(request, 'admin_escolar/setup_wizard.html', context)


def _process_ciclo_step(request, colegio, escuela_rbd):
    """Procesa el formulario del paso 1: Ciclo Académico con validación robusta"""
    form = CicloAcademicoForm(request.POST)
    
    if not form.is_valid():
        # Mostrar errores de validación
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(request, f"{field}: {error}")
        return redirect('setup_wizard')
    
    try:
        with transaction.atomic():
            ciclo = CicloAcademicoService.create(
                user=request.user,
                school_rbd=colegio.rbd,
                nombre=form.cleaned_data['nombre'],
                fecha_inicio=form.cleaned_data['fecha_inicio'],
                fecha_fin=form.cleaned_data['fecha_fin'],
                activate=True,
            )
            messages.success(request, f"Ciclo académico '{ciclo.nombre}' creado exitosamente.")
            return redirect('setup_wizard')
    except Exception:
        logger.exception("Error al crear ciclo académico")
        messages.error(request, "Ocurrió un error al crear el ciclo académico. Contacte al administrador.")
        return redirect('setup_wizard')


def _process_cursos_step(request, colegio, escuela_rbd):
    """Procesa el formulario del paso 2: Cursos con validación robusta"""
    form = CursoCreationForm(request.POST)
    
    if not form.is_valid():
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(request, f"{field}: {error}")
        return redirect('setup_wizard')
    
    try:
        nivel = form.cleaned_data['nivel']
        grado = form.cleaned_data['grado']
        letra = form.cleaned_data['letra']
        cantidad = form.cleaned_data.get('cantidad', 1) or 1
        
        ciclo_activo = SetupWizardQueryService.get_active_cycle(
            colegio=colegio,
            estado_activo=CICLO_ESTADO_ACTIVO,
        )
        
        if not ciclo_activo:
            messages.error(request, "No hay ciclo académico activo")
            return redirect('setup_wizard')
        
        # Crear cursos
        with transaction.atomic():
            for i in range(cantidad):
                letra_curso = chr(ord(letra) + i) if cantidad > 1 else letra
                nombre_curso = f"{grado}° {nivel.nombre} {letra_curso}"
                CursoService.create(
                    user=request.user,
                    school_rbd=colegio.rbd,
                    nombre=nombre_curso
                    ,nivel_id=nivel.id_nivel,
                )
            
            msg = f"{cantidad} curso(s) creado(s) exitosamente." if cantidad > 1 else f"Curso {grado}° {letra} creado exitosamente."
            messages.success(request, msg)
            return redirect('setup_wizard')
    except Exception:
        logger.exception("Error al crear cursos")
        messages.error(request, "Ocurrió un error al crear los cursos. Contacte al administrador.")
        return redirect('setup_wizard')


def _process_profesores_step(request, colegio, escuela_rbd):
    """Procesa el formulario del paso 3: Profesores con validación robusta"""
    form = ProfesorCreationForm(request.POST, rbd_colegio=escuela_rbd)
    
    if not form.is_valid():
        for field, errors in form.errors.items():
            for error in errors:
                field_label = form.fields.get(field).label if hasattr(form.fields.get(field, None), 'label') else field
                messages.error(request, f"{field_label}: {error}")
        return redirect('setup_wizard')
    
    try:
        with transaction.atomic():
            # Crear usuario profesor con datos validados
            profesor = UserService.create_user(
                actor=request.user,
                email=form.cleaned_data['email'] or form.cleaned_data['username'],
                password=form.cleaned_data['password'],
                role_name=ROL_PROFESOR,
                nombre=form.cleaned_data['first_name'],
                apellido_paterno=form.cleaned_data['last_name'],
                rut=form.cleaned_data['rut'],
                rbd_colegio=escuela_rbd,
            )

            AcademicProfileService.create_teacher_profile(user=profesor)
            
            messages.success(request, f"Profesor {profesor.get_full_name()} creado exitosamente.")
            return redirect('setup_wizard')
    except Exception:
        logger.exception("Error al crear profesor")
        messages.error(request, "Ocurrió un error al crear el profesor. Contacte al administrador.")
        return redirect('setup_wizard')


def _process_estudiantes_step(request, colegio, escuela_rbd):
    """Procesa el formulario del paso 4: Estudiantes y Apoderados con validación robusta"""
    form = EstudianteApoderadoForm(request.POST, rbd_colegio=escuela_rbd)
    
    if not form.is_valid():
        for field, errors in form.errors.items():
            for error in errors:
                field_label = form.fields.get(field).label if hasattr(form.fields.get(field, None), 'label') else field
                messages.error(request, f"{field_label}: {error}")
        # También mostrar errores no relacionados a un campo específico
        if form.non_field_errors():
            for error in form.non_field_errors():
                messages.error(request, error)
        return redirect('setup_wizard')
    
    try:
        with transaction.atomic():
            # Crear usuario apoderado con datos validados
            apoderado_user = UserService.create_user(
                actor=request.user,
                email=form.cleaned_data['apoderado_email'] or form.cleaned_data['apoderado_username'],
                password=form.cleaned_data['apoderado_password'],
                role_name=ROL_APODERADO,
                nombre=form.cleaned_data['apoderado_first_name'],
                apellido_paterno=form.cleaned_data['apoderado_last_name'],
                rut=form.cleaned_data['apoderado_rut'],
                rbd_colegio=escuela_rbd,
            )
            
            # Crear perfil apoderado
            apoderado = ApoderadoService.create_profile_for_user(apoderado_user)
            
            # Crear usuario estudiante con datos validados
            estudiante = UserService.create_user(
                actor=request.user,
                email=form.cleaned_data['estudiante_email'] or form.cleaned_data['estudiante_username'],
                password=form.cleaned_data['estudiante_password'],
                role_name=ROL_ESTUDIANTE,
                nombre=form.cleaned_data['estudiante_first_name'],
                apellido_paterno=form.cleaned_data['estudiante_last_name'],
                rut=form.cleaned_data['estudiante_rut'],
                rbd_colegio=escuela_rbd,
            )

            AcademicProfileService.create_student_profile(user=estudiante)
            
            # Crear relación apoderado-estudiante con parentesco validado
            ApoderadoService.link_student(
                apoderado=apoderado,
                estudiante=estudiante,
                parentesco=form.cleaned_data['parentesco'],
                tipo_apoderado='principal',
            )
            
            messages.success(request, f"Estudiante {estudiante.get_full_name()} y apoderado {apoderado_user.get_full_name()} creados exitosamente.")
            return redirect('setup_wizard')
    except Exception:
        logger.exception("Error al crear estudiante y apoderado")
        messages.error(request, "Ocurrió un error al crear el estudiante. Contacte al administrador.")
        return redirect('setup_wizard')


def _get_step_context(current_step, colegio, setup_status):
    """Prepara el contexto específico para cada paso del wizard"""
    context = {
        'current_step': current_step,
        'setup_status': setup_status,
        'colegio': colegio,
        'year': datetime.now().year,
    }
    
    step_key = current_step['key']
    
    if step_key == 'ciclo_academico':
        # Sugerir año actual
        context['anio_sugerido'] = datetime.now().year
        
    elif step_key == 'cursos':
        # Listar niveles disponibles
        context['niveles'] = SetupWizardQueryService.list_levels()
        context['ciclo_activo'] = SetupWizardQueryService.get_active_cycle(
            colegio=colegio,
            estado_activo=CICLO_ESTADO_ACTIVO,
        )
        
    elif step_key == 'profesores':
        # Información para crear primer profesor
        pass
        
    elif step_key == 'estudiantes':
        # Listar cursos disponibles para matrícula
        ciclo_activo = SetupWizardQueryService.get_active_cycle(
            colegio=colegio,
            estado_activo=CICLO_ESTADO_ACTIVO,
        )
        if ciclo_activo:
            context['cursos'] = SetupWizardQueryService.list_courses_for_cycle(
                colegio=colegio,
                ciclo=ciclo_activo,
            )
    
    return context
