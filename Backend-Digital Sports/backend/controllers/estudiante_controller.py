# =============================================================================
# Controlador: Estudiantes (perfiles deportivos) — /api/estudiantes
# Consulta y gestión: docentes y administradores. Cada estudiante puede ver
# su propio perfil deportivo.
# =============================================================================
from flask import request
from sqlalchemy import or_

from backend.extensions import db
from backend.models.equipo import Equipo
from backend.models.estudiante import Estudiante, IntegranteEquipo
from backend.models.falta import Falta
from backend.models.gol import Gol
from backend.services import auditoria_service
from backend.utils.auth import login_requerido, roles_requeridos, usuario_actual
from backend.utils.consultas import obtener_o_404
from backend.utils.respuestas import ApiError, paginar, respuesta_json
from backend.utils import validacion as v


@roles_requeridos('admin', 'docente')
def listar_estudiantes():
    """GET /api/estudiantes — Filtros: ?q=&curso=&id_equipo=&disponibles_torneo=<id_torneo>"""
    query = Estudiante.query
    q = (request.args.get('q') or '').strip()
    if q:
        query = query.filter(or_(Estudiante.nombre.ilike(f'%{q}%'), Estudiante.curso.ilike(f'%{q}%')))
    if request.args.get('curso'):
        query = query.filter(Estudiante.curso.ilike(f"%{request.args['curso']}%"))
    id_equipo = v.arg_entero('id_equipo')
    if id_equipo:
        query = query.join(IntegranteEquipo, IntegranteEquipo.id_estudiante == Estudiante.id_estudiante).filter(
            IntegranteEquipo.id_equipo == id_equipo, IntegranteEquipo.activo.is_(True))
    disponibles = v.arg_entero('disponibles_torneo')
    if disponibles:
        ocupados = (db.session.query(IntegranteEquipo.id_estudiante)
                    .join(Equipo, Equipo.id_equipo == IntegranteEquipo.id_equipo)
                    .filter(Equipo.id_torneo == disponibles, IntegranteEquipo.activo.is_(True)))
        query = query.filter(Estudiante.id_estudiante.notin_(ocupados))
    return respuesta_json(paginar(query.order_by(Estudiante.nombre), lambda e: e.to_dict(con_equipos=True),
                                  por_pagina_defecto=100))


@login_requerido
def detalle_estudiante(id_estudiante):
    usuario = usuario_actual()
    estudiante = obtener_o_404(Estudiante, id_estudiante, 'Estudiante no encontrado.')
    if usuario.rol == 'estudiante' and estudiante.id_usuario != usuario.id_usuario:
        raise ApiError('Solo puedes consultar tu propio perfil deportivo.', 403)
    data = estudiante.to_dict(con_equipos=True)
    data['goles'] = Gol.query.filter_by(id_estudiante=estudiante.id_estudiante).count()
    data['historial'] = [m.to_dict() | {'equipo': m.equipo.nombre, 'torneo': m.equipo.torneo.nombre}
                         for m in sorted(estudiante.membresias, key=lambda m: m.fecha_alta, reverse=True)]
    return respuesta_json(data)


@roles_requeridos('admin', 'docente')
def crear_estudiante():
    """POST /api/estudiantes — Perfil de jugador sin cuenta (p. ej. aún no se registra)."""
    data = v.cuerpo_json()
    estudiante = Estudiante(nombre=v.texto(data, 'nombre', minimo=3, maximo=100),
                            curso=v.texto(data, 'curso', requerido=False, maximo=50))
    db.session.add(estudiante)
    db.session.flush()
    auditoria_service.registrar('crear', 'estudiante', estudiante.id_estudiante, {'nombre': estudiante.nombre})
    db.session.commit()
    return respuesta_json(estudiante.to_dict(con_equipos=True), 201)


@roles_requeridos('admin', 'docente')
def editar_estudiante(id_estudiante):
    estudiante = obtener_o_404(Estudiante, id_estudiante, 'Estudiante no encontrado.')
    data = v.cuerpo_json()
    if 'nombre' in data:
        if estudiante.id_usuario:
            raise ApiError('El nombre de un estudiante con cuenta lo actualiza el propio estudiante o el administrador.', 409)
        estudiante.nombre = v.texto(data, 'nombre', minimo=3, maximo=100)
    if 'curso' in data:
        estudiante.curso = v.texto(data, 'curso', requerido=False, maximo=50)
    auditoria_service.registrar('editar', 'estudiante', estudiante.id_estudiante, data)
    db.session.commit()
    return respuesta_json(estudiante.to_dict(con_equipos=True))


@roles_requeridos('admin')
def eliminar_estudiante(id_estudiante):
    estudiante = obtener_o_404(Estudiante, id_estudiante, 'Estudiante no encontrado.')
    if estudiante.id_usuario:
        raise ApiError('El perfil está vinculado a una cuenta. Desactiva la cuenta en su lugar.', 409)
    if estudiante.membresias or estudiante.goles or Falta.query.filter_by(id_estudiante=id_estudiante).count():
        raise ApiError('El estudiante tiene historial deportivo (equipos, goles o faltas) y no puede eliminarse.', 409)
    auditoria_service.registrar('eliminar', 'estudiante', estudiante.id_estudiante, {'nombre': estudiante.nombre})
    db.session.delete(estudiante)
    db.session.commit()
    return respuesta_json({'mensaje': 'Estudiante eliminado correctamente.'})
