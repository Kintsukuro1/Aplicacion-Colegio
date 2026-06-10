import pytest
from django.contrib.auth import get_user_model

from backend.apps.accounts.models import Role as Rol
from backend.apps.institucion.models import Colegio

User = get_user_model()
pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _disable_https_redirect_for_tests(settings):
    settings.SECURE_SSL_REDIRECT = False
    settings.SESSION_COOKIE_SECURE = False
    settings.CSRF_COOKIE_SECURE = False
    settings.SECURE_HSTS_SECONDS = 0
    settings.SECURE_HSTS_INCLUDE_SUBDOMAINS = False
    settings.SECURE_HSTS_PRELOAD = False
    settings.SECURE_PROXY_SSL_HEADER = None


@pytest.fixture
def rol_admin(db):
    rol, _ = Rol.objects.get_or_create(nombre="Admin")
    return rol


@pytest.fixture
def colegio(db):
    colegio, _ = Colegio.objects.get_or_create(
        rbd=99001,
        defaults={
            "rut_establecimiento": "99001-K",
            "nombre": "Colegio Test",
        },
    )
    return colegio


@pytest.fixture
def admin_user(db, colegio, rol_admin):
    user, created = User.objects.get_or_create(
        email="admin@test.com",
        defaults={
            "nombre": "Admin",
            "apellido_paterno": "Test",
            "rbd_colegio": colegio.rbd,
            "role": rol_admin,
            "is_active": True,
            "is_staff": True,
        },
    )

    if created:
        user.set_password("testpass123")
        user.save(update_fields=["password"])

    return user
