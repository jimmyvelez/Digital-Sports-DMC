# =============================================================================
# Controlador: Historial de cambios — /api/auditoria (solo administrador)
# =============================================================================
from flask import request

from backend.models.auditoria import Auditoria
from backend.utils.auth import roles_requeridos
from backend.utils.respuestas import paginar, respuesta_json


@roles_requeridos('admin')
def listar_auditoria():
    """GET /api/auditoria — Filtros: ?entidad=&accion=&id_usuario="""
    query = Auditoria.query
    for campo in ('entidad', 'accion'):
        if request.args.get(campo):
            query = query.filter(getattr(Auditoria, campo) == request.args[campo])
    if request.args.get('id_usuario', '').isdigit():
        query = query.filter(Auditoria.id_usuario == int(request.args['id_usuario']))
    return respuesta_json(paginar(query.order_by(Auditoria.fecha.desc(), Auditoria.id_auditoria.desc()),
                                  lambda a: a.to_dict()))
