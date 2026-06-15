from rest_framework import serializers

from backend.apps.notificaciones.models import DispositivoMovil, Notificacion
from backend.apps.notificaciones.services.notification_link_service import normalize_notification_enlace


class UserContextSerializer(serializers.Serializer):
    class SessionUserSerializer(serializers.Serializer):
        id = serializers.IntegerField()
        name = serializers.CharField()
        role = serializers.CharField(allow_null=True)
        email = serializers.EmailField()

    class SessionSchoolSerializer(serializers.Serializer):
        id = serializers.IntegerField()
        name = serializers.CharField(allow_null=True)

    id = serializers.IntegerField()
    email = serializers.EmailField()
    full_name = serializers.CharField()
    role = serializers.CharField(allow_null=True)
    rbd_colegio = serializers.IntegerField(allow_null=True)
    capabilities = serializers.ListField(child=serializers.CharField())
    user = SessionUserSerializer(required=False)
    school = SessionSchoolSerializer(required=False, allow_null=True)


class NotificationSerializer(serializers.ModelSerializer):
    enlace = serializers.SerializerMethodField()

    class Meta:
        model = Notificacion
        fields = [
            'id',
            'tipo',
            'titulo',
            'mensaje',
            'enlace',
            'prioridad',
            'leido',
            'fecha_creacion',
            'fecha_lectura',
        ]

    def get_enlace(self, obj: Notificacion) -> str:
        return normalize_notification_enlace(
            obj.enlace,
            obj.tipo,
            titulo=obj.titulo,
            mensaje=obj.mensaje,
        )


class DeviceRegistrationSerializer(serializers.Serializer):
    token_fcm = serializers.CharField(max_length=255)
    plataforma = serializers.ChoiceField(choices=DispositivoMovil.PLATAFORMA_CHOICES)
    nombre_dispositivo = serializers.CharField(required=False, allow_blank=True, max_length=100)
    modelo = serializers.CharField(required=False, allow_blank=True, max_length=100)
    version_app = serializers.CharField(required=False, allow_blank=True, max_length=20)


class DeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = DispositivoMovil
        fields = [
            'id',
            'plataforma',
            'nombre_dispositivo',
            'modelo',
            'version_app',
            'activo',
            'fecha_registro',
            'ultima_actividad',
        ]
