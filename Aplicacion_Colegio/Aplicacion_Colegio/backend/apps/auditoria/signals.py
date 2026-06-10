"""
Señales de Auditoría
Thread-local storage para usuario y request actuales.
"""

from threading import local

# Thread-local storage para request
_thread_locals = local()


def get_current_user():
    """
    Obtiene el usuario actual desde thread-local storage.
    Debe ser configurado por middleware.
    """
    return getattr(_thread_locals, 'user', None)


def get_current_request():
    """
    Obtiene el request actual desde thread-local storage.
    """
    return getattr(_thread_locals, 'request', None)


def set_current_user(user):
    """
    Establece el usuario actual en thread-local storage.
    Llamado por middleware.
    """
    _thread_locals.user = user


def set_current_request(request):
    """
    Establece el request actual en thread-local storage.
    """
    _thread_locals.request = request
