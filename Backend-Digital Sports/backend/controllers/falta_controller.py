# =============================================================================
# Controlador: Faltas e incidencias — /api/faltas
# Docente: registra en partidos que puede gestionar; consulta y edita las
# que registró o las de sus partidos. Admin: acceso total.
# Las faltas NO generan sanciones automáticas ni afectan la clasificación.
# =============================================================================
from datetime import datetime, time

from flask import request
from sqlalchemy import or_

from backend.extensions import db
from backend.models.equipo import Equipo
from backend.models.estudiante import Estudiante, IntegranteEquipo
from backend.models.falta import ESTADOS_FALTA, TIPOS_FALTA, Falta
from backend.models.partido import Partido
from backend.services import auditoria_service
from backend.services.permisos import exigir, puede_editar_falta, puede_gestionar_partido
from backend.utils.auth import roles_requeridos, usuario_actual
from backend.utils.consultas import obtener_o_404
from backend.utils.respuestas import ApiError, paginar, respuesta_json
from backend.utils import validacion as v


def _serializar(falta, usuario):
    data = falta.to_dict()
    data['puede_editar'] = puede_editar_falta(usuario, falta)
    return data


def _validar_involucrados(partido, id_equipo, id_estudiante):
    if id_equipo not in (partido.id_equipo_local, partido.id_equipo_visitante):
        raise ApiError('El equipo indicado no participa en este partido.')
    if id_estudiante is not None:
        obtener_o_404(Estudiante, id_estudiante, 'El estudiante indicado no existe.')
        pertenece = IntegranteEquipo.query.filter_by(id_equipo=id_equipo, id_estudiante=id_estudiante).first()
        if not pertenece:
            raise ApiError('El estudiante no pertenece al equipo indicado.')


@roles_requeridos('admin', 'docente')
def listar_faltas():
    """GET /api/faltas — Filtros: ?id_partido=&id_equipo=&id_estudiante=&tipo=&estado=&desde=&hasta="""
    usuario = usuario_actual()
    query = Falta.query.join(Partido, Partido.id_partido == Falta.id_partido)
    if usuario.rol == 'docente':
        equipos = [e.id_equipo for e in Equipo.query.filter_by(id_docente=usuario.id_usuario).all()]
        query = query.filter(or_(Falta.id_docente == usuario.id_usuario,
                                 Partido.id_usuario == usuario.id_usuario,
                                 Partido.id_equipo_local.in_(equipos),
                                 Partido.id_equipo_visitante.in_(equipos)))
    for campo, columna in (('id_partido', Falta.id_partido), ('id_equipo', Falta.id_equipo),
                           ('id_estudiante', Falta.id_estudiante)):
        valor = v.arg_entero(campo)
        if valor:
            query = query.filter(columna == valor)
    if request.args.get('tipo'):
        query = query.filter(Falta.tipo == request.args['tipo'])
    if request.args.get('estado'):
        query = query.filter(Falta.estado == request.args['estado'])
    desde, hasta = v.arg_fecha('desde'), v.arg_fecha('hasta')
    if desde:
        query = query.filter(Falta.fecha >= datetime.combine(desde, time.min))
    if hasta:
        query = query.filter(Falta.fecha <= datetime.combine(hasta, time.max))
    return respuesta_json(paginar(query.order_by(Falta.fecha.desc(), Falta.id_falta.desc()),
                                  lambda f: _serializar(f, usuario)))


@roles_requeridos('admin', 'docente')
def detalle_falta(id_falta):
    usuario = usuario_actual()
    falta = obtener_o_404(Falta, id_falta, 'Falta no encontrada.')
    exigir(puede_editar_falta(usuario, falta) or puede_gestionar_partido(usuario, falta.partido))
    return respuesta_json(_serializar(falta, usuario))


@roles_requeridos('admin', 'docente')
def crear_falta():
    """POST /api/faltas — {id_partido, id_equipo, id_estudiante?, tipo, descripcion?, minuto?, fecha?}"""
    usuario = usuario_actual()
    data = v.cuerpo_json()
    partido = obtener_o_404(Partido, v.entero(data, 'id_partido', etiqueta='partido'), 'El partido indicado no existe.')
    exigir(puede_gestionar_partido(usuario, partido), 'Solo puedes registrar faltas en partidos a tu cargo.')
    if partido.estado in ('programado', 'cancelado'):
        raise ApiError('Solo se registran faltas en partidos en juego, suspendidos o finalizados.', 409)
    id_equipo = v.entero(data, 'id_equipo', etiqueta='equipo')
    id_estudiante = v.entero(data, 'id_estudiante', requerido=False, etiqueta='estudiante')
    _validar_involucrados(partido, id_equipo, id_estudiante)

    falta = Falta(
        id_partido=partido.id_partido, id_equipo=id_equipo, id_estudiante=id_estudiante,
        id_docente=usuario.id_usuario,
        tipo=v.opcion(data, 'tipo', TIPOS_FALTA),
        descripcion=v.texto(data, 'descripcion', requerido=False, maximo=2000, etiqueta='descripción'),
        minuto=v.entero(data, 'minuto', requerido=False, minimo=0, maximo=200),
        fecha=v.fecha_hora(data, 'fecha', requerido=False) or partido.fecha,
        estado='registrada',
    )
    db.session.add(falta)
    db.session.flush()
    auditoria_service.registrar('crear', 'falta', falta.id_falta, {'partido': partido.id_partido, 'tipo': falta.tipo})
    db.session.commit()
    return respuesta_json(_serializar(falta, usuario), 201)


@roles_requeridos('admin', 'docente')
def editar_falta(id_falta):
    usuario = usuario_actual()
    falta = obtener_o_404(Falta, id_falta, 'Falta no encontrada.')
    exigir(puede_editar_falta(usuario, falta), 'Solo puedes editar las faltas que registraste.')
    data = v.cuerpo_json()
    id_equipo = v.entero(data, 'id_equipo') if 'id_equipo' in data else falta.id_equipo
    id_estudiante = (v.entero(data, 'id_estudiante', requerido=False) if 'id_estudiante' in data
                     else falta.id_estudiante)
    _validar_involucrados(falta.partido, id_equipo, id_estudiante)
    falta.id_equipo, falta.id_estudiante = id_equipo, id_estudiante
    if 'tipo' in data:
        falta.tipo = v.opcion(data, 'tipo', TIPOS_FALTA)
    if 'descripcion' in data:
        falta.descripcion = v.texto(data, 'descripcion', requerido=False, maximo=2000)
    if 'minuto' in data:
        falta.minuto = v.entero(data, 'minuto', requerido=False, minimo=0, maximo=200)
    if 'fecha' in data:
        falta.fecha = v.fecha_hora(data, 'fecha')
    if 'estado' in data:
        falta.estado = v.opcion(data, 'estado', ESTADOS_FALTA)
    auditoria_service.registrar('editar', 'falta', falta.id_falta, data)
    db.session.commit()
    return respuesta_json(_serializar(falta, usuario))


@roles_requeridos('admin')
def eliminar_falta(id_falta):
    """Solo el admin elimina; el docente puede marcarla como 'anulada'."""
    falta = obtener_o_404(Falta, id_falta, 'Falta no encontrada.')
    auditoria_service.registrar('eliminar', 'falta', falta.id_falta, falta.to_dict())
    db.session.delete(falta)
    db.session.commit()
    return respuesta_json({'mensaje': 'Falta eliminada.'})
