"""
Management command to check system health status.

Provides a comprehensive view of:
- Data integrity issues
- Setup completion status  
- Critical blockers
- Warnings

Usage:
    python manage.py check_system_health
    python manage.py check_system_health --rbd=12345
    python manage.py check_system_health --format=json
    python manage.py check_system_health --rbd=12345 --format=json --output=health_report.json
"""
import json
from django.core.management.base import BaseCommand
from backend.apps.core.services.system_health_service import SystemHealthService


class Command(BaseCommand):
    help = 'Check system health status including data integrity and setup validation'

    def add_arguments(self, parser):
        parser.add_argument(
            '--rbd',
            type=str,
            default=None,
            help='RBD del colegio a analizar (opcional, sin especificar analiza todo el sistema)'
        )
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

    def handle(self, *args, **options):
        rbd_colegio = options.get('rbd')
        format_type = options.get('format')
        output_file = options.get('output')
        
        # Banner solo si es modo texto
        if format_type == 'text':
            self.stdout.write(self.style.WARNING('=' * 80))
            self.stdout.write(self.style.WARNING('SYSTEM HEALTH CHECK'))
            self.stdout.write(self.style.WARNING('=' * 80))
            if rbd_colegio:
                self.stdout.write(f'Colegio RBD: {rbd_colegio}')
            else:
                self.stdout.write('Scope: Todo el sistema')
            self.stdout.write('')

        # Obtener estado de salud
        health_status = SystemHealthService.get_system_health(rbd_colegio)
        
        # Output según formato
        if format_type == 'json':
            self._output_json(health_status, output_file)
        else:
            self._output_text(health_status, output_file)
        
        # Exit code según estado de salud
        if not health_status['is_healthy']:
            # Exit code 1 si hay problemas críticos
            if health_status['summary']['critical_issues'] > 0:
                exit(1)

    def _output_text(self, health_status, output_file):
        """Output health status in text format"""
        lines = []
        
        # Símbolos ASCII para compatibilidad
        checkmark = 'OK'
        crossmark = 'ERROR'
        warning_mark = 'WARNING'
        
        # Header
        lines.append(self.style.WARNING('=' * 80))
        lines.append(self.style.HTTP_INFO('SYSTEM HEALTH REPORT'))
        lines.append(self.style.WARNING('=' * 80))
        lines.append(f'Timestamp: {health_status["timestamp"]}')
        lines.append(f'Colegio: {health_status.get("colegio", "All system")}')
        lines.append('')
        
        # Status general
        if health_status['is_healthy']:
            lines.append(self.style.SUCCESS(f'{checkmark} SYSTEM IS HEALTHY'))
        else:
            lines.append(self.style.ERROR(f'{crossmark} SYSTEM HAS ISSUES'))
        
        lines.append('')
        lines.append(self.style.HTTP_INFO('SUMMARY:'))
        lines.append(f'  Total Issues: {health_status["summary"]["total_issues"]}')
        lines.append(f'  Critical Issues: {health_status["summary"]["critical_issues"]}')
        lines.append(f'  Warnings: {health_status["summary"]["warnings"]}')
        lines.append('')
        
        # Setup status (si disponible)
        if 'setup_status' in health_status:
            lines.append(self.style.HTTP_INFO('SETUP STATUS:'))
            setup = health_status['setup_status']
            
            if setup['setup_complete']:
                lines.append(self.style.SUCCESS(f'  {checkmark} Setup Complete'))
            else:
                lines.append(self.style.WARNING(f'  {warning_mark} Setup Incomplete'))
                lines.append(f'  Completed: {setup["completed_steps"]}/{setup["total_steps"]} ({setup["completion_percentage"]}%)')
                lines.append(f'  Missing Steps: {", ".join(setup["missing_steps"])}')
            lines.append('')
        
        # Data integrity
        lines.append(self.style.HTTP_INFO('DATA INTEGRITY:'))
        data_integrity = health_status['data_integrity']
        
        if not data_integrity['has_inconsistencies']:
            lines.append(self.style.SUCCESS(f'  {checkmark} No data inconsistencies found'))
        else:
            lines.append(self.style.WARNING(f'  {warning_mark} Found {data_integrity["total_issues"]} data inconsistencies'))
            lines.append('')
            lines.append('  Issues by category:')
            for category_name, category_data in data_integrity['categories'].items():
                if category_data['count'] > 0:
                    lines.append(f'    - {category_name}: {category_data["count"]} issues')
        lines.append('')
        
        # Critical issues
        if health_status['summary']['critical_issues'] > 0:
            lines.append(self.style.ERROR('CRITICAL ISSUES:'))
            for issue in health_status['critical_issues']:
                lines.append(f'  {crossmark} [{issue["type"]}] {issue["description"]}')
                lines.append(f'     Action: {issue["action_required"]}')
                lines.append('')
        
        # Warnings
        if health_status['summary']['warnings'] > 0:
            lines.append(self.style.WARNING('WARNINGS:'))
            # Mostrar solo las primeras 5 warnings para no saturar
            for issue in health_status['warnings'][:5]:
                lines.append(f'  {warning_mark} [{issue["type"]}] {issue["description"]}')
                lines.append(f'     Action: {issue["action_required"]}')
                lines.append('')
            
            if len(health_status['warnings']) > 5:
                lines.append(f'  ... and {len(health_status["warnings"]) - 5} more warnings')
                lines.append('')
        
        # Footer
        lines.append(self.style.WARNING('=' * 80))
        
        # Recomendación final
        if health_status['is_healthy']:
            lines.append(self.style.SUCCESS('✓ SYSTEM IS READY FOR OPERATION'))
        else:
            if health_status['summary']['critical_issues'] > 0:
                lines.append(self.style.ERROR('✗ CRITICAL ISSUES MUST BE RESOLVED BEFORE OPERATION'))
            else:
                lines.append(self.style.WARNING('⚠ SYSTEM IS OPERATIONAL BUT HAS WARNINGS'))
        
        lines.append(self.style.WARNING('=' * 80))
        
        # Output
        output = '\n'.join(lines)
        
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                # Remover colores para archivo
                import re
                clean_output = re.sub(r'\x1b\[[0-9;]*m', '', output)
                f.write(clean_output)
            self.stdout.write(self.style.SUCCESS(f'\nReport saved to: {output_file}'))
        else:
            self.stdout.write(output)

    def _output_json(self, health_status, output_file):
        """Output health status in JSON format"""
        output = json.dumps(health_status, indent=2, ensure_ascii=False)
        
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(output)
            self.stdout.write(self.style.SUCCESS(f'JSON report saved to: {output_file}'))
        else:
            self.stdout.write(output)
