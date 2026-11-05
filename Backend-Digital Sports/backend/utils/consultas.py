from backend.extensions import db
from backend.utils.respuestas import ApiError


def obtener_o_404(modelo, id_valor, mensaje='Recurso no encontrado.'):
    obj = db.session.get(modelo, id_valor)
    if obj is None:
        raise ApiError(mensaje, 404)
    return obj
