"""
Ejemplo de Uso del Template Mapping en Vistas
==============================================

Este archivo demuestra cómo usar el sistema de mapeo de templates
por roles en las vistas de Django.
"""

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from backend.common.template_mapping import get_template_for_role, get_template_from_url_name


# EJEMPLO 1: Vista básica con template dinámico por rol
@login_required
def mis_notas_view(request):
    """
    Vista que muestra las notas del usuario según su rol.
    - Estudiante: Ve sus propias notas
    - Profesor: Gestiona notas de sus cursos
    - Apoderado: Ve notas de su hijo
    """
    user = request.user
    role_name = user.role.nombre if hasattr(user, 'role') else 'estudiante'
    
    # Obtener template correcto según el rol
    template = get_template_for_role('mis_notas', role_name)
    
    # Preparar contexto según el rol
    context = {}
    
    if role_name == 'estudiante':
        # Lógica para estudiante
        context['notas'] = []  # TODO: Obtener notas del estudiante
        context['promedio_general'] = 0.0
        
    elif role_name == 'profesor':
        # Lógica para profesor
        context['cursos'] = []  # TODO: Obtener cursos del profesor
        context['estudiantes'] = []
        
    elif role_name == 'apoderado':
        # Lógica para apoderado
        context['hijos'] = []  # TODO: Obtener hijos del apoderado
        
    return render(request, template, context)


# EJEMPLO 2: Vista con manejo de excepciones
@login_required
def asistencia_view(request):
    """
    Vista de asistencia con manejo de errores.
    """
    user = request.user
    role_name = user.role.nombre if hasattr(user, 'role') else 'estudiante'
    
    try:
        template = get_template_for_role('asistencia', role_name)
    except ValueError as e:
        # Si no existe mapeo, usar template genérico
        template = 'frontend/templates/base_app.html'
        context = {'error': str(e)}
        return render(request, template, context)
    
    context = {
        'porcentaje_asistencia': 95.0,
        'dias_presente': 180,
        'dias_ausente': 5,
    }
    
    return render(request, template, context)


# EJEMPLO 3: Vista usando el nombre de URL
@login_required
def dashboard_view(request):
    """
    Dashboard principal que se adapta al rol del usuario.
    """
    user = request.user
    role_name = user.role.nombre if hasattr(user, 'role') else 'estudiante'
    
    # Método alternativo: usar el nombre de la URL
    template = get_template_from_url_name('dashboard', role_name)
    
    # Contexto base para todos los roles
    context = {
        'nombre_usuario': user.get_full_name() or user.username,
        'year': 2026,
    }
    
    # Agregar datos específicos por rol
    if role_name == 'estudiante':
        context.update({
            'clases_hoy': 5,
            'tareas_pendientes': 3,
            'tareas_urgentes': 1,
            'promedio_general': 6.2,
            'porcentaje_asistencia': 95.5,
        })
        
    elif role_name == 'profesor':
        context.update({
            'cursos_activos': 4,
            'estudiantes_total': 120,
            'evaluaciones_pendientes': 15,
        })
        
    elif role_name == 'apoderado':
        context.update({
            'hijos_count': 2,
            'comunicados_nuevos': 3,
        })
    
    return render(request, template, context)


# EJEMPLO 4: Vista con Class-Based View
from django.views import View
from django.utils.decorators import method_decorator

@method_decorator(login_required, name='dispatch')
class PerfilView(View):
    """
    Vista de perfil usando CBV.
    """
    
    def get_template(self, role_name):
        """Obtiene el template correcto para el rol."""
        return get_template_for_role('perfil', role_name)
    
    def get(self, request):
        user = request.user
        role_name = user.role.nombre if hasattr(user, 'role') else 'estudiante'
        
        template = self.get_template(role_name)
        
        context = {
            'user': user,
            'promedio_general': 6.0,
            'porcentaje_asistencia': 90.0,
            'tareas_completadas': 45,
            'tareas_totales': 50,
        }
        
        return render(request, template, context)
    
    def post(self, request):
        """Actualiza el perfil del usuario."""
        user = request.user
        role_name = user.role.nombre if hasattr(user, 'role') else 'estudiante'
        
        # Procesar formulario
        # ...
        
        template = self.get_template(role_name)
        context = {'success': True, 'message': 'Perfil actualizado'}
        
        return render(request, template, context)


# EJEMPLO 5: Decorator personalizado para templates dinámicos
from functools import wraps

def dynamic_template(view_name):
    """
    Decorator que asigna automáticamente el template según el rol.
    
    Uso:
        @dynamic_template('mis_notas')
        def mi_vista(request, template):
            context = {...}
            return render(request, template, context)
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            user = request.user
            role_name = user.role.nombre if hasattr(user, 'role') else 'estudiante'
            
            try:
                template = get_template_for_role(view_name, role_name)
            except ValueError:
                template = 'frontend/templates/base_app.html'
            
            # Pasar el template como argumento a la vista
            return view_func(request, template, *args, **kwargs)
        
        return wrapper
    return decorator


# Ejemplo de uso del decorator
@login_required
@dynamic_template('tareas')
def tareas_view(request, template):
    """
    Vista de tareas usando el decorator personalizado.
    El template ya viene asignado según el rol.
    """
    context = {
        'tareas_pendientes': 3,
        'tareas_entregadas': 12,
        'tareas_vencidas': 1,
        'promedio_tareas': 6.5,
    }
    
    return render(request, template, context)


# EJEMPLO 6: Vista API que también sirve templates
from django.http import JsonResponse

@login_required
def notas_api_view(request):
    """
    Vista que puede servir tanto JSON como HTML según el Accept header.
    """
    user = request.user
    role_name = user.role.nombre if hasattr(user, 'role') else 'estudiante'
    
    # Obtener datos
    notas_data = {
        'promedio': 6.2,
        'asignaturas': [
            {'nombre': 'Matemática', 'nota': 6.5},
            {'nombre': 'Lenguaje', 'nota': 6.0},
        ]
    }
    
    # Si solicita JSON, devolver JSON
    if request.META.get('HTTP_ACCEPT') == 'application/json':
        return JsonResponse(notas_data)
    
    # Si no, renderizar template según rol
    template = get_template_for_role('mis_notas', role_name)
    context = notas_data
    
    return render(request, template, context)


# EJEMPLO 7: Middleware para logging de templates usados
class TemplateLoggingMiddleware:
    """
    Middleware que registra qué templates se usan por cada rol.
    Útil para debugging y analytics.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        response = self.get_response(request)
        
        # Después de la respuesta, registrar información
        if hasattr(request, 'user') and request.user.is_authenticated:
            role = request.user.role.nombre if hasattr(request.user, 'role') else 'unknown'
            path = request.path
            
            # TODO: Guardar en log o analytics
            # print(f"Template usado por {role} en {path}")
        
        return response
