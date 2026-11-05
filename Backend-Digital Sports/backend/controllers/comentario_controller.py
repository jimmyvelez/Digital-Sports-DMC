# =============================================================================
# Controlador: Comentarios de noticias
#   /api/noticias/<id>/comentarios  (listar / comentar)
#   /api/comentarios/<id>           (editar, eliminar, reportar, moderar, ver reportes)
# Las URLs se declaran en backend/routes/comentario_routes.py
# =============================================================================
import re
from datetime import timedelta

from flask import request
from sqlalchemy import or_

from backend.extensions import db
from backend.models.comentario import Comentario, ReporteComentario, MOTIVOS_REPORTE
from backend.models.noticia import Noticia
from backend.models.notificacion import Notificacion
from backend.controllers.noticia_controller import _es_visible_publicamente, _puede_ver
from backend.services import auditoria_service, notificacion_service
from backend.services.permisos import exigir
from backend.utils.auth import login_requerido, roles_requeridos, usuario_actual
from backend.utils.consultas import obtener_o_404
from backend.utils.respuestas import ApiError, paginar, respuesta_json
from backend.utils.tiempo import ahora
from backend.utils import validacion as v


CONTROL_RE = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]')
COMENTARIO_MIN, COMENTARIO_MAX = 2, 1000
REPORTES_PARA_OCULTAR = 3


# -----------------------------------------------------------------------------
# Comentarios de una noticia
# -----------------------------------------------------------------------------
def _serializar_comentario(c, usuario):
    es_admin = bool(usuario and usuario.rol == 'admin')
    data = c.to_dict(con_reportes=es_admin)
    data['es_propio'] = bool(usuario and c.id_usuario == usuario.id_usuario)
    data['puede_moderar'] = es_admin
    return data


def _limpiar_contenido(data):
    contenido = CONTROL_RE.sub('', v.texto(data, 'contenido', maximo=COMENTARIO_MAX, etiqueta='comentario'))
    if len(contenido.strip()) < COMENTARIO_MIN:
        raise ApiError(f'El comentario debe tener al menos {COMENTARIO_MIN} caracteres.')
    return contenido.strip()


def listar_comentarios(id_noticia):
    usuario = usuario_actual()
    noticia = obtener_o_404(Noticia, id_noticia, 'Noticia no encontrada.')
    if not _puede_ver(usuario, noticia):
        raise ApiError('Noticia no encontrada.', 404)
    query = Comentario.query.filter_by(id_noticia=noticia.id_noticia)
    if not (usuario and usuario.rol == 'admin'):
        query = query.filter(or_(Comentario.estado == 'visible',
                                 Comentario.id_usuario == (usuario.id_usuario if usuario else -1)))
    return respuesta_json(paginar(query.order_by(Comentario.fecha_creacion.desc()),
                                  lambda c: _serializar_comentario(c, usuario), por_pagina_defecto=20))


@login_requerido
def crear_comentario(id_noticia):
    usuario = usuario_actual()
    noticia = obtener_o_404(Noticia, id_noticia, 'Noticia no encontrada.')
    if not _es_visible_publicamente(noticia):
        raise ApiError('Solo se puede comentar en noticias publicadas.', 409)
    contenido = _limpiar_contenido(v.cuerpo_json())

    ultimo = (Comentario.query.filter_by(id_usuario=usuario.id_usuario)
              .order_by(Comentario.fecha_creacion.desc()).first())
    if ultimo and ultimo.fecha_creacion > ahora() - timedelta(seconds=10):
        raise ApiError('Espera unos segundos antes de publicar otro comentario.', 429)

    comentario = Comentario(id_noticia=noticia.id_noticia, id_usuario=usuario.id_usuario, contenido=contenido)
    db.session.add(comentario)
    db.session.commit()
    return respuesta_json(_serializar_comentario(comentario, usuario), 201)


# -----------------------------------------------------------------------------
# Operaciones sobre un comentario
# -----------------------------------------------------------------------------
@roles_requeridos('admin')
def listar_para_moderacion():
    """GET /api/comentarios?reportados=1&estado= — Bandeja de moderación del admin."""
    usuario = usuario_actual()
    query = Comentario.query
    if request.args.get('reportados') == '1':
        query = query.filter(Comentario.reportes > 0)
    if request.args.get('estado'):
        query = query.filter(Comentario.estado == request.args['estado'])
    return respuesta_json(paginar(query.order_by(Comentario.reportes.desc(), Comentario.fecha_creacion.desc()),
                                  lambda c: _serializar_comentario(c, usuario)))


@roles_requeridos('admin')
def listar_reportes_comentario(id_comentario):
    """GET /api/comentarios/<id>/reportes — Historial de reportes del comentario para el admin."""
    comentario = obtener_o_404(Comentario, id_comentario, 'Comentario no encontrado.')
    reportes = [r.to_dict() for r in comentario.registros_reporte]
    return respuesta_json({
        'id_comentario': comentario.id_comentario,
        'contenido': comentario.contenido,
        'autor': comentario.usuario.nombre if comentario.usuario else 'Usuario',
        'correo_autor': comentario.usuario.correo if comentario.usuario else None,
        'noticia': comentario.noticia.titulo if comentario.noticia else None,
        'id_noticia': comentario.id_noticia,
        'estado': comentario.estado,
        'total_reportes': len(reportes),
        'reportes': reportes
    })


