"""
Management command to semi-automatically fix data integrity issues.

Requires confirmation before applying changes and logs all modifications.

STRATEGY:

- Degrade state instead of deleting (mark inactive, not remove)

- Require explicit confirmation for each category

- Log all changes with timestamps

- Provide rollback information


Usage:

    python manage.py fix_data_integrity --dry-run

    python manage.py fix_data_integrity --auto-confirm

    python manage.py fix_data_integrity --category=matriculas

    python manage.py fix_data_integrity --log-file=fixes.log

"""

import json

from datetime import datetime

from django.core.management.base import BaseCommand

from django.db import transaction


class Command(BaseCommand):
    help = 'Fix data integrity issues with confirmation and logging'

    def __init__(self):
        super().__init__()
        self.changes_log = []
        self.dry_run = False
    
    def _get_checkmark(self):
        """Get checkmark character, ASCII for non-TTY"""
        return 'OK' if not hasattr(self.stdout, 'isatty') or not self.stdout.isatty() else '✓'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be fixed without making changes'
        )
        parser.add_argument(
            '--auto-confirm',
            action='store_true',
            help='Skip confirmation prompts (use with caution)'
        )
        parser.add_argument(
            '--category',
            type=str,
            choices=['matriculas', 'cursos', 'clases', 'users', 'perfiles'],
            help='Fix only a specific category'
        )
        parser.add_argument(
            '--log-file',
            type=str,
            help='Save changes log to file'
        )

    def handle(self, *args, **options):
        self.dry_run = options.get('dry_run', False)
        auto_confirm = options.get('auto_confirm', False)
        category = options.get('category')
        log_file = options.get('log_file')

        if self.dry_run:
            self.stdout.write(self.style.WARNING('=' * 80))
            self.stdout.write(self.style.WARNING('DRY RUN MODE - NO CHANGES WILL BE MADE'))
            self.stdout.write(self.style.WARNING('=' * 80))
        else:
            self.stdout.write(self.style.WARNING('=' * 80))
            self.stdout.write(self.style.WARNING('DATA INTEGRITY FIX - WILL MODIFY DATA'))
            self.stdout.write(self.style.WARNING('=' * 80))

        total_fixed = 0

        # Fix by category
        if not category or category == 'matriculas':
            total_fixed += self._fix_matriculas(auto_confirm)

        if not category or category == 'cursos':
            total_fixed += self._fix_cursos(auto_confirm)

        if not category or category == 'clases':
            total_fixed += self._fix_clases(auto_confirm)

        if not category or category == 'users':
            total_fixed += self._fix_users(auto_confirm)

        if not category or category == 'perfiles':
            total_fixed += self._fix_perfiles(auto_confirm)

        # Summary
        self.stdout.write('')
        self.stdout.write(self.style.WARNING('=' * 80))
        if total_fixed > 0:
            checkmark = self._get_checkmark()
            self.stdout.write(self.style.SUCCESS(f'{checkmark} SUMMARY: {total_fixed} issues fixed'))
        else:
            self.stdout.write(self.style.SUCCESS('SUMMARY: 0 issues fixed - Data is clean'))
        self.stdout.write(self.style.WARNING('=' * 80))

        # Save log
        if log_file and not self.dry_run:
            self._save_log(log_file)

    def _fix_matriculas(self, auto_confirm):
        """Fix matriculas with invalid relationships"""
        from backend.apps.matriculas.models import Matricula
        
        self.stdout.write(self.style.HTTP_INFO('\n1. FIXING MATRICULAS...'))
        
        # Find active matriculas with inactive curso
        issues = Matricula.objects.filter(
            estado='ACTIVA',
            curso__activo=False
        )
        
        count = issues.count()
        if count == 0:
            checkmark = self._get_checkmark()
            self.stdout.write(self.style.SUCCESS(f'  {checkmark} No issues found'))
            return 0

        self.stdout.write(f'  Found {count} active matriculas with inactive curso')
        
        if not auto_confirm and not self.dry_run:
            confirm = input('  Suspend these matriculas? (yes/no): ')
            if confirm.lower() != 'yes':
                self.stdout.write('  Skipped')
                return 0

        if not self.dry_run:
            with transaction.atomic():
                for matricula in issues:
                    old_estado = matricula.estado
                    matricula.estado = 'SUSPENDIDA'
                    matricula.save()
                    
                    self.changes_log.append({
                        'timestamp': datetime.now().isoformat(),
                        'model': 'Matricula',
                        'id': matricula.id,
                        'field': 'estado',
                        'old_value': old_estado,
                        'new_value': 'SUSPENDIDA',
                        'reason': 'Curso inactivo'
                    })
            
            checkmark = self._get_checkmark()
            self.stdout.write(self.style.SUCCESS(f'  {checkmark} Fixed {count} matriculas'))
        else:
            self.stdout.write(f'  Would fix {count} matriculas')

        # Fix matriculas with invalid ciclo
        issues_ciclo = Matricula.objects.filter(
            estado='ACTIVA'
        ).exclude(
            ciclo_academico__estado='ACTIVO'
        )
        
        count_ciclo = issues_ciclo.count()
        if count_ciclo > 0:
            self.stdout.write(f'  Found {count_ciclo} active matriculas with non-ACTIVO ciclo')
            
            if not auto_confirm and not self.dry_run:
                confirm = input('  Suspend these matriculas? (yes/no): ')
                if confirm.lower() != 'yes':
                    self.stdout.write('  Skipped')
                    return count

            if not self.dry_run:
                with transaction.atomic():
                    for matricula in issues_ciclo:
                        old_estado = matricula.estado
                        matricula.estado = 'SUSPENDIDA'
                        matricula.save()
                        
                        self.changes_log.append({
                            'timestamp': datetime.now().isoformat(),
                            'model': 'Matricula',
                            'id': matricula.id,
                            'field': 'estado',
                            'old_value': old_estado,
                            'new_value': 'SUSPENDIDA',
                            'reason': 'Ciclo no ACTIVO'
                        })
                
                checkmark = self._get_checkmark()
                self.stdout.write(self.style.SUCCESS(f'  {checkmark} Fixed {count_ciclo} matriculas'))
            else:
                self.stdout.write(f'  Would fix {count_ciclo} matriculas')
        
        return count + count_ciclo

    def _fix_cursos(self, auto_confirm):
        """Fix cursos with invalid ciclo"""
        from backend.apps.cursos.models import Curso
        
        self.stdout.write(self.style.HTTP_INFO('\n2. FIXING CURSOS...'))
        
        issues = Curso.objects.filter(
            activo=True
        ).exclude(
            ciclo_academico__estado='ACTIVO'
        )
        
        count = issues.count()
        if count == 0:
            checkmark = self._get_checkmark()
            self.stdout.write(self.style.SUCCESS(f'  {checkmark} No issues found'))
            return 0

        self.stdout.write(f'  Found {count} active cursos with non-ACTIVO ciclo')
        
        if not auto_confirm and not self.dry_run:
            confirm = input('  Deactivate these cursos? (yes/no): ')
            if confirm.lower() != 'yes':
                self.stdout.write('  Skipped')
                return 0

        if not self.dry_run:
            with transaction.atomic():
                for curso in issues:
                    curso.activo = False
                    curso.save()
                    
                    self.changes_log.append({
                        'timestamp': datetime.now().isoformat(),
                        'model': 'Curso',
                        'id': curso.id_curso,
                        'field': 'activo',
                        'old_value': True,
                        'new_value': False,
                        'reason': 'Ciclo no ACTIVO'
                    })
            
            checkmark = self._get_checkmark()
            self.stdout.write(self.style.SUCCESS(f'  {checkmark} Fixed {count} cursos'))
        else:
            self.stdout.write(f'  Would fix {count} cursos')

        return count

    def _fix_clases(self, auto_confirm):
        """Fix clases with invalid relationships"""
        from backend.apps.cursos.models import Clase
        
        self.stdout.write(self.style.HTTP_INFO('\n3. FIXING CLASES...'))
        
        # Fix clases with inactive curso
        issues = Clase.objects.filter(
            activo=True,
            curso__activo=False
        )
        
        count = issues.count()
        if count == 0:
            checkmark = self._get_checkmark()
            self.stdout.write(self.style.SUCCESS(f'  {checkmark} No issues found'))
            return 0

        self.stdout.write(f'  Found {count} active clases with inactive curso')
        
        if not auto_confirm and not self.dry_run:
            confirm = input('  Deactivate these clases? (yes/no): ')
            if confirm.lower() != 'yes':
                self.stdout.write('  Skipped')
                return 0

        if not self.dry_run:
            with transaction.atomic():
                for clase in issues:
                    clase.activo = False
                    clase.save()
                    
                    self.changes_log.append({
                        'timestamp': datetime.now().isoformat(),
                        'model': 'Clase',
                        'id': clase.id,
                        'field': 'activo',
                        'old_value': True,
                        'new_value': False,
                        'reason': 'Curso inactivo'
                    })
            
            checkmark = self._get_checkmark()
            self.stdout.write(self.style.SUCCESS(f'  {checkmark} Fixed {count} clases'))
        else:
            self.stdout.write(f'  Would fix {count} clases')

        # Fix clases with inactive profesor
        issues_prof = Clase.objects.filter(
            activo=True,
            profesor__is_active=False
        )
        
        count_prof = issues_prof.count()
        if count_prof > 0:
            self.stdout.write(f'  Found {count_prof} active clases with inactive profesor')
            
            if not auto_confirm and not self.dry_run:
                confirm = input('  Deactivate these clases? (yes/no): ')
                if confirm.lower() != 'yes':
                    self.stdout.write('  Skipped')
                    return count

            if not self.dry_run:
                with transaction.atomic():
                    for clase in issues_prof:
                        clase.activo = False
                        clase.save()
                        
                        self.changes_log.append({
                            'timestamp': datetime.now().isoformat(),
                            'model': 'Clase',
                            'id': clase.id,
                            'field': 'activo',
                            'old_value': True,
                            'new_value': False,
                            'reason': 'Profesor inactivo'
                        })
                
                checkmark = self._get_checkmark()
                self.stdout.write(self.style.SUCCESS(f'  {checkmark} Fixed {count_prof} clases'))
            else:
                self.stdout.write(f'  Would fix {count_prof} clases')

        return count + count_prof

    def _fix_users(self, auto_confirm):
        """Fix users with orphaned rbd_colegio"""
        from django.contrib.auth import get_user_model
        from backend.apps.institucion.models import Colegio
        
        User = get_user_model()
        
        self.stdout.write(self.style.HTTP_INFO('\n4. FIXING USERS...'))
        
        # Get all valid RBDs
        valid_rbds = list(Colegio.objects.values_list('rbd', flat=True))
        
        # Find users with invalid rbd
        issues = User.objects.filter(
            rbd_colegio__isnull=False
        ).exclude(
            rbd_colegio__in=valid_rbds
        )
        
        count = issues.count()
        if count == 0:
            checkmark = self._get_checkmark()
            self.stdout.write(self.style.SUCCESS(f'  {checkmark} No issues found'))
            return 0

        self.stdout.write(f'  Found {count} users with orphaned rbd_colegio')
        
        if not auto_confirm and not self.dry_run:
            confirm = input('  Clear rbd_colegio for these users? (yes/no): ')
            if confirm.lower() != 'yes':
                self.stdout.write('  Skipped')
                return 0

        if not self.dry_run:
            with transaction.atomic():
                for user in issues:
                    old_rbd = user.rbd_colegio
                    user.rbd_colegio = None
                    user.save()
                    
                    self.changes_log.append({
                        'timestamp': datetime.now().isoformat(),
                        'model': 'User',
                        'id': user.id,
                        'field': 'rbd_colegio',
                        'old_value': old_rbd,
                        'new_value': None,
                        'reason': 'Colegio no existe'
                    })
            
            checkmark = self._get_checkmark()
            self.stdout.write(self.style.SUCCESS(f'  {checkmark} Fixed {count} users'))
        else:
            self.stdout.write(f'  Would fix {count} users')

        return count

    def _fix_perfiles(self, auto_confirm):
        """Fix perfiles estudiante with invalid ciclo"""
        from backend.apps.accounts.models import PerfilEstudiante
        
        self.stdout.write(self.style.HTTP_INFO('\n5. FIXING PERFILES ESTUDIANTE...'))
        
        issues = PerfilEstudiante.objects.filter(
            ciclo_actual__isnull=False
        ).exclude(
            ciclo_actual__estado='ACTIVO'
        )
        
        count = issues.count()
        if count == 0:
            checkmark = self._get_checkmark()
            self.stdout.write(self.style.SUCCESS(f'  {checkmark} No issues found'))
            return 0

        self.stdout.write(f'  Found {count} perfiles with non-ACTIVO ciclo_actual')
        
        if not auto_confirm and not self.dry_run:
            confirm = input('  Clear ciclo_actual for these perfiles? (yes/no): ')
            if confirm.lower() != 'yes':
                self.stdout.write('  Skipped')
                return 0

        if not self.dry_run:
            with transaction.atomic():
                for perfil in issues:
                    old_ciclo = perfil.ciclo_actual
                    perfil.ciclo_actual = None
                    perfil.save()
                    
                    self.changes_log.append({
                        'timestamp': datetime.now().isoformat(),
                        'model': 'PerfilEstudiante',
                        'id': perfil.id,
                        'field': 'ciclo_actual',
                        'old_value': str(old_ciclo),
                        'new_value': None,
                        'reason': 'Ciclo no ACTIVO'
                    })
            
            checkmark = self._get_checkmark()
            self.stdout.write(self.style.SUCCESS(f'  {checkmark} Fixed {count} perfiles'))
        else:
            self.stdout.write(f'  Would fix {count} perfiles')

        return count

    def _save_log(self, log_file):
        """Save changes log to file"""
        log_data = {
            'timestamp': datetime.now().isoformat(),
            'total_changes': len(self.changes_log),
            'changes': self.changes_log
        }
        
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(log_data, f, indent=2, ensure_ascii=False)
        
        checkmark = self._get_checkmark()
        self.stdout.write(self.style.SUCCESS(f'\n{checkmark} Log saved to {log_file}'))
