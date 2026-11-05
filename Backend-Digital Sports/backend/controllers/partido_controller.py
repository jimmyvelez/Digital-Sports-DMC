# =============================================================================
# Controlador: Partidos, estados y resultados — /api/partidos
# Consulta pública. Gestión: docentes (según asignación) y administradores.
# =============================================================================
from datetime import datetime, time, timedelta

from flask import request
from sqlalchemy import or_

from backend.models.equipo import Equipo
from backend.models.estudiante import IntegranteEquipo
from backend.models.partido import ESTADOS_PARTIDO, TRANSICIONES_PARTIDO, Partido
from backend.models.usuario import Usuario
from backend.services import partido_service
from backend.services.permisos import exigir, puede_gestionar_partido
from backend.utils.auth import roles_requeridos, usuario_actual
from backend.utils.consultas import obtener_o_404
from backend.utils.respuestas import ApiError, paginar, respuesta_json
from backend.utils.tiempo import ahora
from backend.utils import validacion as v


def _serializar(partido, usuario):
    data = partido.to_dict()
    gestionable = puede_gestionar_partido(usuario, partido)
    data['puede_gestionar'] = gestionable
    if gestionable:
        transiciones = sorted(TRANSICIONES_PARTIDO[partido.estado])
        if partido.estado == 'finalizado' and usuario.rol != 'admin':
            transiciones = []
        data['estados_permitidos'] = transiciones
    return data


def _ids_equipos_de(usuario):
    """Equipos 'propios': los del estudiante o los que tiene a cargo el docente."""
    if usuario.rol == 'estudiante' and usuario.perfil_estudiante:
        return [m.id_equipo for m in IntegranteEquipo.query.filter_by(
            id_estudiante=usuario.perfil_estudiante.id_estudiante, activo=True).all()]
    if usuario.rol == 'docente':
        return [e.id_equipo for e in Equipo.query.filter_by(id_docente=usuario.id_usuario).all()]
    return []


def listar_partidos():
    """
    GET /api/partidos — Calendario y resultados.
    Filtros: ?id_torneo=&id_equipo=&estado=(uno o varios separados por coma)
             &desde=AAAA-MM-DD&hasta=AAAA-MM-DD&mios=1&proximos=1&recientes=1
    """
    usuario = usuario_actual()
    query = Partido.query
    id_torneo = v.arg_entero('id_torneo')
    if id_torneo:
        query = query.filter(Partido.id_torneo == id_torneo)
    id_equipo = v.arg_entero('id_equipo')
    if id_equipo:
        query = query.filter(or_(Partido.id_equipo_local == id_equipo, Partido.id_equipo_visitante == id_equipo))
    estados = [e for e in (request.args.get('estado') or '').split(',') if e]
    if estados:
        if any(e not in ESTADOS_PARTIDO for e in estados):
            raise ApiError(f'Estado inválido. Opciones: {", ".join(ESTADOS_PARTIDO)}.')
        query = query.filter(Partido.estado.in_(estados))
    desde, hasta = v.arg_fecha('desde'), v.arg_fecha('hasta')
    if desde:
        query = query.filter(Partido.fecha >= datetime.combine(desde, time.min))
    if hasta:
        query = query.filter(Partido.fecha <= datetime.combine(hasta, time.max))

    if request.args.get('mios') == '1':
        if not usuario:
            raise ApiError('Debes iniciar sesión.', 401)
        ids = _ids_equipos_de(usuario)
        condiciones = [Partido.id_equipo_local.in_(ids), Partido.id_equipo_visitante.in_(ids)]
        if usuario.rol == 'docente':
            condiciones.append(Partido.id_usuario == usuario.id_usuario)
        query = query.filter(or_(*condiciones))

    orden = Partido.fecha.asc()
    if request.args.get('proximos') == '1':
        query = query.filter(Partido.estado.in_(('programado', 'en_juego', 'suspendido')),
                             Partido.fecha >= ahora() - timedelta(hours=3))
    elif request.args.get('recientes') == '1':
        query = query.filter(Partido.estado == 'finalizado')
        orden = Partido.fecha.desc()
    elif request.args.get('orden') == 'desc':
        orden = Partido.fecha.desc()
    return respuesta_json(paginar(query.order_by(orden, Partido.id_partido), lambda p: _serializar(p, usuario),
                                  por_pagina_defecto=100))


def detalle_partido(id_partido):
    usuario = usuario_actual()
    partido = obtener_o_404(Partido, id_partido, 'Partido no encontrado.')
    data = _serializar(partido, usuario)
    data['goles'] = [g.to_dict() for g in sorted(partido.goles, key=lambda g: (g.minuto or 0, g.id_gol))]
    return respuesta_json(data)


