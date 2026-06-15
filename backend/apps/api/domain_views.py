from datetime import date

from django.db.models import Q
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from backend.apps.api.base import CapabilityModelViewSet
from backend.apps.api.domain_serializers import (
    AnotacionConvivenciaListSerializer,
    AnotacionConvivenciaSerializer,
    ComunicadoListSerializer,
    ComunicadoSerializer,
    ConversacionSerializer,
    DerivacionExternaSerializer,
    EntrevistaOrientacionSerializer,
    EstadoCuentaListSerializer,
    EstadoCuentaSerializer,
    JustificativoInasistenciaListSerializer,
    JustificativoInasistenciaSerializer,
    MensajeSerializer,
    PagoHistorialListSerializer,
    PagoHistorialSerializer,
)
from backend.apps.api.permissions import HasCapability
from backend.apps.comunicados.models import Comunicado
from backend.apps.core.models import (
    AnotacionConvivencia,
    DerivacionExterna,
    EntrevistaOrientacion,
    JustificativoInasistencia,
)
from backend.apps.matriculas.models import EstadoCuenta, Pago
from backend.apps.mensajeria.models import Conversacion, Mensaje
from backend.apps.mensajeria.services.mensajeria_service import MensajeriaService
from backend.apps.core.views.school_context import resolve_request_rbd
from backend.common.services.policy_service import PolicyService


def _is_global_admin(user):
    return PolicyService.has_capability(user, "SYSTEM_ADMIN")


def _school_id_for_request(request):
    return resolve_request_rbd(request)


class ComunicadoViewSet(CapabilityModelViewSet):
    queryset = Comunicado.objects.select_related("publicado_por", "colegio").prefetch_related("cursos_destinatarios")
    serializer_class = ComunicadoSerializer
    permission_classes = [IsAuthenticated, HasCapability]
    parser_classes = [MultiPartParser, FormParser]
    action_capabilities = {
        "list": "ANNOUNCEMENT_VIEW",
        "retrieve": "ANNOUNCEMENT_VIEW",
        "create": "ANNOUNCEMENT_CREATE",
        "update": "ANNOUNCEMENT_EDIT",
        "partial_update": "ANNOUNCEMENT_EDIT",
        "destroy": "ANNOUNCEMENT_DELETE",
        "send": "ANNOUNCEMENT_PUBLISH",
    }

    def get_queryset(self):
        qs = super().get_queryset().filter(activo=True)
        if _is_global_admin(self.request.user):
            return qs.order_by("-fecha_publicacion")
        return qs.filter(colegio_id=_school_id_for_request(self.request)).order_by("-fecha_publicacion")

    def get_serializer_class(self):
        if self.action == "list":
            return ComunicadoListSerializer
        return ComunicadoSerializer

    def perform_create(self, serializer):
        serializer.save(
            colegio_id=_school_id_for_request(self.request),
            publicado_por=self.request.user,
            activo=True,
        )

    @action(detail=True, methods=["post"])
    def send(self, request, pk=None):
        comunicado = self.get_object()
        comunicado.activo = True
        comunicado.fecha_publicacion = comunicado.fecha_publicacion or date.today()
        comunicado.save(update_fields=["activo", "fecha_publicacion"])
        return Response({"success": True, "message": "Comunicado enviado/publicado."})


