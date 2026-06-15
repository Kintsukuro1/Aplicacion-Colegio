"""
Management command to check and fix student data for testing
"""
from django.core.management.base import BaseCommand
from backend.apps.accounts.models import User, PerfilEstudiante
from backend.apps.institucion.models import CicloAcademico, Colegio
from backend.apps.cursos.models import Curso
from backend.apps.matriculas.models import Matricula


class Command(BaseCommand):
    help = 'Check and fix student data for testing'

    def handle(self, *args, **options):
        # Get the test student
        try:
            student = User.objects.get(email='alumno1@colegio.cl')
            self.stdout.write(f"Found student: {student}")
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR("Student alumno1@colegio.cl not found"))
            return

        # Check perfil
        perfil = PerfilEstudiante.objects.filter(user=student).first()
        if not perfil:
            self.stdout.write(self.style.WARNING("No PerfilEstudiante found, creating one..."))
            perfil = PerfilEstudiante.objects.create(
                user=student,
                estado='Activo'
            )

        # Check colegio and ciclo
        colegio = Colegio.objects.filter(rbd=student.rbd_colegio).first()
        if not colegio:
            self.stdout.write(self.style.ERROR("No colegio found for student"))
            return

        ciclo = CicloAcademico.objects.filter(colegio=colegio, estado='ACTIVO').first()
        if not ciclo:
            self.stdout.write(self.style.WARNING("No active ciclo found, creating one..."))
            from django.utils import timezone
            from datetime import date
            ciclo = CicloAcademico.objects.create(
                colegio=colegio,
                nombre='2024-2025',
                fecha_inicio=date(2024, 3, 1),
                fecha_fin=date(2025, 12, 31),
                estado='ACTIVO',
                creado_por=student  # This might not be correct, but for testing
            )

        # Set ciclo_actual on perfil
        if not perfil.ciclo_actual:
            perfil.ciclo_actual = ciclo
            perfil.save()
            self.stdout.write(f"Set ciclo_actual to {ciclo}")

        # Check for courses in this cycle
        cursos = Curso.objects.filter(colegio=colegio, ciclo_academico=ciclo)
        if not cursos.exists():
            self.stdout.write(self.style.WARNING("No courses found in cycle, creating a test course..."))
            from backend.apps.institucion.models import NivelEducativo
            nivel = NivelEducativo.objects.filter(nombre='Básica').first()
            if not nivel:
                nivel = NivelEducativo.objects.create(nombre='Básica')
            
            curso = Curso.objects.create(
                colegio=colegio,
                nombre='1° Básico A',
                nivel=nivel,
                ciclo_academico=ciclo
            )
            cursos = [curso]

        # Check matricula
        matricula = Matricula.objects.filter(
            estudiante=student,
            curso__ciclo_academico=ciclo,
            estado='ACTIVA'
        ).first()

        if not matricula:
            self.stdout.write(self.style.WARNING("No active matricula found, creating one..."))
            curso = cursos.first()
            matricula = Matricula.objects.create(
                estudiante=student,
                curso=curso,
                estado='ACTIVA',
                colegio=colegio
            )

        self.stdout.write(self.style.SUCCESS("Student data setup complete"))
        self.stdout.write(f"Perfil: {perfil}")
        self.stdout.write(f"Ciclo: {perfil.ciclo_actual}")
        self.stdout.write(f"Curso actual: {perfil.curso_actual}")
        self.stdout.write(f"Matricula: {matricula}")