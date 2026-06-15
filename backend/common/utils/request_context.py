"""Contexto de request para trazabilidad transversal (request-id)."""

from contextvars import ContextVar

_request_id_var: ContextVar[str] = ContextVar('request_id', default='-')


def set_request_id(request_id: str) -> None:
    _request_id_var.set(request_id or '-')


def get_request_id() -> str:
    return _request_id_var.get()


def clear_request_id() -> None:
    _request_id_var.set('-')