class ConversacionViewSet(viewsets.GenericViewSet):
    queryset = Conversacion.objects.select_related("clase", "participante1", "participante2")
    serializer_class = ConversacionSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self):
        qs = Conversacion.objects.filter(
            Q(participante1=self.request.user) | Q(participante2=self.request.user)
        ).select_related("clase", "participante1", "participante2")
        if _is_global_admin(self.request.user):
            return qs.order_by("-ultima_actividad")
        return qs.filter(clase__colegio_id=_school_id_for_request(self.request)).order_by("-ultima_actividad")

    def list(self, request):
        serializer = self.get_serializer(self.get_queryset(), many=True)
        return Response(serializer.data)

    def create(self, request):
        clase_id = request.data.get("clase_id")
        destinatario_id = request.data.get("destinatario_id")
        if not clase_id or not destinatario_id:
            raise ValidationError({"detail": "Debe enviar clase_id y destinatario_id."})

        clase = MensajeriaService.get_class_for_messages(int(clase_id))
        if not MensajeriaService.user_has_access_to_class(request.user, clase):
            raise PermissionDenied("No tiene acceso a la clase.")

        destinatario = MensajeriaService.get_user_for_messages(int(destinatario_id))
        conversacion = MensajeriaService.get_or_create_conversacion(clase, request.user, destinatario)
        serializer = self.get_serializer(conversacion)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get", "post"], url_path="mensajes")
    def mensajes(self, request, pk=None):
        conversacion = self.get_object()

        if request.method.lower() == "get":
            MensajeriaService.mark_conversation_as_read(request.user, conversacion)
            mensajes = conversacion.mensajes.select_related("emisor", "receptor").order_by("fecha_envio")
            return Response(MensajeSerializer(mensajes, many=True).data)

        contenido = (request.data.get("contenido") or "").strip()
        archivo = request.FILES.get("archivo")
        is_valid, error_msg = MensajeriaService.validate_message_data(contenido, archivo)
        if not is_valid:
            raise ValidationError({"detail": error_msg})

        receptor = conversacion.get_otro_participante(request.user)
        mensaje = MensajeriaService.send_message(conversacion, request.user, receptor, contenido, archivo)
        return Response(MensajeSerializer(mensaje).data, status=status.HTTP_201_CREATED)


class AnotacionConvivenciaViewSet(CapabilityModelViewSet):
    queryset = AnotacionConvivencia.objects.select_related("estudiante", "registrado_por", "colegio")
    serializer_class = AnotacionConvivenciaSerializer
    permission_classes = [IsAuthenticated, HasCapability]
    action_capabilities = {
        "list": "DISCIPLINE_VIEW",
        "retrieve": "DISCIPLINE_VIEW",
        "create": "DISCIPLINE_CREATE",
        "update": "DISCIPLINE_EDIT",
        "partial_update": "DISCIPLINE_EDIT",
        "destroy": "DISCIPLINE_EDIT",
    }

    def get_queryset(self):
        qs = super().get_queryset()
        if _is_global_admin(self.request.user):
            return qs.order_by("-fecha")
        return qs.filter(colegio_id=_school_id_for_request(self.request)).order_by("-fecha")

    def get_serializer_class(self):
        if self.action == "list":
            return AnotacionConvivenciaListSerializer
        return AnotacionConvivenciaSerializer

    def perform_create(self, serializer):
        serializer.save(colegio_id=_school_id_for_request(self.request), registrado_por=self.request.user)


class EntrevistaOrientacionViewSet(CapabilityModelViewSet):
    queryset = EntrevistaOrientacion.objects.select_related("estudiante", "psicologo", "colegio")
    serializer_class = EntrevistaOrientacionSerializer
    permission_classes = [IsAuthenticated, HasCapability]
    action_capabilities = {
        "list": "COUNSELING_VIEW",
        "retrieve": "COUNSELING_VIEW",
        "create": "COUNSELING_CREATE",
        "update": "COUNSELING_EDIT",
        "partial_update": "COUNSELING_EDIT",
        "destroy": "COUNSELING_EDIT",
    }

    def get_queryset(self):
        qs = super().get_queryset()
        if _is_global_admin(self.request.user):
            return qs.order_by("-fecha")
        return qs.filter(colegio_id=_school_id_for_request(self.request)).order_by("-fecha")

    def perform_create(self, serializer):
        serializer.save(colegio_id=_school_id_for_request(self.request), psicologo=self.request.user)


