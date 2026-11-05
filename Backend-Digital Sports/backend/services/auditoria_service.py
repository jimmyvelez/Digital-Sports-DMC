"""Registro del historial de cambios importantes."""
import json

from backend.extensions import db
from backend.models.auditoria import Auditoria
from backend.utils.auth import usuario_actual


def registrar(accion, entidad, id_entidad=None, detalle=None, usuario=None):
    """
    Agrega un registro de auditoría a la sesión actual. No hace commit:
    se confirma en la misma transacción que la operación auditada.
    """
    usuario = usuario or usuario_actual()
    db.session.add(Auditoria(
        id_usuario=usuario.id_usuario if usuario else None,
        accion=accion,
        entidad=entidad,
        id_entidad=id_entidad,
        detalle=json.dumps(detalle, ensure_ascii=False, default=str) if detalle is not None else None,
    ))
