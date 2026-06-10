"""
Student Management Views - Vistas ligeras para gestión CRUD de estudiantes

Estas vistas son orquestadores que delegan la lógica de negocio al StudentService.
Solo manejan HTTP, validaciones de entrada, y respuestas al usuario.

Migrando desde: sistema_antiguo/core/views.py (líneas 1306-1567)
"""

from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse

from backend.apps.accounts.services.student_service import StudentService
from backend.apps.accounts.models import User, Role, PerfilEstudiante
from backend.apps.cursos.models import Curso


@login_required()
def gestionar_estudiantes(request):
    """
    Vista pasarela para gestión CRUD de estudiantes.
    
    Solo recibe request, valida permisos mínimos, llama a servicio, devuelve response.
    """
    user = request.user
    
    # Validar permisos básicos
    is_valid, error_msg = StudentService.validate_admin_permissions(user)
    if not is_valid:
        messages.error(request, error_msg)
        return redirect('dashboard')
    
    escuela_rbd = user.rbd_colegio
    
    # POST: Procesar acciones delegando al servicio
    if request.method == 'POST':
        result = StudentService.process_student_action(user, escuela_rbd, request.POST)
        
        if result['success']:
            messages.success(request, result['message'])
        else:
            messages.error(request, result['message'])
        
        return redirect('/dashboard/?pagina=gestionar_estudiantes')
    
    # GET: Cargar datos para mostrar
    # Obtener filtros
    filtro_curso = request.GET.get('curso', '')
    filtro_estado = request.GET.get('estado', '')
    filtro_busqueda = request.GET.get('busqueda', '').strip()
    
    # Listar estudiantes con filtros
    estudiantes = StudentService.list_students(
        user=user,
        escuela_rbd=escuela_rbd,
        User=User,
        PerfilEstudiante=PerfilEstudiante,
        filtro_curso=filtro_curso,
        filtro_estado=filtro_estado,
        filtro_busqueda=filtro_busqueda
    )
    
    # Obtener cursos disponibles
    cursos = StudentService.get_available_courses(
        escuela_rbd=escuela_rbd,
        Curso=Curso
    )
    
    # Calcular estadísticas
    stats = StudentService.get_statistics(
        user=user,
        escuela_rbd=escuela_rbd,
        User=User,
        PerfilEstudiante=PerfilEstudiante
    )
    
    # Construir contexto
    context = {
        'estudiantes': estudiantes,
        'cursos': cursos,
        'total_estudiantes': stats['total_estudiantes'],
        'estudiantes_activos': stats['estudiantes_activos'],
        'estudiantes_sin_curso': stats['estudiantes_sin_curso'],
        'total_cursos_con_estudiantes': stats['total_cursos_con_estudiantes'],
        'filtro_curso': filtro_curso,
        'filtro_estado': filtro_estado,
        'filtro_busqueda': filtro_busqueda,
    }
    
    # Retornar JSON si se solicita, sino retornar render de la vista
    if request.GET.get('json'):
        return JsonResponse(context, safe=False)
    return render(request, 'admin_escolar/gestionar_estudiantes.html', context)

