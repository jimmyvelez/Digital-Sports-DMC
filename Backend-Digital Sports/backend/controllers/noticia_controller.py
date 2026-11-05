# =============================================================================
# Controlador: Noticias — /api/noticias (los comentarios están en comentario_routes.py)
# Las URLs se declaran en backend/routes/noticia_routes.py
# =============================================================================
import re

from flask import request
from sqlalchemy import and_, or_

from backend.extensions import db
from backend.models.noticia import ESTADOS_NOTICIA, Noticia
from backend.services import auditoria_service
from backend.services.permisos import exigir, puede_gestionar_noticia
from backend.utils.auth import roles_requeridos, usuario_actual
from backend.utils.consultas import obtener_o_404
from backend.utils.respuestas import ApiError, paginar, respuesta_json
from backend.utils.tiempo import ahora
from backend.utils import validacion as v


def _es_visible_publicamente(noticia):
    return (noticia.estado == 'publicada' and noticia.fecha_publicacion is not None
            and noticia.fecha_publicacion <= ahora())


def _puede_ver(usuario, noticia):
    return _es_visible_publicamente(noticia) or puede_gestionar_noticia(usuario, noticia)


def _serializar(noticia, usuario, resumen=False):
    data = noticia.to_dict(resumen=resumen)
    data['puede_gestionar'] = puede_gestionar_noticia(usuario, noticia)
    data['visible'] = _es_visible_publicamente(noticia)
    return data


# -----------------------------------------------------------------------------
# Noticias
# -----------------------------------------------------------------------------
def listar_noticias():
    """
    GET /api/noticias — Público: solo publicadas. Docente: publicadas + propias.
    Admin: todas. Filtros: ?estado=&q=&mias=1
    """
    usuario = usuario_actual()
    query = Noticia.query
    publicadas = and_(Noticia.estado == 'publicada', Noticia.fecha_publicacion <= ahora())
    if usuario is None or usuario.rol == 'estudiante':
        query = query.filter(publicadas)
    elif usuario.rol == 'docente':
        query = query.filter(or_(publicadas, Noticia.id_autor == usuario.id_usuario))
    if request.args.get('mias') == '1' and usuario:
        query = query.filter(Noticia.id_autor == usuario.id_usuario)
    estado = request.args.get('estado')
    if estado:
        query = query.filter(Noticia.estado == estado)
    q = (request.args.get('q') or '').strip()
    if q:
        query = query.filter(or_(Noticia.titulo.ilike(f'%{q}%'), Noticia.descripcion.ilike(f'%{q}%')))
    query = query.order_by(Noticia.fecha_publicacion.desc(), Noticia.id_noticia.desc())
    return respuesta_json(paginar(query, lambda n: _serializar(n, usuario, resumen=True), por_pagina_defecto=12))


def detalle_noticia(id_noticia):
    usuario = usuario_actual()
    noticia = obtener_o_404(Noticia, id_noticia, 'Noticia no encontrada.')
    if not _puede_ver(usuario, noticia):
        raise ApiError('Noticia no encontrada.', 404)
    return respuesta_json(_serializar(noticia, usuario))


def _aplicar_noticia(noticia, data, parcial):
    if not parcial or 'titulo' in data:
        noticia.titulo = v.texto(data, 'titulo', minimo=5, maximo=200, etiqueta='título')
    campo_contenido = 'contenido' if 'contenido' in data else 'descripcion'
    if not parcial or campo_contenido in data:
        noticia.descripcion = v.texto(data, campo_contenido, minimo=20, maximo=20000, etiqueta='contenido')
    if not parcial or 'imagen' in data:
        imagen = v.texto(data, 'imagen', requerido=False, maximo=500)
        if imagen and re.match(r'^\s*(javascript|data|vbscript):', imagen, re.I):
            raise ApiError('La ruta de la imagen no es válida.')
        noticia.imagen = imagen
    if 'fecha_publicacion' in data:
        noticia.fecha_publicacion = v.fecha_hora(data, 'fecha_publicacion', requerido=False)


def _aplicar_estado(noticia, estado):
    if estado == 'publicada' and noticia.fecha_publicacion is None:
        noticia.fecha_publicacion = ahora()
    noticia.estado = estado


@roles_requeridos('admin', 'docente')
def crear_noticia():
    """POST /api/noticias — {titulo, contenido, imagen?, estado=borrador|publicada, fecha_publicacion?}"""
    usuario = usuario_actual()
    data = v.cuerpo_json()
    noticia = Noticia(id_autor=usuario.id_usuario)
    _aplicar_noticia(noticia, data, parcial=False)
    _aplicar_estado(noticia, v.opcion(data, 'estado', ('borrador', 'publicada'), defecto='borrador'))
    db.session.add(noticia)
    db.session.flush()
    auditoria_service.registrar('crear', 'noticia', noticia.id_noticia, {'titulo': noticia.titulo,
                                                                         'estado': noticia.estado})
    db.session.commit()
    return respuesta_json(_serializar(noticia, usuario), 201)


@roles_requeridos('admin', 'docente')
def editar_noticia(id_noticia):
    usuario = usuario_actual()
    noticia = obtener_o_404(Noticia, id_noticia, 'Noticia no encontrada.')
    exigir(puede_gestionar_noticia(usuario, noticia), 'Solo puedes editar las noticias de tu autoría.')
    data = v.cuerpo_json()
    _aplicar_noticia(noticia, data, parcial=True)
    if 'estado' in data:
        _aplicar_estado(noticia, v.opcion(data, 'estado', ESTADOS_NOTICIA))
    auditoria_service.registrar('editar', 'noticia', noticia.id_noticia, {'titulo': noticia.titulo,
                                                                          'estado': noticia.estado})
    db.session.commit()
    return respuesta_json(_serializar(noticia, usuario))


@roles_requeridos('admin', 'docente')
def cambiar_estado_noticia(id_noticia):
    """PATCH /api/noticias/<id>/estado — {estado: borrador|publicada|retirada}"""
    usuario = usuario_actual()
    noticia = obtener_o_404(Noticia, id_noticia, 'Noticia no encontrada.')
    exigir(puede_gestionar_noticia(usuario, noticia), 'Solo puedes gestionar las noticias de tu autoría.')
    estado = v.opcion(v.cuerpo_json(), 'estado', ESTADOS_NOTICIA)
    anterior = noticia.estado
    _aplicar_estado(noticia, estado)
    auditoria_service.registrar('cambiar_estado', 'noticia', noticia.id_noticia, {'de': anterior, 'a': estado})
    db.session.commit()
    return respuesta_json(_serializar(noticia, usuario))


@roles_requeridos('admin', 'docente')
def eliminar_noticia(id_noticia):
    usuario = usuario_actual()
    noticia = obtener_o_404(Noticia, id_noticia, 'Noticia no encontrada.')
    exigir(puede_gestionar_noticia(usuario, noticia), 'Solo puedes eliminar las noticias de tu autoría.')
    auditoria_service.registrar('eliminar', 'noticia', noticia.id_noticia, {'titulo': noticia.titulo})
    db.session.delete(noticia)
    db.session.commit()
    return respuesta_json({'mensaje': 'Noticia eliminada correctamente.'})
