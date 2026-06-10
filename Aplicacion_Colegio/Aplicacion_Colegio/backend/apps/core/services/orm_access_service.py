from __future__ import annotations


class ORMAccessService:
    """Wrapper central para acceso ORM desde servicios/controladores del core."""

    @staticmethod
    def create(model, **kwargs):
        return model.objects.create(**kwargs)

    @staticmethod
    def get(model, **kwargs):
        return model.objects.get(**kwargs)

    @staticmethod
    def filter(model, **kwargs):
        return model.objects.filter(**kwargs)

    @staticmethod
    def update(queryset, **kwargs):
        return queryset.update(**kwargs)

    @staticmethod
    def delete(queryset):
        return queryset.delete()

    @staticmethod
    def get_or_create(model, defaults=None, **kwargs):
        return model.objects.get_or_create(defaults=defaults, **kwargs)

    @staticmethod
    def update_or_create(model, defaults=None, **kwargs):
        return model.objects.update_or_create(defaults=defaults, **kwargs)