@login_requerido
def editar_comentario(id_comentario):
    usuario = usuario_actual()
    comentario = obtener_o_404(Comentario, id_comentario, 'Comentario no encontrado.')
    exigir(comentario.id_usuario == usuario.id_usuario, 'Solo puedes editar tus propios comentarios.')
    if comentario.estado == 'oculto':
        raise ApiError('Este comentario fue ocultado por moderación y no puede editarse.', 409)
    comentario.contenido = _limpiar_contenido(v.cuerpo_json())
    comentario.fecha_edicion = ahora()
    db.session.commit()
    return respuesta_json(_serializar_comentario(comentario, usuario))


@login_requerido
def eliminar_comentario(id_comentario):
    usuario = usuario_actual()
    comentario = obtener_o_404(Comentario, id_comentario, 'Comentario no encontrado.')
    exigir(comentario.id_usuario == usuario.id_usuario or usuario.rol == 'admin',
           'Solo puedes eliminar tus propios comentarios.')
    if comentario.id_usuario != usuario.id_usuario:
        auditoria_service.registrar('eliminar', 'comentario', comentario.id_comentario,
                                    {'autor': comentario.usuario.nombre if comentario.usuario else 'Usuario',
                                     'contenido': comentario.contenido[:200]})
    # Eliminar notificaciones asociadas
    Notificacion.query.filter_by(id_comentario=comentario.id_comentario).delete()
    db.session.delete(comentario)
    db.session.commit()
    return respuesta_json({'mensaje': 'Comentario eliminado.'})


@login_requerido
def reportar_comentario(id_comentario):
    usuario = usuario_actual()
    comentario = obtener_o_404(Comentario, id_comentario, 'Comentario no encontrado.')
    if comentario.id_usuario == usuario.id_usuario:
        raise ApiError('No puedes reportar tu propio comentario.')

    # 1. Validar que no lo haya reportado antes (evita spam por el mismo usuario)
    if ReporteComentario.query.filter_by(id_comentario=comentario.id_comentario,
                                         id_usuario=usuario.id_usuario).first():
        raise ApiError('Ya has reportado este comentario previamente.', 409)

    # 2. Control de tasa / Cooldown anti-spam
    ultimo_reporte = (ReporteComentario.query.filter_by(id_usuario=usuario.id_usuario)
                      .order_by(ReporteComentario.fecha.desc()).first())
    if ultimo_reporte and ultimo_reporte.fecha > ahora() - timedelta(seconds=5):
        raise ApiError('Por favor espera unos segundos antes de enviar otro reporte.', 429)

    reportes_recientes = ReporteComentario.query.filter(
        ReporteComentario.id_usuario == usuario.id_usuario,
        ReporteComentario.fecha > ahora() - timedelta(hours=1)
    ).count()
    if reportes_recientes >= 20:
        raise ApiError('Has alcanzado el límite de reportes permitidos temporalmente. Intenta más tarde.', 429)

    # 3. Leer y sanitizar motivo y detalles opcionales
    data = {}
    try:
        data = request.get_json(silent=True) or {}
    except Exception:
        data = {}

    motivo = data.get('motivo', 'ofensivo') if isinstance(data, dict) else 'ofensivo'
    if motivo not in MOTIVOS_REPORTE:
        motivo = 'ofensivo'

    detalles = None
    if isinstance(data, dict) and data.get('detalles'):
        detalles = str(data['detalles']).strip()[:500]

    # 4. Registrar en base de datos para conservar el historial completo
    reporte = ReporteComentario(
        id_comentario=comentario.id_comentario,
        id_usuario=usuario.id_usuario,
        motivo=motivo,
        detalles=detalles,
        fecha=ahora()
    )
    db.session.add(reporte)
    comentario.reportes = (comentario.reportes or 0) + 1

    # Ocultamiento preventivo al acumular reportes; el admin decide después.
    if comentario.reportes >= REPORTES_PARA_OCULTAR:
        comentario.estado = 'oculto'

    # 5. Notificar automáticamente a los administradores (acumulando si ya existe notificación)
    notificacion_service.notificar_reporte_comentario(comentario, reporte, usuario)

    # 6. Registrar en auditoría
    auditoria_service.registrar(
        'reportar', 'comentario', comentario.id_comentario,
        {'motivo': motivo, 'reportes_acumulados': comentario.reportes,
         'noticia': comentario.noticia.titulo if comentario.noticia else None}
    )

    db.session.commit()
    return respuesta_json({
        'mensaje': 'Gracias. El comentario fue reportado para revisión del administrador.',
        'reportes': comentario.reportes
    })


@roles_requeridos('admin')
def moderar_comentario(id_comentario):
    """PATCH /api/comentarios/<id>/moderar — {estado: visible|oculto, limpiar_reportes?}"""
    usuario = usuario_actual()
    comentario = obtener_o_404(Comentario, id_comentario, 'Comentario no encontrado.')
    data = v.cuerpo_json()
    comentario.estado = v.opcion(data, 'estado', ('visible', 'oculto'))
    if v.booleano(data, 'limpiar_reportes', defecto=comentario.estado == 'visible'):
        comentario.reportes = 0

    # Marcar como leídas las notificaciones de reporte sobre este comentario
    Notificacion.query.filter_by(
        id_comentario=comentario.id_comentario,
        tipo='reporte_comentario',
        leida=False
    ).update({'leida': True, 'fecha_lectura': ahora()}, synchronize_session=False)

    auditoria_service.registrar('moderar', 'comentario', comentario.id_comentario,
                                {'estado': comentario.estado, 'reportes_activos': comentario.reportes})
    db.session.commit()
    return respuesta_json(_serializar_comentario(comentario, usuario))

