"""
Data Repair Service - Fase 2: Corrección Controlada de Datos

Este servicio corrige datos inválidos de forma segura siguiendo las reglas:

REGLAS ABSOLUTAS:
- NUNCA borrar registros
- Solo marcar como inactivo, suspender, deshabilitar, o corregir estados
- Todas las operaciones deben ser auditables y reversibles
- Retornar reporte detallado de todas las correcciones realizadas

ACCIONES PERMITIDAS:
- Matriculas inválidas → estado='SUSPENDIDA'
- Cursos inválidos → activo=False
- Clases inválidas → activo=False
- Users huérfanos → is_active=False (solo si no tienen perfiles críticos)
- Perfiles estudiante inválidos → estado_academico='Suspendido'

ACCIONES PROHIBIDAS:
- DELETE de cualquier registro
- Modificación de relaciones (ForeignKey)
- Cambios en datos de negocio (notas, asistencia, etc.)
"""
from typing import Dict, List, Optional
from datetime import datetime
from django.db import transaction
from django.utils import timezone

from backend.apps.matriculas.models import Matricula
from backend.apps.cursos.models import Curso, Clase
from backend.apps.accounts.models import User, PerfilEstudiante
from backend.apps.institucion.models import Colegio


class DataRepairService:
    """
    Servicio para corregir datos inválidos de forma controlada.
    
    NO elimina datos. Solo corrige estados y marca como inactivo.
    """

    @staticmethod
    def execute(operation, params=None):
        if params is None:
            params = {}
        DataRepairService.validate(operation, params)
        return DataRepairService._execute(operation, params)

    @staticmethod
    def validate(operation, params):
        if not isinstance(operation, str) or not operation.strip():
            raise ValueError('Parámetro requerido: operation')
        if not isinstance(params, dict):
            raise ValueError('Parámetro inválido: params debe ser dict')

    @staticmethod
    def _execute(operation, params):
        handler = getattr(DataRepairService, f'_execute_{operation}', None)
        if callable(handler):
            return handler(params)
        raise ValueError(f'Operación no soportada: {operation}')
    
    def __init__(self):
        self.report = {
            'timestamp': timezone.now().isoformat(),
            'total_corrections': 0,
            'categories': {}
        }
    
    @transaction.atomic
    def repair_all(self, rbd_colegio: Optional[str] = None, dry_run: bool = False) -> Dict:
        """
        Ejecuta todas las correcciones de datos.
        
        Args:
            rbd_colegio: Optional. Si se proporciona, solo repara datos de ese colegio
            dry_run: Si es True, no persiste cambios (solo reporta qué haría)
            
        Returns:
            Diccionario con reporte de correcciones realizadas
        """
        # Si es dry_run, crear un savepoint para revertir
        if dry_run:
            sid = transaction.savepoint()
        
        try:
            # Ejecutar todas las correcciones en orden
            self.report['categories']['matriculas'] = self._repair_matriculas(rbd_colegio)
            self.report['categories']['cursos'] = self._repair_cursos(rbd_colegio)
            self.report['categories']['clases'] = self._repair_clases(rbd_colegio)
            self.report['categories']['usuarios'] = self._repair_usuarios(rbd_colegio)
            self.report['categories']['perfiles_estudiante'] = self._repair_perfiles_estudiante(rbd_colegio)
            
            # Calcular total de correcciones
            for category in self.report['categories'].values():
                self.report['total_corrections'] += category['count']
            
            # Si es dry_run, revertir todos los cambios
            if dry_run:
                transaction.savepoint_rollback(sid)
                self.report['dry_run'] = True
                self.report['note'] = 'DRY RUN: No se persistieron cambios en la base de datos'
            else:
                self.report['dry_run'] = False
                
            return self.report
            
        except Exception as e:
            if dry_run:
                transaction.savepoint_rollback(sid)
            raise
    
    def _repair_matriculas(self, rbd_colegio: Optional[str] = None) -> Dict:
        """
        Corrige matrículas inválidas marcándolas como SUSPENDIDA.
        
        Casos corregidos:
        - Matrícula activa con curso inactivo
        - Matrícula activa con ciclo no ACTIVO
        - Matrícula activa sin curso
        - Matrícula activa sin ciclo
        """
        corrections = []
        
        # Construir base queryset
        base_qs = Matricula.objects.filter(estado='ACTIVA')
        if rbd_colegio:
            base_qs = base_qs.filter(colegio__rbd=rbd_colegio)
        
        # Caso 1: Matrícula activa con curso inactivo
        matriculas_curso_inactivo = base_qs.filter(
            curso__activo=False
        ).select_related('curso', 'estudiante', 'ciclo_academico')
        
        for m in matriculas_curso_inactivo:
            m.estado = 'SUSPENDIDA'
            m.save(update_fields=['estado'])
            corrections.append({
                'id': m.id,
                'type': 'MATRICULA_CURSO_INACTIVO',
                'action': 'Changed estado to SUSPENDIDA',
                'reason': f'Curso "{m.curso.nombre}" está inactivo',
                'estudiante': m.estudiante.get_full_name(),
                'curso': m.curso.nombre if m.curso else None
            })
        
        # Caso 2: Matrícula activa con ciclo no ACTIVO
        matriculas_ciclo_invalido = base_qs.exclude(
            ciclo_academico__estado='ACTIVO'
        ).select_related('curso', 'estudiante', 'ciclo_academico')
        
        for m in matriculas_ciclo_invalido:
            m.estado = 'SUSPENDIDA'
            m.save(update_fields=['estado'])
            corrections.append({
                'id': m.id,
                'type': 'MATRICULA_CICLO_INVALIDO',
                'action': 'Changed estado to SUSPENDIDA',
                'reason': f'Ciclo "{m.ciclo_academico.nombre if m.ciclo_academico else "NULL"}" no está ACTIVO',
                'estudiante': m.estudiante.get_full_name(),
                'ciclo_estado': m.ciclo_academico.estado if m.ciclo_academico else None
            })
        
        # Caso 3: Matrícula activa sin curso
        matriculas_sin_curso = base_qs.filter(
            curso__isnull=True
        ).select_related('estudiante', 'ciclo_academico')
        
        for m in matriculas_sin_curso:
            m.estado = 'SUSPENDIDA'
            m.save(update_fields=['estado'])
            corrections.append({
                'id': m.id,
                'type': 'MATRICULA_SIN_CURSO',
                'action': 'Changed estado to SUSPENDIDA',
                'reason': 'Matrícula sin curso asignado',
                'estudiante': m.estudiante.get_full_name()
            })
        
        # Caso 4: Matrícula activa sin ciclo
        matriculas_sin_ciclo = base_qs.filter(
            ciclo_academico__isnull=True
        ).select_related('curso', 'estudiante')
        
        for m in matriculas_sin_ciclo:
            m.estado = 'SUSPENDIDA'
            m.save(update_fields=['estado'])
            corrections.append({
                'id': m.id,
                'type': 'MATRICULA_SIN_CICLO',
                'action': 'Changed estado to SUSPENDIDA',
                'reason': 'Matrícula sin ciclo académico',
                'estudiante': m.estudiante.get_full_name(),
                'curso': m.curso.nombre if m.curso else None
            })
        
        return {
            'count': len(corrections),
            'corrections': corrections
        }
    
    def _repair_cursos(self, rbd_colegio: Optional[str] = None) -> Dict:
        """
        Corrige cursos inválidos marcándolos como inactivos.
        
        Casos corregidos:
        - Curso activo con ciclo no ACTIVO
        - Curso activo sin ciclo
        """
        corrections = []
        
        # Construir base queryset
        base_qs = Curso.objects.filter(activo=True)
        if rbd_colegio:
            base_qs = base_qs.filter(colegio__rbd=rbd_colegio)
        
        # Caso 1: Curso activo con ciclo no ACTIVO
        cursos_ciclo_invalido = base_qs.exclude(
            ciclo_academico__estado='ACTIVO'
        ).select_related('ciclo_academico', 'colegio')
        
        for c in cursos_ciclo_invalido:
            c.activo = False
            c.save(update_fields=['activo'])
            corrections.append({
                'id': c.id_curso,
                'type': 'CURSO_CICLO_INVALIDO',
                'action': 'Set activo=False',
                'reason': f'Ciclo "{c.ciclo_academico.nombre if c.ciclo_academico else "NULL"}" no está ACTIVO',
                'curso': c.nombre,
                'colegio': c.colegio.nombre,
                'ciclo_estado': c.ciclo_academico.estado if c.ciclo_academico else None
            })
        
        # Caso 2: Curso activo sin ciclo
        cursos_sin_ciclo = base_qs.filter(
            ciclo_academico__isnull=True
        ).select_related('colegio')
        
        for c in cursos_sin_ciclo:
            c.activo = False
            c.save(update_fields=['activo'])
            corrections.append({
                'id': c.id_curso,
                'type': 'CURSO_SIN_CICLO',
                'action': 'Set activo=False',
                'reason': 'Curso sin ciclo académico',
                'curso': c.nombre,
                'colegio': c.colegio.nombre
            })
        
        return {
            'count': len(corrections),
            'corrections': corrections
        }
    
    def _repair_clases(self, rbd_colegio: Optional[str] = None) -> Dict:
        """
        Corrige clases inválidas marcándolas como inactivas.
        
        Casos corregidos:
        - Clase activa con curso inactivo
        - Clase activa con profesor inactivo
        - Clase activa con ciclo del curso no ACTIVO
        """
        corrections = []
        
        # Construir base queryset
        base_qs = Clase.objects.filter(activo=True)
        if rbd_colegio:
            base_qs = base_qs.filter(colegio__rbd=rbd_colegio)
        
        # Caso 1: Clase activa con curso inactivo
        clases_curso_inactivo = base_qs.filter(
            curso__activo=False
        ).select_related('curso', 'asignatura', 'profesor', 'colegio')
        
        for c in clases_curso_inactivo:
            c.activo = False
            c.save(update_fields=['activo'])
            corrections.append({
                'id': c.id,
                'type': 'CLASE_CURSO_INACTIVO',
                'action': 'Set activo=False',
                'reason': f'Curso "{c.curso.nombre}" está inactivo',
                'curso': c.curso.nombre,
                'asignatura': c.asignatura.nombre,
                'profesor': c.profesor.get_full_name() if c.profesor else None
            })
        
        # Caso 2: Clase activa con profesor inactivo
        clases_profesor_inactivo = base_qs.filter(
            profesor__is_active=False
        ).select_related('curso', 'asignatura', 'profesor', 'colegio')
        
        for c in clases_profesor_inactivo:
            c.activo = False
            c.save(update_fields=['activo'])
            corrections.append({
                'id': c.id,
                'type': 'CLASE_PROFESOR_INACTIVO',
                'action': 'Set activo=False',
                'reason': f'Profesor "{c.profesor.get_full_name()}" está inactivo',
                'curso': c.curso.nombre,
                'asignatura': c.asignatura.nombre,
                'profesor': c.profesor.get_full_name()
            })
        
        # Caso 3: Clase activa con ciclo del curso no ACTIVO
        clases_ciclo_invalido = base_qs.exclude(
            curso__ciclo_academico__estado='ACTIVO'
        ).select_related('curso', 'curso__ciclo_academico', 'asignatura', 'profesor')
        
        for c in clases_ciclo_invalido:
            c.activo = False
            c.save(update_fields=['activo'])
            corrections.append({
                'id': c.id,
                'type': 'CLASE_CICLO_INVALIDO',
                'action': 'Set activo=False',
                'reason': 'Ciclo del curso no está ACTIVO',
                'curso': c.curso.nombre,
                'asignatura': c.asignatura.nombre,
                'ciclo': c.curso.ciclo_academico.nombre if c.curso.ciclo_academico else None,
                'ciclo_estado': c.curso.ciclo_academico.estado if c.curso.ciclo_academico else None
            })
        
        return {
            'count': len(corrections),
            'corrections': corrections
        }
    
    def _repair_usuarios(self, rbd_colegio: Optional[str] = None) -> Dict:
        """
        Corrige usuarios con referencias huérfanas.
        
        Casos corregidos:
        - Usuario con rbd_colegio que no existe → desactiva usuario
        
        NOTA: Solo desactiva si el usuario NO tiene perfiles críticos activos
        """
        corrections = []
        
        # Construir base queryset
        base_qs = User.objects.filter(
            rbd_colegio__isnull=False,
            is_active=True
        )
        if rbd_colegio:
            base_qs = base_qs.filter(rbd_colegio=rbd_colegio)
        
        for u in base_qs.select_related('role'):
            # Verificar si el colegio existe
            try:
                colegio = Colegio.objects.get(rbd=u.rbd_colegio)
            except Colegio.DoesNotExist:
                # Colegio no existe - verificar si tiene perfiles críticos
                tiene_matriculas_activas = Matricula.objects.filter(
                    estudiante=u,
                    estado='ACTIVA'
                ).exists()
                
                # Solo desactivar si NO tiene matrículas activas
                if not tiene_matriculas_activas:
                    u.is_active = False
                    u.save(update_fields=['is_active'])
                    corrections.append({
                        'id': u.id,
                        'type': 'USER_COLEGIO_HUERFANO',
                        'action': 'Set is_active=False',
                        'reason': f'RBD colegio {u.rbd_colegio} no existe',
                        'email': u.email,
                        'nombre': u.get_full_name(),
                        'role': u.role.nombre if u.role else None
                    })
                else:
                    corrections.append({
                        'id': u.id,
                        'type': 'USER_COLEGIO_HUERFANO',
                        'action': 'SKIPPED - tiene matrículas activas',
                        'reason': f'RBD colegio {u.rbd_colegio} no existe pero usuario tiene matrículas activas',
                        'email': u.email,
                        'nombre': u.get_full_name(),
                        'warning': 'Requiere intervención manual'
                    })
        
        return {
            'count': len(corrections),
            'corrections': corrections
        }
    
    def _repair_perfiles_estudiante(self, rbd_colegio: Optional[str] = None) -> Dict:
        """
        Corrige perfiles de estudiante inválidos.
        
        Casos corregidos:
        - Perfil activo con ciclo_actual no ACTIVO → estado='Suspendido'
        - Perfil activo sin ciclo_actual → estado='Suspendido'
        - Perfil activo con usuario inactivo → estado='Suspendido'
        """
        corrections = []
        
        # Construir base queryset
        base_qs = PerfilEstudiante.objects.filter(estado_academico='Activo')
        if rbd_colegio:
            base_qs = base_qs.filter(user__rbd_colegio=rbd_colegio)
        
        # Caso 1: Perfil activo con ciclo_actual no ACTIVO
        perfiles_ciclo_invalido = base_qs.filter(
            ciclo_actual__isnull=False
        ).exclude(
            ciclo_actual__estado='ACTIVO'
        ).select_related('user', 'ciclo_actual')
        
        for p in perfiles_ciclo_invalido:
            p.estado_academico = 'Suspendido'
            p.save(update_fields=['estado_academico'])
            corrections.append({
                'id': p.id,
                'type': 'PERFIL_CICLO_INVALIDO',
                'action': 'Changed estado_academico to Suspendido',
                'reason': f'Ciclo actual "{p.ciclo_actual.nombre}" no está ACTIVO',
                'estudiante': p.user.get_full_name(),
                'estudiante_email': p.user.email,
                'ciclo_estado': p.ciclo_actual.estado
            })
        
        # Caso 2: Perfil activo sin ciclo_actual
        perfiles_sin_ciclo = base_qs.filter(
            ciclo_actual__isnull=True
        ).select_related('user')
        
        for p in perfiles_sin_ciclo:
            p.estado_academico = 'Suspendido'
            p.save(update_fields=['estado_academico'])
            corrections.append({
                'id': p.id,
                'type': 'PERFIL_SIN_CICLO',
                'action': 'Changed estado_academico to Suspendido',
                'reason': 'Perfil sin ciclo_actual asignado',
                'estudiante': p.user.get_full_name(),
                'estudiante_email': p.user.email
            })
        
        # Caso 3: Perfil activo con usuario inactivo
        perfiles_user_inactivo = base_qs.filter(
            user__is_active=False
        ).select_related('user')
        
        for p in perfiles_user_inactivo:
            p.estado_academico = 'Suspendido'
            p.save(update_fields=['estado_academico'])
            corrections.append({
                'id': p.id,
                'type': 'PERFIL_USER_INACTIVO',
                'action': 'Changed estado_academico to Suspendido',
                'reason': 'Usuario asociado está inactivo',
                'estudiante': p.user.get_full_name(),
                'estudiante_email': p.user.email
            })
        
        return {
            'count': len(corrections),
            'corrections': corrections
        }
