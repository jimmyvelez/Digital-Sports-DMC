# =============================================================================
# Controlador: Goles (estadística de goleadores) — /api/goles
# =============================================================================
from sqlalchemy import func

from backend.extensions import db
from backend.models.equipo import Equipo
from backend.models.estudiante import Estudiante, IntegranteEquipo
from backend.models.gol import Gol
from backend.models.partido import Partido
from backend.services import auditoria_service
from backend.services.permisos import exigir, puede_gestionar_partido
from backend.utils.auth import roles_requeridos, usuario_actual
from backend.utils.consultas import obtener_o_404
from backend.utils.respuestas import ApiError, paginar, respuesta_json
from backend.utils import validacion as v


def listar_goles():
    """GET /api/goles — Filtros: ?id_partido=&id_estudiante=&id_torneo=&id_equipo="""
    query = Gol.query.join(Partido, Partido.id_partido == Gol.id_partido)
    for campo, columna in (('id_partido', Gol.id_partido), ('id_estudiante', Gol.id_estudiante),
                           ('id_torneo', Partido.id_torneo), ('id_equipo', Gol.id_equipo)):
        valor = v.arg_entero(campo)
        if valor:
            query = query.filter(columna == valor)
    return respuesta_json(paginar(query.order_by(Partido.fecha.desc(), Gol.minuto, Gol.id_gol),
                                  lambda g: g.to_dict(), por_pagina_defecto=100))


def goleadores():
    """GET /api/goles/goleadores — Ranking (?id_torneo=). Solo partidos no cancelados."""
    query = (db.session.query(Estudiante.id_estudiante, Estudiante.nombre, Equipo.nombre,
                              func.count(Gol.id_gol).label('goles'))
             .join(Gol, Gol.id_estudiante == Estudiante.id_estudiante)
             .join(Partido, Partido.id_partido == Gol.id_partido)
             .outerjoin(Equipo, Equipo.id_equipo == Gol.id_equipo)
             .filter(Partido.estado != 'cancelado'))
    id_torneo = v.arg_entero('id_torneo')
    if id_torneo:
        query = query.filter(Partido.id_torneo == id_torneo)
    filas = (query.group_by(Estudiante.id_estudiante, Estudiante.nombre, Equipo.nombre)
             .order_by(func.count(Gol.id_gol).desc(), Estudiante.nombre).limit(50).all())
    return respuesta_json([{'id_estudiante': f[0], 'estudiante': f[1], 'equipo': f[2], 'goles': f[3]}
                           for f in filas])


@roles_requeridos('admin', 'docente')
def crear_gol():
    """POST /api/goles — {id_partido, id_estudiante, minuto?}"""
    usuario = usuario_actual()
    data = v.cuerpo_json()
    partido = obtener_o_404(Partido, v.entero(data, 'id_partido', etiqueta='partido'), 'El partido indicado no existe.')
    exigir(puede_gestionar_partido(usuario, partido), 'No tienes permisos para registrar goles en este partido.')
    if partido.estado not in ('en_juego', 'finalizado'):
        raise ApiError('Solo se registran goles en partidos en juego o finalizados.', 409)
    estudiante = obtener_o_404(Estudiante, v.entero(data, 'id_estudiante', etiqueta='estudiante'),
                               'El estudiante indicado no existe.')

    membresia = IntegranteEquipo.query.filter(
        IntegranteEquipo.id_estudiante == estudiante.id_estudiante,
        IntegranteEquipo.id_equipo.in_([partido.id_equipo_local, partido.id_equipo_visitante])).first()
    if not membresia:
        raise ApiError('El estudiante no pertenece a ninguno de los equipos de este partido.')

    # Coherencia con el resultado oficial registrado
    if partido.tiene_resultado:
        maximo = partido.goles_local if membresia.id_equipo == partido.id_equipo_local else partido.goles_visitante
        actuales = Gol.query.filter_by(id_partido=partido.id_partido, id_equipo=membresia.id_equipo).count()
        if actuales >= maximo:
            raise ApiError(f'El equipo ya tiene registrados los {maximo} gol(es) de su resultado. '
                           'Corrige el resultado si falta algún gol.', 409)

    gol = Gol(id_partido=partido.id_partido, id_estudiante=estudiante.id_estudiante,
              id_equipo=membresia.id_equipo, minuto=v.entero(data, 'minuto', requerido=False, minimo=0, maximo=200))
    db.session.add(gol)
    db.session.flush()
    auditoria_service.registrar('crear', 'gol', gol.id_gol, {'partido': partido.id_partido,
                                                             'estudiante': estudiante.nombre})
    db.session.commit()
    return respuesta_json(gol.to_dict(), 201)


@roles_requeridos('admin', 'docente')
def eliminar_gol(id_gol):
    usuario = usuario_actual()
    gol = obtener_o_404(Gol, id_gol, 'Gol no encontrado.')
    exigir(puede_gestionar_partido(usuario, gol.partido), 'No tienes permisos para gestionar este partido.')
    auditoria_service.registrar('eliminar', 'gol', gol.id_gol, {'partido': gol.id_partido})
    db.session.delete(gol)
    db.session.commit()
    return respuesta_json({'mensaje': 'Gol eliminado correctamente.'})
