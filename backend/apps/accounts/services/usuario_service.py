from __future__ import annotations

from typing import Any, Dict

from .user_service import UserService


class UsuarioService:
    @staticmethod
    def create(actor, data: Dict[str, Any]):
        return UserService.create(actor=actor, data=data)

    @staticmethod
    def update(actor, user_id: int, data: Dict[str, Any]):
        return UserService.update(actor=actor, user_id=user_id, data=data)

    @staticmethod
    def delete(actor, user_id: int):
        return UserService.delete(actor=actor, user_id=user_id)

    @staticmethod
    def get(user_id: int):
        return UserService.get(user_id=user_id)

    @staticmethod
    def validations(data: Dict[str, Any], *, user_id: int | None = None):
        return UserService.validations(data=data, user_id=user_id)
