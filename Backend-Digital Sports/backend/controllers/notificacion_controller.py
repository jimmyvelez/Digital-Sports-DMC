# =============================================================================
# Controlador: Notificaciones del usuario autenticado — /api/notificaciones
# Cada usuario solo ve y modifica sus propias notificaciones.
# =============================================================================
from flask import request

from backend.extensions import db
from backend.models.notificacion import Notificacion
from backend.utils.auth import login_requerido, usuario_actual
from backend.utils.respuestas import ApiError, paginar, respuesta_json
from backend.utils.tiempo import ahora


def _propias():
    return Notificacion.query.filter(Notificacion.id_usuario == usuario_actual().id_usuario)


@login_requerido
def listar_notificaciones():
    """GET /api/notificaciones — ?no_leidas=1"""
    query = _propias()
    if request.args.get('no_leidas') == '1':
        query = query.filter(Notificacion.leida.is_(False))
    data = paginar(query.order_by(Notificacion.fecha_creacion.desc(), Notificacion.id_notificacion.desc()),
                   lambda n: n.to_dict(), por_pagina_defecto=20)
    data['no_leidas'] = _propias().filter(Notificacion.leida.is_(False)).count()
    return respuesta_json(data)


@login_requerido
def conteo_no_leidas():
    return respuesta_json({'no_leidas': _propias().filter(Notificacion.leida.is_(False)).count()})


@login_requerido
def marcar_leida(id_notificacion):
    notificacion = _propias().filter(Notificacion.id_notificacion == id_notificacion).first()
    if not notificacion:  # 404 también si es de otro usuario: no se revela su existencia
        raise ApiError('Notificación no encontrada.', 404)
    if not notificacion.leida:
        notificacion.leida = True
        notificacion.fecha_lectura = ahora()
        db.session.commit()
    return respuesta_json(notificacion.to_dict())


@login_requerido
def marcar_todas():
    total = _propias().filter(Notificacion.leida.is_(False)).update(
        {'leida': True, 'fecha_lectura': ahora()}, synchronize_session=False)
    db.session.commit()
    return respuesta_json({'mensaje': f'{total} notificación(es) marcadas como leídas.', 'actualizadas': total})
