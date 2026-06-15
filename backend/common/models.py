"""
Modelos base compartidos
"""
from django.db import models


class TimeStampedModel(models.Model):
    """Modelo abstracto con campos de auditoría temporal"""
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Creado el")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Actualizado el")

    class Meta:
        abstract = True