def _leer_programacion(data, parcial):
    datos = {}
    if not parcial or 'id_torneo' in data:
        datos['id_torneo'] = v.entero(data, 'id_torneo', etiqueta='torneo')
    for campo, etiqueta in (('id_equipo_local', 'equipo local'), ('id_equipo_visitante', 'equipo visitante')):
        if not parcial or campo in data:
            datos[campo] = v.entero(data, campo, etiqueta=etiqueta)
    if not parcial or 'fecha' in data:
        datos['fecha'] = v.fecha_hora(data, 'fecha', etiqueta='fecha y hora')
    if not parcial or 'lugar' in data:
        datos['lugar'] = v.texto(data, 'lugar', requerido=False, maximo=150)
    if 'observaciones' in data:
        datos['observaciones'] = v.texto(data, 'observaciones', requerido=False, maximo=2000)
    if data.get('id_usuario'):
        responsable = obtener_o_404(Usuario, v.entero(data, 'id_usuario'), 'Docente responsable no encontrado.')
        if responsable.rol not in ('docente', 'admin') or not responsable.activo:
            raise ApiError('El responsable del partido debe ser un docente activo.')
        datos['id_usuario'] = responsable.id_usuario
    return datos


@roles_requeridos('admin', 'docente')
def crear_partido():
    """POST /api/partidos — {id_torneo, id_equipo_local, id_equipo_visitante, fecha, lugar?, observaciones?}"""
    usuario = usuario_actual()
    data = v.cuerpo_json()
    datos = _leer_programacion(data, parcial=False)
    if usuario.rol == 'docente':
        datos.pop('id_usuario', None)  # el docente que programa queda como responsable
    partido = partido_service.crear_partido(usuario, datos)
    return respuesta_json(_serializar(partido, usuario), 201)


@roles_requeridos('admin', 'docente')
def editar_partido(id_partido):
    usuario = usuario_actual()
    partido = obtener_o_404(Partido, id_partido, 'Partido no encontrado.')
    exigir(puede_gestionar_partido(usuario, partido), 'No tienes permisos para gestionar este partido.')
    data = v.cuerpo_json()
    datos = _leer_programacion(data, parcial=True)
    if 'id_torneo' in datos and datos.pop('id_torneo') != partido.id_torneo:
        raise ApiError('No se puede cambiar el torneo de un partido. Elimínalo y prográmalo de nuevo.', 409)
    if usuario.rol == 'docente':
        datos.pop('id_usuario', None)
    # Compatibilidad: permitir estado/resultado en el mismo PUT
    partido = partido_service.actualizar_partido(usuario, partido, datos)
    if 'goles_local' in data or 'goles_visitante' in data:
        partido = partido_service.registrar_resultado(usuario, partido, data.get('goles_local'),
                                                      data.get('goles_visitante'),
                                                      finalizar=data.get('estado', 'finalizado') == 'finalizado')
    elif data.get('estado') and data['estado'] != partido.estado:
        partido = partido_service.cambiar_estado(usuario, partido, data['estado'], data.get('motivo'))
    return respuesta_json(_serializar(partido, usuario))


@roles_requeridos('admin', 'docente')
def cambiar_estado(id_partido):
    """PATCH /api/partidos/<id>/estado — {estado, motivo?}"""
    usuario = usuario_actual()
    partido = obtener_o_404(Partido, id_partido, 'Partido no encontrado.')
    exigir(puede_gestionar_partido(usuario, partido), 'No tienes permisos para gestionar este partido.')
    data = v.cuerpo_json()
    partido = partido_service.cambiar_estado(usuario, partido, v.opcion(data, 'estado', ESTADOS_PARTIDO),
                                             v.texto(data, 'motivo', requerido=False, maximo=300))
    return respuesta_json(_serializar(partido, usuario))


@roles_requeridos('admin', 'docente')
def registrar_resultado(id_partido):
    """PUT /api/partidos/<id>/resultado — {goles_local, goles_visitante, finalizar=true}"""
    usuario = usuario_actual()
    partido = obtener_o_404(Partido, id_partido, 'Partido no encontrado.')
    exigir(puede_gestionar_partido(usuario, partido), 'No tienes permisos para registrar el resultado de este partido.')
    data = v.cuerpo_json()
    finalizar = v.booleano(data, 'finalizar', defecto=True)
    partido = partido_service.registrar_resultado(usuario, partido, data.get('goles_local'),
                                                  data.get('goles_visitante'), finalizar=finalizar)
    return respuesta_json(_serializar(partido, usuario))


@roles_requeridos('admin', 'docente')
def eliminar_partido(id_partido):
    usuario = usuario_actual()
    partido = obtener_o_404(Partido, id_partido, 'Partido no encontrado.')
    exigir(puede_gestionar_partido(usuario, partido), 'No tienes permisos para gestionar este partido.')
    partido_service.eliminar_partido(usuario, partido)
    return respuesta_json({'mensaje': 'Partido eliminado correctamente.'})
