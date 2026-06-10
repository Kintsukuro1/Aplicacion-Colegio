from rest_framework import serializers

from backend.apps.comunicados.models import Comunicado
from backend.apps.core.models import (
    AnotacionConvivencia,
    DerivacionExterna,
    EntrevistaOrientacion,
    JustificativoInasistencia,
)
from backend.apps.matriculas.models import Boleta, EstadoCuenta, Pago
from backend.apps.mensajeria.models import Conversacion, Mensaje


class ComunicadoSerializer(serializers.ModelSerializer):
    publicado_por_nombre = serializers.CharField(source="publicado_por.get_full_name", read_only=True)

    class Meta:
        model = Comunicado
        fields = [
            "id_comunicado",
            "colegio",
            "tipo",
            "titulo",
            "contenido",
            "destinatario",
            "cursos_destinatarios",
            "archivo_adjunto",
            "fecha_evento",
            "lugar_evento",
            "requiere_confirmacion",
            "es_prioritario",
            "es_destacado",
            "activo",
            "publicado_por",
            "publicado_por_nombre",
            "fecha_publicacion",
            "fecha_creacion",
            "fecha_actualizacion",
        ]
        read_only_fields = [
            "id_comunicado",
            "publicado_por",
            "publicado_por_nombre",
            "fecha_publicacion",
            "fecha_creacion",
            "fecha_actualizacion",
        ]


class ComunicadoListSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source="id_comunicado", read_only=True)
    nombre = serializers.CharField(source="titulo", read_only=True)
    estado = serializers.SerializerMethodField()

    class Meta:
        model = Comunicado
        fields = [
            "id",
            "nombre",
            "estado",
        ]

    def get_estado(self, obj):
        return "ACTIVO" if obj.activo else "INACTIVO"


class ConversacionSerializer(serializers.ModelSerializer):
    otro_participante_id = serializers.SerializerMethodField()
    otro_participante_nombre = serializers.SerializerMethodField()
    no_leidos = serializers.SerializerMethodField()

    class Meta:
        model = Conversacion
        fields = [
            "id_conversacion",
            "clase",
            "participante1",
            "participante2",
            "fecha_creacion",
            "ultima_actividad",
            "otro_participante_id",
            "otro_participante_nombre",
            "no_leidos",
        ]
        read_only_fields = [
            "id_conversacion",
            "participante1",
            "participante2",
            "fecha_creacion",
            "ultima_actividad",
            "otro_participante_id",
            "otro_participante_nombre",
            "no_leidos",
        ]

    def get_otro_participante_id(self, obj):
        user = self.context["request"].user
        return obj.get_otro_participante(user).id

    def get_otro_participante_nombre(self, obj):
        user = self.context["request"].user
        return obj.get_otro_participante(user).get_full_name()

    def get_no_leidos(self, obj):
        user = self.context["request"].user
        return obj.mensajes.filter(receptor=user, leido=False).count()


class MensajeSerializer(serializers.ModelSerializer):
    emisor_nombre = serializers.CharField(source="emisor.get_full_name", read_only=True)
    receptor_nombre = serializers.CharField(source="receptor.get_full_name", read_only=True)

    class Meta:
        model = Mensaje
        fields = [
            "id_mensaje",
            "conversacion",
            "emisor",
            "emisor_nombre",
            "receptor",
            "receptor_nombre",
            "contenido",
            "archivo_adjunto",
            "leido",
            "fecha_envio",
            "fecha_lectura",
        ]
        read_only_fields = [
            "id_mensaje",
            "emisor",
            "emisor_nombre",
            "receptor",
            "receptor_nombre",
            "leido",
            "fecha_envio",
            "fecha_lectura",
        ]


class AnotacionConvivenciaSerializer(serializers.ModelSerializer):
    estudiante_nombre = serializers.CharField(source="estudiante.get_full_name", read_only=True)
    registrado_por_nombre = serializers.CharField(source="registrado_por.get_full_name", read_only=True)

    class Meta:
        model = AnotacionConvivencia
        fields = [
            "id_anotacion",
            "estudiante",
            "estudiante_nombre",
            "colegio",
            "tipo",
            "categoria",
            "descripcion",
            "gravedad",
            "registrado_por",
            "registrado_por_nombre",
            "fecha",
            "notificado_apoderado",
            "fecha_notificacion",
        ]
        read_only_fields = ["id_anotacion", "colegio", "registrado_por", "registrado_por_nombre"]


class AnotacionConvivenciaListSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source="id_anotacion", read_only=True)
    nombre = serializers.CharField(source="estudiante.get_full_name", read_only=True)
    estado = serializers.SerializerMethodField()

    class Meta:
        model = AnotacionConvivencia
        fields = [
            "id",
            "nombre",
            "estado",
        ]

    def get_estado(self, obj):
        return obj.tipo