class DerivacionExternaViewSet(CapabilityModelViewSet):
    queryset = DerivacionExterna.objects.select_related("estudiante", "derivado_por", "colegio")
    serializer_class = DerivacionExternaSerializer
    permission_classes = [IsAuthenticated, HasCapability]
    action_capabilities = {
        "list": "REFERRAL_VIEW",
        "retrieve": "REFERRAL_VIEW",
        "create": "REFERRAL_CREATE",
        "update": "REFERRAL_EDIT",
        "partial_update": "REFERRAL_EDIT",
        "destroy": "REFERRAL_EDIT",
    }

    def get_queryset(self):
        qs = super().get_queryset()
        if _is_global_admin(self.request.user):
            return qs.order_by("-fecha_derivacion")
        return qs.filter(colegio_id=_school_id_for_request(self.request)).order_by("-fecha_derivacion")

    def perform_create(self, serializer):
        serializer.save(colegio_id=_school_id_for_request(self.request), derivado_por=self.request.user)


class JustificativoInasistenciaViewSet(CapabilityModelViewSet):
    queryset = JustificativoInasistencia.objects.select_related("estudiante", "presentado_por", "colegio")
    serializer_class = JustificativoInasistenciaSerializer
    permission_classes = [IsAuthenticated, HasCapability]
    parser_classes = [MultiPartParser, FormParser]
    action_capabilities = {
        "list": "JUSTIFICATION_VIEW",
        "retrieve": "JUSTIFICATION_VIEW",
        "create": "DASHBOARD_VIEW_SELF",
    }
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        qs = super().get_queryset()
        if _is_global_admin(self.request.user):
            return qs.order_by("-fecha_ausencia")

        # Apoderados ven sus justificativos; inspector ve del colegio.
        if hasattr(self.request.user, "perfil_apoderado"):
            return qs.filter(presentado_por=self.request.user).order_by("-fecha_ausencia")

        return qs.filter(colegio_id=_school_id_for_request(self.request)).order_by("-fecha_ausencia")

    def get_serializer_class(self):
        if self.action == "list":
            return JustificativoInasistenciaListSerializer
        return JustificativoInasistenciaSerializer

    def perform_create(self, serializer):
        serializer.save(colegio_id=_school_id_for_request(self.request), presentado_por=self.request.user)


class PagoHistorialViewSet(CapabilityModelViewSet):
    queryset = Pago.objects.select_related("estudiante", "cuota", "cuota__matricula")
    serializer_class = PagoHistorialSerializer
    permission_classes = [IsAuthenticated, HasCapability]
    action_capabilities = {
        "list": "FINANCE_VIEW",
        "retrieve": "FINANCE_VIEW",
    }
    http_method_names = ["get", "head", "options"]

    def get_queryset(self):
        qs = super().get_queryset()
        if _is_global_admin(self.request.user):
            return qs.order_by("-fecha_pago")
        return qs.filter(cuota__matricula__colegio_id=_school_id_for_request(self.request)).order_by("-fecha_pago")

    def get_serializer_class(self):
        if self.action == "list":
            return PagoHistorialListSerializer
        return PagoHistorialSerializer


class EstadoCuentaViewSet(CapabilityModelViewSet):
    queryset = EstadoCuenta.objects.select_related("estudiante", "colegio")
    serializer_class = EstadoCuentaSerializer
    permission_classes = [IsAuthenticated, HasCapability]
    action_capabilities = {
        "list": "FINANCE_VIEW",
        "retrieve": "FINANCE_VIEW",
    }
    http_method_names = ["get", "head", "options"]

    def get_queryset(self):
        qs = super().get_queryset()
        if _is_global_admin(self.request.user):
            return qs.order_by("-anio", "-mes")
        return qs.filter(colegio_id=_school_id_for_request(self.request)).order_by("-anio", "-mes")

    def get_serializer_class(self):
        if self.action == "list":
            return EstadoCuentaListSerializer
        return EstadoCuentaSerializer
