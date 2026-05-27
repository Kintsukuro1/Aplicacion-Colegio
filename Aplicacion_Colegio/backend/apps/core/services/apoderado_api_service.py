"""
Service para operaciones de Apoderado vía API.
Centraliza el acceso ORM para justificativos e inasistencias.
"""
from __future__ import annotations

import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class ApoderadoApiService:
    """Encapsula las operaciones ORM del apoderado para mantener las vistas libres de acceso directo."""

    # ------------------------------------------------------------------
    # Utilidades internas
    # ------------------------------------------------------------------

    @staticmethod
    def get_estudiante_ids_for_apoderado(user) -> list[int]:
        """Retorna IDs de estudiantes vinculados al apoderado activo."""
        from backend.apps.accounts.models import RelacionApoderadoEstudiante

        perfil_apoderado = getattr(user, 'perfil_apoderado', None)
        if not perfil_apoderado:
            return []

        return list(
            RelacionApoderadoEstudiante.objects.filter(
                apoderado_id=perfil_apoderado.id,
                activa=True,
            ).values_list('estudiante_id', flat=True)
        )

    @staticmethod
    def get_estudiante_or_none(estudiante_id: int, rbd: int):
        """Retorna usuario estudiante si pertenece al colegio; None si no existe."""
        from backend.apps.accounts.models import User

        try:
            return User.objects.get(id=estudiante_id, rbd_colegio=rbd)
        except User.DoesNotExist:
            return None

    # ------------------------------------------------------------------
    # Justificativos
    # ------------------------------------------------------------------

    @staticmethod
    def list_justificativos(user, rbd: int) -> list[dict]:
        """Lista justificativos del apoderado para el colegio dado."""
        from backend.apps.core.models import JustificativoInasistencia

        qs = (
            JustificativoInasistencia.objects.filter(
                presentado_por=user,
                colegio_id=rbd,
            )
            .select_related('estudiante')
            .order_by('-fecha_creacion')
        )

        result = []
        for j in qs:
            result.append({
                'id': j.id_justificativo,
                'estudiante': j.estudiante.get_full_name(),
                'fecha_ausencia': j.fecha_ausencia.strftime('%d/%m/%Y'),
                'fecha_fin': j.fecha_fin_ausencia.strftime('%d/%m/%Y') if j.fecha_fin_ausencia else None,
                'tipo': j.get_tipo_display(),
                'motivo': j.motivo,
                'estado': j.estado,
                'estado_display': j.get_estado_display(),
                'tiene_adjunto': bool(j.documento_adjunto),
                'observaciones_revision': j.observaciones_revision or '',
                'fecha_creacion': j.fecha_creacion.strftime('%d/%m/%Y %H:%M'),
            })
        return result

    @staticmethod
    def crear_justificativo(
        *,
        user,
        rbd: int,
        estudiante,
        fecha_ausencia: str,
        fecha_fin_ausencia,
        motivo: str,
        tipo: str,
        documento=None,
    ):
        """Crea un JustificativoInasistencia y retorna la instancia."""
        from backend.apps.core.models import JustificativoInasistencia

        return JustificativoInasistencia.objects.create(
            estudiante=estudiante,
            colegio_id=rbd,
            fecha_ausencia=fecha_ausencia,
            fecha_fin_ausencia=fecha_fin_ausencia,
            motivo=motivo,
            tipo=tipo,
            documento_adjunto=documento,
            presentado_por=user,
        )

    # ------------------------------------------------------------------
    # Firma digital
    # ------------------------------------------------------------------

    @staticmethod
    def list_firmas_apoderado(apoderado) -> tuple[list, list]:
        """Retorna (pendientes, firmados) para el apoderado."""
        from backend.apps.accounts.models import FirmaDigitalApoderado

        firmas_qs = (
            FirmaDigitalApoderado.objects.filter(apoderado=apoderado)
            .select_related('estudiante')
            .order_by('-timestamp_firma')
        )

        firmados = []
        for firma in firmas_qs:
            firmados.append({
                'id': firma.id,
                'tipo': firma.get_tipo_documento_display(),
                'titulo': firma.titulo_documento,
                'estudiante': firma.estudiante.get_full_name() if firma.estudiante else '',
                'fecha_firma': firma.timestamp_firma.strftime('%d/%m/%Y %H:%M'),
                'valida': firma.firma_valida,
            })

        # TODO: Implement pending document detection
        return [], firmados

    @staticmethod
    def firmar_documento(*, apoderado, tipo_documento: str, titulo: str, contenido: str,
                         ip_address: str, user_agent: str, estudiante=None):
        """Crea una FirmaDigitalApoderado y retorna la instancia."""
        from backend.apps.accounts.models import FirmaDigitalApoderado

        return FirmaDigitalApoderado.crear_firma(
            apoderado=apoderado,
            tipo_documento=tipo_documento,
            titulo=titulo,
            contenido=contenido,
            ip_address=ip_address,
            user_agent=user_agent,
            estudiante=estudiante,
        )

    @staticmethod
    def crear_solicitud_admision(
        *,
        user,
        rbd: int,
        curso_id: int,
        ciclo_id: int,
        nombre_est: str,
        paterno_est: str,
        materno_est: str,
        rut_est: str = None,
        nacimiento_est=None,
        genero_est: str = 'O',
        direccion: str = '',
        telefono: str = '',
        parentesco: str = 'OTRO',
        certificado_nacimiento=None,
        certificado_medico=None
    ):
        """Crea una postulación de admisión y maneja la lógica de cola/lista de espera."""
        from backend.apps.matriculas.models import SolicitudAdmision, Matricula
        from backend.apps.cursos.models import Curso
        from backend.apps.accounts.models import User
        from django.utils import timezone
        
        # 1. Verificar si el curso está lleno (límite de 3 matrículas activas para pruebas)
        matriculas_activas = Matricula.objects.filter(
            curso_id=curso_id,
            estado='ACTIVA'
        ).count()
        
        limite_cupos = 3
        if matriculas_activas >= limite_cupos:
            estado = 'EN_LISTA_ESPERA'
            # Calcular posición en la cola
            solicitudes_cola = SolicitudAdmision.objects.filter(
                colegio_id=rbd,
                curso_postulado_id=curso_id,
                estado='EN_LISTA_ESPERA'
            ).count()
            posicion_lista_espera = solicitudes_cola + 1
        else:
            estado = 'PENDIENTE'
            posicion_lista_espera = None
            
        # 2. Intentar buscar estudiante existente por RUT o nombres
        estudiante_existente = None
        if rut_est:
            estudiante_existente = User.objects.filter(
                rut=rut_est,
                role__nombre='Estudiante'
            ).first()
            
        # 3. Crear solicitud
        solicitud = SolicitudAdmision.objects.create(
            colegio_id=rbd,
            apoderado=user,
            ciclo_academico_id=ciclo_id,
            curso_postulado_id=curso_id,
            estudiante=estudiante_existente,
            nombre_estudiante=nombre_est,
            apellido_paterno_estudiante=paterno_est,
            apellido_materno_estudiante=materno_est,
            rut_estudiante=rut_est,
            fecha_nacimiento_estudiante=nacimiento_est,
            genero_estudiante=genero_est,
            direccion_hogar=direccion,
            telefono_contacto=telefono,
            parentesco=parentesco,
            certificado_nacimiento=certificado_nacimiento,
            certificado_medico=certificado_medico,
            estado=estado,
            posicion_lista_espera=posicion_lista_espera
        )
        
        # 4. Actualizar ficha del apoderado
        perfil_apoderado = getattr(user, 'perfil_apoderado', None)
        if perfil_apoderado:
            if direccion:
                perfil_apoderado.direccion = direccion
            if telefono:
                perfil_apoderado.telefono = telefono
            perfil_apoderado.save(update_fields=['direccion', 'telefono'])
            
        return solicitud

    @staticmethod
    def firmar_contrato_admision(
        *,
        user,
        solicitud_id: int,
        rut_firmante: str,
        ip_address: str,
        user_agent: str
    ):
        """Firma el contrato de admisión con Firma Electrónica Simple y matricula al estudiante."""
        import uuid
        import hashlib
        from decimal import Decimal
        from django.utils import timezone
        from backend.apps.matriculas.models import SolicitudAdmision, ContratoServicioEducacional, Matricula
        from backend.apps.accounts.models import User, Role, PerfilEstudiante, RelacionApoderadoEstudiante
        
        # 1. Obtener y validar solicitud
        solicitud = SolicitudAdmision.objects.all_schools().get(
            id_solicitud=solicitud_id,
            apoderado=user,
            colegio_id=user.rbd_colegio
        )
        
        if solicitud.estado != 'ACEPTADA':
            raise ValueError('La solicitud no está aceptada para firma.')
            
        # 2. Obtener o crear contrato educacional
        contrato, created = ContratoServicioEducacional.objects.get_or_create(
            solicitud=solicitud,
            defaults={
                'colegio_id': solicitud.colegio_id,
                'apoderado': user,
                'ciclo_academico_id': solicitud.ciclo_academico_id,
                'cuerpo_contrato': (
                    f"Contrato de Prestación de Servicios Educacionales para el estudiante "
                    f"{solicitud.nombre_estudiante} {solicitud.apellido_paterno_estudiante}. "
                    f"Este contrato regula las obligaciones financieras de mensualidad (Arancel Anual $2,500,000 "
                    f"dividido en 10 cuotas) y matrícula ($150,000) correspondientes al ciclo académico "
                    f"{solicitud.ciclo_academico.nombre} en la institución."
                )
            }
        )
        
        # 3. Generar Firma Electrónica Simple
        firma_token = str(uuid.uuid4())
        timestamp_str = timezone.now().isoformat()
        datos_firma = f"{contrato.cuerpo_contrato}|{rut_firmante}|{ip_address}|{timestamp_str}"
        firma_hash = hashlib.sha256(datos_firma.encode('utf-8')).hexdigest()
        
        contrato.firmado = True
        contrato.fecha_firma = timezone.now()
        contrato.ip_firma = ip_address
        contrato.user_agent_firma = user_agent
        contrato.rut_firmante = rut_firmante
        contrato.firma_hash = firma_hash
        contrato.firma_token = firma_token
        contrato.save()
        
        # 4. Actualizar estado de la solicitud
        solicitud.estado = 'FIRMADA'
        solicitud.save(update_fields=['estado'])
        
        # 5. Crear usuario de Estudiante si no existe
        student_user = solicitud.estudiante
        if not student_user:
            role_estudiante = Role.objects.get(nombre='Estudiante')
            
            # Generar username único
            base_username = (
                f"{solicitud.nombre_estudiante.lower().replace(' ', '')}."
                f"{solicitud.apellido_paterno_estudiante.lower().replace(' ', '')}"
            )
            username = base_username
            counter = 1
            while User.objects.filter(email=f"{username}@colegio.cl").exists():
                username = f"{base_username}{counter}"
                counter += 1
                
            student_user = User.objects.create_user(
                username=username,
                email=f"{username}@colegio.cl",
                password=f"Estudiante.{solicitud.rut_estudiante or '12345678'}",
                nombre=solicitud.nombre_estudiante,
                apellido_paterno=solicitud.apellido_paterno_estudiante,
                apellido_materno=solicitud.apellido_materno_estudiante,
                rut=solicitud.rut_estudiante,
                role=role_estudiante,
                rbd_colegio=solicitud.colegio_id
            )
            
            # Crear perfil de estudiante
            PerfilEstudiante.objects.create(
                user=student_user,
                estado_academico='Activo',
                curso_actual_id=solicitud.curso_postulado,
                ciclo_actual=solicitud.ciclo_academico
            )
            
            solicitud.estudiante = student_user
            solicitud.save(update_fields=['estudiante'])
            
        # 6. Crear relación de apoderado-estudiante si no existe
        perfil_apoderado = getattr(user, 'perfil_apoderado', None)
        if perfil_apoderado:
            parentesco_norm = solicitud.parentesco.lower() if solicitud.parentesco in ['PADRE', 'MADRE', 'ABUELO', 'TIO', 'TUTOR_LEGAL', 'OTRO'] else 'otro'
            RelacionApoderadoEstudiante.objects.get_or_create(
                apoderado=perfil_apoderado,
                estudiante=student_user,
                defaults={
                    'tipo_apoderado': 'principal',
                    'parentesco': parentesco_norm,
                    'activa': True
                }
            )
            
        # 7. Crear Matrícula oficial activa
        Matricula.objects.create(
            estudiante=student_user,
            colegio_id=solicitud.colegio_id,
            curso=solicitud.curso_postulado,
            estado='ACTIVA',
            ciclo_academico=solicitud.ciclo_academico,
            valor_matricula=contrato.valor_matricula,
            valor_mensual=contrato.valor_arancel_anual / Decimal(str(contrato.numero_cuotas))
        )
        
        return contrato