class EntrevistaOrientacionSerializer(serializers.ModelSerializer):
    estudiante_nombre = serializers.CharField(source="estudiante.get_full_name", read_only=True)
    psicologo_nombre = serializers.CharField(source="psicologo.get_full_name", read_only=True)

    class Meta:
        model = EntrevistaOrientacion
        fields = [
            "id_entrevista",
            "estudiante",
            "estudiante_nombre",
            "colegio",
            "psicologo",
            "psicologo_nombre",
            "fecha",
            "motivo",
            "observaciones",
            "acuerdos",
            "recomendaciones_profesor",
            "seguimiento_requerido",
            "fecha_siguiente_sesion",
            "confidencial",
        ]
        read_only_fields = ["id_entrevista", "colegio", "psicologo", "psicologo_nombre"]


class DerivacionExternaSerializer(serializers.ModelSerializer):
    estudiante_nombre = serializers.CharField(source="estudiante.get_full_name", read_only=True)
    derivado_por_nombre = serializers.CharField(source="derivado_por.get_full_name", read_only=True)

    class Meta:
        model = DerivacionExterna
        fields = [
            "id_derivacion",
            "estudiante",
            "estudiante_nombre",
            "colegio",
            "derivado_por",
            "derivado_por_nombre",
            "profesional_destino",
            "especialidad",
            "motivo",
            "estado",
            "fecha_derivacion",
            "fecha_retorno",
            "informe_retorno",
        ]
        read_only_fields = ["id_derivacion", "colegio", "derivado_por", "derivado_por_nombre"]


class JustificativoInasistenciaSerializer(serializers.ModelSerializer):
    estudiante_nombre = serializers.CharField(source="estudiante.get_full_name", read_only=True)
    presentado_por_nombre = serializers.CharField(source="presentado_por.get_full_name", read_only=True)

    class Meta:
        model = JustificativoInasistencia
        fields = [
            "id_justificativo",
            "estudiante",
            "estudiante_nombre",
            "colegio",
            "fecha_ausencia",
            "fecha_fin_ausencia",
            "motivo",
            "tipo",
            "documento_adjunto",
            "estado",
            "presentado_por",
            "presentado_por_nombre",
            "revisado_por",
            "fecha_revision",
            "observaciones_revision",
            "fecha_creacion",
        ]
        read_only_fields = [
            "id_justificativo",
            "colegio",
            "estado",
            "presentado_por",
            "presentado_por_nombre",
            "revisado_por",
            "fecha_revision",
            "observaciones_revision",
            "fecha_creacion",
        ]


class JustificativoInasistenciaListSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source="id_justificativo", read_only=True)
    nombre = serializers.CharField(source="estudiante.get_full_name", read_only=True)
    estado = serializers.CharField(read_only=True)

    class Meta:
        model = JustificativoInasistencia
        fields = [
            "id",
            "nombre",
            "estado",
        ]


class PagoHistorialSerializer(serializers.ModelSerializer):
    estudiante_nombre = serializers.CharField(source="estudiante.get_full_name", read_only=True)
    cuota_numero = serializers.IntegerField(source="cuota.numero_cuota", read_only=True)

    class Meta:
        model = Pago
        fields = [
            "id",
            "cuota",
            "cuota_numero",
            "estudiante",
            "estudiante_nombre",
            "monto",
            "metodo_pago",
            "estado",
            "numero_comprobante",
            "fecha_pago",
        ]


class PagoHistorialListSerializer(serializers.ModelSerializer):
    nombre = serializers.CharField(source="estudiante.get_full_name", read_only=True)

    class Meta:
        model = Pago
        fields = [
            "id",
            "nombre",
            "estado",
        ]


class EstadoCuentaSerializer(serializers.ModelSerializer):
    estudiante_nombre = serializers.CharField(source="estudiante.get_full_name", read_only=True)

    class Meta:
        model = EstadoCuenta
        fields = [
            "id",
            "estudiante",
            "estudiante_nombre",
            "colegio",
            "mes",
            "anio",
            "total_deuda",
            "total_pagado",
            "saldo_pendiente",
            "estado",
            "fecha_generacion",
            "fecha_envio",
            "observaciones",
        ]


class EstadoCuentaListSerializer(serializers.ModelSerializer):
    nombre = serializers.CharField(source="estudiante.get_full_name", read_only=True)

    class Meta:
        model = EstadoCuenta
        fields = [
            "id",
            "nombre",
            "estado",
        ]


class BoletaSerializer(serializers.ModelSerializer):
    estudiante_nombre = serializers.CharField(source="estudiante.get_full_name", read_only=True)

    class Meta:
        model = Boleta
        fields = [
            "id",
            "numero_boleta",
            "pago",
            "estudiante",
            "estudiante_nombre",
            "monto_total",
            "detalle",
            "estado",
            "fecha_emision",
        ]
