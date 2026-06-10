"""
Management command to audit data integrity without modifying anything.
Detects inconsistent relationships and invalid states across the system.

Usage:
    python manage.py audit_data_integrity
    python manage.py audit_data_integrity --format=json
    python manage.py audit_data_integrity --output=report.json
    python manage.py audit_data_integrity --fix  # Corrige los problemas encontrados
    python manage.py audit_data_integrity --fix --dry-run  # Muestra qué corregiría sin persistir
"""
import json
from datetime import datetime
from django.core.management.base import BaseCommand
from django.db.models import Q
from backend.apps.matriculas.models import Matricula
from backend.apps.cursos.models import Curso, Clase
from backend.apps.accounts.models import User, PerfilEstudiante
from backend.apps.institucion.models import Colegio, CicloAcademico
from backend.apps.core.services.data_repair_service import DataRepairService


class Command(BaseCommand):
    help = 'Audits data integrity without modifying anything. Generates report of inconsistencies.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--format',
            type=str,
            default='text',
            choices=['text', 'json'],
            help='Output format (text or json)'
        )
        parser.add_argument(
            '--output',
            type=str,
            default=None,
            help='Output file path (optional, prints to stdout if not specified)'
        )
        parser.add_argument(
            '--fix',
            action='store_true',
            help='Attempt to fix detected issues (default: only audit without fixing)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='With --fix: show what would be fixed without persisting changes'
        )

    def handle(self, *args, **options):
        # Si --fix está activo, usar el servicio de reparación
        if options.get('fix'):
            return self._handle_fix(options)
        
        # Solo auditar (comportamiento original)
        # Solo mostrar banners si no es formato JSON
        json_mode = options.get('format') == 'json'
        
        if not json_mode:
            self.stdout.write(self.style.WARNING('=' * 80))
            self.stdout.write(self.style.WARNING('DATA INTEGRITY AUDIT - READ ONLY'))
            self.stdout.write(self.style.WARNING('=' * 80))
            self.stdout.write('')

        report = {
            'timestamp': datetime.now().isoformat(),
            'total_issues': 0,
            'categories': {}
        }

        # Run all audit checks (pasar json_mode para suprimir output de texto)
        self.json_mode = json_mode
        report['categories']['matriculas_invalidas'] = self._audit_matriculas()
        report['categories']['cursos_invalidos'] = self._audit_cursos()
        report['categories']['clases_invalidas'] = self._audit_clases()
        report['categories']['usuarios_huerfanos'] = self._audit_users()
        report['categories']['perfiles_estudiante_invalidos'] = self._audit_perfil_estudiante()

        # Calculate total issues
        for category in report['categories'].values():
            report['total_issues'] += category['count']

        # Output report
        if json_mode:
            self._output_json(report, options['output'])
        else:
            self._output_text(report, options['output'])

        # Summary (solo si no es JSON)
        if not json_mode:
            self.stdout.write('')
            self.stdout.write(self.style.WARNING('=' * 80))
            
            # Use ASCII characters instead of Unicode for better compatibility
            checkmark = 'OK' if not hasattr(self.stdout, 'isatty') or not self.stdout.isatty() else '✓'
            crossmark = 'ERROR' if not hasattr(self.stdout, 'isatty') or not self.stdout.isatty() else '✗'
            
            if report['total_issues'] == 0:
                self.stdout.write(self.style.SUCCESS(f'{checkmark} NO DATA INTEGRITY ISSUES FOUND'))
            else:
                self.stdout.write(self.style.ERROR(f'{crossmark} FOUND {report["total_issues"]} DATA INTEGRITY ISSUES'))
            self.stdout.write(self.style.WARNING('=' * 80))
    
    def _handle_fix(self, options):
        """Maneja el modo de corrección de datos"""
        json_mode = options.get('format') == 'json'
        dry_run = options.get('dry-run', False)
        
        if not json_mode:
            self.stdout.write(self.style.WARNING('=' * 80))
            if dry_run:
                self.stdout.write(self.style.WARNING('DATA REPAIR SERVICE - DRY RUN MODE'))
                self.stdout.write(self.style.WARNING('(No changes will be persisted)'))
            else:
                self.stdout.write(self.style.ERROR('DATA REPAIR SERVICE - FIXING MODE'))
                self.stdout.write(self.style.ERROR('WARNING: This will modify database records!'))
            self.stdout.write(self.style.WARNING('=' * 80))
            self.stdout.write('')
        
        # Ejecutar servicio de reparación
        repair_service = DataRepairService()
        report = repair_service.repair_all(rbd_colegio=None, dry_run=dry_run)
        
        # Generar output
        if json_mode:
            self._output_fix_json(report, options['output'])
        else:
            self._output_fix_text(report, options['output'])
        
        return report
    
    def _output_fix_text(self, report, output_file):
        """Output del reporte de correcciones en formato texto"""
        lines = []
        lines.append('\n' + '=' * 80)
        lines.append('DATA REPAIR REPORT')
        if report.get('dry_run'):
            lines.append('MODE: DRY RUN (No changes persisted)')
        else:
            lines.append('MODE: LIVE (Changes persisted to database)')
        lines.append('=' * 80)
        lines.append(f'Timestamp: {report["timestamp"]}')
        lines.append(f'Total Corrections: {report["total_corrections"]}')
        lines.append('')
        
        for category_name, category_data in report['categories'].items():
            lines.append(f'\n{category_name.upper().replace("_", " ")}:')
            lines.append(f'Count: {category_data["count"]}')
            if category_data['count'] > 0:
                lines.append('')
                for correction in category_data['corrections']:
                    lines.append(f'  - [{correction["type"]}] ID: {correction["id"]}')
                    lines.append(f'    Action: {correction["action"]}')
                    lines.append(f'    Reason: {correction["reason"]}')
                    
                    # Mostrar datos relevantes
                    for key, value in correction.items():
                        if key not in ['id', 'type', 'action', 'reason'] and value is not None:
                            lines.append(f'    {key}: {value}')
                    lines.append('')
        
        if report.get('note'):
            lines.append(f'\nNOTE: {report["note"]}')
        
        output = '\n'.join(lines)
        
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(output)
            self.stdout.write(self.style.SUCCESS(f'\nReport saved to: {output_file}'))
        else:
            self.stdout.write(output)
        
        # Summary
        self.stdout.write('')
        self.stdout.write(self.style.WARNING('=' * 80))
        checkmark = 'OK' if not hasattr(self.stdout, 'isatty') or not self.stdout.isatty() else '✓'
        
        if report['total_corrections'] == 0:
            self.stdout.write(self.style.SUCCESS(f'{checkmark} NO CORRECTIONS NEEDED'))
        else:
            if report.get('dry_run'):
                self.stdout.write(self.style.WARNING(f'{checkmark} WOULD CORRECT {report["total_corrections"]} ISSUES (DRY RUN)'))
            else:
                self.stdout.write(self.style.SUCCESS(f'{checkmark} CORRECTED {report["total_corrections"]} ISSUES'))
        self.stdout.write(self.style.WARNING('=' * 80))
    
    def _output_fix_json(self, report, output_file):
        """Output del reporte de correcciones en formato JSON"""
        output = json.dumps(report, indent=2, ensure_ascii=False)
        
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(output)
            self.stdout.write(self.style.SUCCESS(f'\nJSON report saved to: {output_file}'))
        else:
            self.stdout.write(output)

    def _audit_matriculas(self):
        """Audit Matricula records for invalid relationships"""
        if not getattr(self, 'json_mode', False):
            self.stdout.write(self.style.HTTP_INFO('\n1. AUDITING MATRICULAS...'))
        
        issues = []
        
        # Check: Active matriculas with inactive curso
        matriculas_curso_inactivo = Matricula.objects.filter(
            estado='ACTIVA',
            curso__activo=False
        ).select_related('curso', 'estudiante', 'ciclo_academico')
        
        for m in matriculas_curso_inactivo:
            issues.append({
                'id': m.id,
                'type': 'MATRICULA_CURSO_INACTIVO',
                'description': f'Matricula #{m.id} activa pero curso "{m.curso.nombre}" está inactivo',
                'estudiante': m.estudiante.get_full_name(),
                'estudiante_email': m.estudiante.email,
                'curso': m.curso.nombre if m.curso else None,
                'ciclo': m.ciclo_academico.nombre if m.ciclo_academico else None,
                'suggested_action': 'Cambiar matricula a estado SUSPENDIDA'
            })
        
        # Check: Active matriculas with non-ACTIVO ciclo_academico
        matriculas_ciclo_invalido = Matricula.objects.filter(
            estado='ACTIVA'
        ).exclude(
            ciclo_academico__estado='ACTIVO'
        ).select_related('curso', 'estudiante', 'ciclo_academico')
        
        for m in matriculas_ciclo_invalido:
            issues.append({
                'id': m.id,
                'type': 'MATRICULA_CICLO_INVALIDO',
                'description': f'Matricula #{m.id} activa pero ciclo "{m.ciclo_academico.nombre if m.ciclo_academico else "NULL"}" no está ACTIVO',
                'estudiante': m.estudiante.get_full_name(),
                'estudiante_email': m.estudiante.email,
                'curso': m.curso.nombre if m.curso else None,
                'ciclo': m.ciclo_academico.nombre if m.ciclo_academico else None,
                'ciclo_estado': m.ciclo_academico.estado if m.ciclo_academico else None,
                'suggested_action': 'Cambiar matricula a estado SUSPENDIDA o actualizar ciclo_academico'
            })
        
        # Check: Matriculas with NULL curso
        matriculas_sin_curso = Matricula.objects.filter(
            estado='ACTIVA',
            curso__isnull=True
        ).select_related('estudiante', 'ciclo_academico')
        
        for m in matriculas_sin_curso:
            issues.append({
                'id': m.id,
                'type': 'MATRICULA_SIN_CURSO',
                'description': f'Matricula #{m.id} activa sin curso asignado',
                'estudiante': m.estudiante.get_full_name(),
                'estudiante_email': m.estudiante.email,
                'ciclo': m.ciclo_academico.nombre if m.ciclo_academico else None,
                'suggested_action': 'Asignar curso o cambiar estado a SUSPENDIDA'
            })
        
        # Check: Matriculas with NULL ciclo_academico
        matriculas_sin_ciclo = Matricula.objects.filter(
            estado='ACTIVA',
            ciclo_academico__isnull=True
        ).select_related('curso', 'estudiante')
        
        for m in matriculas_sin_ciclo:
            issues.append({
                'id': m.id,
                'type': 'MATRICULA_SIN_CICLO',
                'description': f'Matricula #{m.id} activa sin ciclo académico',
                'estudiante': m.estudiante.get_full_name(),
                'estudiante_email': m.estudiante.email,
                'curso': m.curso.nombre if m.curso else None,
                'suggested_action': 'Asignar ciclo académico o cambiar estado'
            })
        
        self._print_category_summary('Matriculas', issues)
        
        return {
            'count': len(issues),
            'issues': issues
        }

    def _audit_cursos(self):
        """Audit Curso records for invalid relationships"""
        if not getattr(self, 'json_mode', False):
            self.stdout.write(self.style.HTTP_INFO('\n2. AUDITING CURSOS...'))
        
        issues = []
        
        # Check: Active cursos with non-ACTIVO ciclo_academico
        cursos_ciclo_invalido = Curso.objects.filter(
            activo=True
        ).exclude(
            ciclo_academico__estado='ACTIVO'
        ).select_related('ciclo_academico', 'colegio')
        
        for c in cursos_ciclo_invalido:
            issues.append({
                'id': c.id_curso,
                'type': 'CURSO_CICLO_INVALIDO',
                'description': f'Curso "{c.nombre}" activo pero ciclo "{c.ciclo_academico.nombre if c.ciclo_academico else "NULL"}" no está ACTIVO',
                'curso': c.nombre,
                'colegio': c.colegio.nombre,
                'ciclo': c.ciclo_academico.nombre if c.ciclo_academico else None,
                'ciclo_estado': c.ciclo_academico.estado if c.ciclo_academico else None,
                'suggested_action': 'Marcar curso como inactivo (activo=False)'
            })
        
        # Check: Cursos with NULL ciclo_academico
        cursos_sin_ciclo = Curso.objects.filter(
            activo=True,
            ciclo_academico__isnull=True
        ).select_related('colegio')
        
        for c in cursos_sin_ciclo:
            issues.append({
                'id': c.id_curso,
                'type': 'CURSO_SIN_CICLO',
                'description': f'Curso "{c.nombre}" activo sin ciclo académico',
                'curso': c.nombre,
                'colegio': c.colegio.nombre,
                'suggested_action': 'Asignar ciclo académico o marcar como inactivo'
            })
        
        self._print_category_summary('Cursos', issues)
        
        return {
            'count': len(issues),
            'issues': issues
        }

    def _audit_clases(self):
        """Audit Clase records for invalid relationships"""
        if not getattr(self, 'json_mode', False):
            self.stdout.write(self.style.HTTP_INFO('\n3. AUDITING CLASES...'))
        
        issues = []
        
        # Check: Active clases with inactive curso
        clases_curso_inactivo = Clase.objects.filter(
            activo=True,
            curso__activo=False
        ).select_related('curso', 'asignatura', 'profesor', 'colegio')
        
        for c in clases_curso_inactivo:
            issues.append({
                'id': c.id,
                'type': 'CLASE_CURSO_INACTIVO',
                'description': f'Clase #{c.id} activa pero curso "{c.curso.nombre}" está inactivo',
                'curso': c.curso.nombre,
                'asignatura': c.asignatura.nombre,
                'profesor': c.profesor.get_full_name(),
                'colegio': c.colegio.nombre,
                'suggested_action': 'Desactivar clase (activo=False)'
            })
        
        # Check: Active clases with inactive profesor
        clases_profesor_inactivo = Clase.objects.filter(
            activo=True,
            profesor__is_active=False
        ).select_related('curso', 'asignatura', 'profesor', 'colegio')
        
        for c in clases_profesor_inactivo:
            issues.append({
                'id': c.id,
                'type': 'CLASE_PROFESOR_INACTIVO',
                'description': f'Clase #{c.id} activa pero profesor "{c.profesor.get_full_name()}" está inactivo',
                'curso': c.curso.nombre,
                'asignatura': c.asignatura.nombre,
                'profesor': c.profesor.get_full_name(),
                'colegio': c.colegio.nombre,
                'suggested_action': 'Desactivar clase o reasignar profesor'
            })
        
        # Check: Active clases where curso has invalid ciclo
        clases_ciclo_invalido = Clase.objects.filter(
            activo=True
        ).exclude(
            curso__ciclo_academico__estado='ACTIVO'
        ).select_related('curso', 'curso__ciclo_academico', 'asignatura', 'profesor')
        
        for c in clases_ciclo_invalido:
            issues.append({
                'id': c.id,
                'type': 'CLASE_CICLO_INVALIDO',
                'description': f'Clase #{c.id} activa pero ciclo del curso no está ACTIVO',
                'curso': c.curso.nombre,
                'asignatura': c.asignatura.nombre,
                'profesor': c.profesor.get_full_name(),
                'ciclo': c.curso.ciclo_academico.nombre if c.curso.ciclo_academico else None,
                'ciclo_estado': c.curso.ciclo_academico.estado if c.curso.ciclo_academico else None,
                'suggested_action': 'Desactivar clase (activo=False)'
            })
        
        self._print_category_summary('Clases', issues)
        
        return {
            'count': len(issues),
            'issues': issues
        }

    def _audit_users(self):
        """Audit User records for orphaned colegio references"""
        if not getattr(self, 'json_mode', False):
            self.stdout.write(self.style.HTTP_INFO('\n4. AUDITING USERS (ORPHANED COLEGIOS)...'))
        
        issues = []
        
        # Get all users with rbd_colegio set
        users_with_colegio = User.objects.filter(
            rbd_colegio__isnull=False,
            is_active=True
        ).select_related('role')
        
        for u in users_with_colegio:
            # Check if colegio exists
            try:
                colegio = Colegio.objects.get(rbd=u.rbd_colegio)
            except Colegio.DoesNotExist:
                issues.append({
                    'id': u.id,
                    'type': 'USER_COLEGIO_HUERFANO',
                    'description': f'Usuario "{u.get_full_name()}" tiene rbd_colegio={u.rbd_colegio} pero el colegio no existe',
                    'email': u.email,
                    'nombre': u.get_full_name(),
                    'rbd_colegio': u.rbd_colegio,
                    'role': u.role.nombre if u.role else None,
                    'suggested_action': 'Reasignar a colegio válido o desactivar usuario'
                })
        
        self._print_category_summary('Users', issues)
        
        return {
            'count': len(issues),
            'issues': issues
        }

    def _audit_perfil_estudiante(self):
        """Audit PerfilEstudiante records for invalid ciclo_actual"""
        if not getattr(self, 'json_mode', False):
            self.stdout.write(self.style.HTTP_INFO('\n5. AUDITING PERFILES ESTUDIANTE...'))
        
        issues = []
        
        # Check: Active students with non-ACTIVO ciclo_actual
        perfiles_ciclo_invalido = PerfilEstudiante.objects.filter(
            estado_academico='Activo',
            ciclo_actual__isnull=False
        ).exclude(
            ciclo_actual__estado='ACTIVO'
        ).select_related('user', 'ciclo_actual')
        
        for p in perfiles_ciclo_invalido:
            issues.append({
                'id': p.id,
                'type': 'PERFIL_CICLO_INVALIDO',
                'description': f'PerfilEstudiante #{p.id} activo pero ciclo_actual "{p.ciclo_actual.nombre}" no está ACTIVO',
                'estudiante': p.user.get_full_name(),
                'estudiante_email': p.user.email,
                'ciclo_actual': p.ciclo_actual.nombre,
                'ciclo_estado': p.ciclo_actual.estado,
                'suggested_action': 'Actualizar ciclo_actual o cambiar estado_academico'
            })
        
        # Check: Active students with NULL ciclo_actual
        perfiles_sin_ciclo = PerfilEstudiante.objects.filter(
            estado_academico='Activo',
            ciclo_actual__isnull=True
        ).select_related('user')
        
        for p in perfiles_sin_ciclo:
            issues.append({
                'id': p.id,
                'type': 'PERFIL_SIN_CICLO',
                'description': f'PerfilEstudiante #{p.id} activo sin ciclo_actual asignado',
                'estudiante': p.user.get_full_name(),
                'estudiante_email': p.user.email,
                'suggested_action': 'Asignar ciclo_actual o cambiar estado_academico'
            })
        
        # Check: Inactive users with active perfil
        perfiles_user_inactivo = PerfilEstudiante.objects.filter(
            estado_academico='Activo',
            user__is_active=False
        ).select_related('user')
        
        for p in perfiles_user_inactivo:
            issues.append({
                'id': p.id,
                'type': 'PERFIL_USER_INACTIVO',
                'description': f'PerfilEstudiante #{p.id} activo pero User está inactivo',
                'estudiante': p.user.get_full_name(),
                'estudiante_email': p.user.email,
                'suggested_action': 'Cambiar estado_academico a "Suspendido" o reactivar usuario'
            })
        
        self._print_category_summary('Perfiles Estudiante', issues)
        
        return {
            'count': len(issues),
            'issues': issues
        }

    def _print_category_summary(self, category_name, issues):
        """Print summary for a category"""
        # Solo imprimir si NO estamos en modo JSON
        if getattr(self, 'json_mode', False):
            return
            
        # Use ASCII characters instead of Unicode for better compatibility
        checkmark = 'OK' if not hasattr(self.stdout, 'isatty') or not self.stdout.isatty() else '✓'
        crossmark = 'ERROR' if not hasattr(self.stdout, 'isatty') or not self.stdout.isatty() else '✗'
        
        if len(issues) == 0:
            self.stdout.write(self.style.SUCCESS(f'  {checkmark} {category_name}: No issues found'))
        else:
            self.stdout.write(self.style.ERROR(f'  {crossmark} {category_name}: {len(issues)} issues found'))
            for issue in issues[:3]:  # Show first 3 as examples
                self.stdout.write(f'    - {issue["description"]}')
            if len(issues) > 3:
                self.stdout.write(f'    ... and {len(issues) - 3} more')

    def _output_text(self, report, output_file):
        """Output report in text format"""
        lines = []
        lines.append('\n' + '=' * 80)
        lines.append('DATA INTEGRITY AUDIT REPORT')
        lines.append('=' * 80)
        lines.append(f'Timestamp: {report["timestamp"]}')
        lines.append(f'Total Issues: {report["total_issues"]}')
        lines.append('')
        
        for category_name, category_data in report['categories'].items():
            lines.append(f'\n{category_name.upper().replace("_", " ")}:')
            lines.append(f'Count: {category_data["count"]}')
            if category_data['count'] > 0:
                lines.append('')
                for issue in category_data['issues']:
                    lines.append(f'  - [{issue["type"]}] {issue["description"]}')
                    lines.append(f'    Suggested Action: {issue["suggested_action"]}')
                    lines.append('')
        
        output = '\n'.join(lines)
        
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(output)
            self.stdout.write(self.style.SUCCESS(f'\nReport saved to: {output_file}'))
        else:
            self.stdout.write(output)

    def _output_json(self, report, output_file):
        """Output report in JSON format"""
        output = json.dumps(report, indent=2, ensure_ascii=False)
        
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(output)
            self.stdout.write(self.style.SUCCESS(f'\nJSON report saved to: {output_file}'))
        else:
            self.stdout.write(output)
