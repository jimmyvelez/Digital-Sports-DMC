# =============================================================================
# Controlador: Equipos y plantillas — /api/equipos
# =============================================================================
from flask import request
from sqlalchemy import or_

from backend.extensions import db
from backend.models.equipo import Equipo
from backend.models.estudiante import IntegranteEquipo
from backend.models.gol import Gol
from backend.models.partido import Partido
from backend.models.torneo import Torneo
from backend.models.usuario import Usuario
from backend.services import auditoria_service, equipo_service
from backend.services.permisos import exigir, puede_gestionar_equipo
from backend.utils.auth import roles_requeridos, usuario_actual
from backend.utils.consultas import obtener_o_404
from backend.utils.respuestas import ApiError, paginar, respuesta_json
from backend.utils import validacion as v


def _serializar(equipo, usuario, con_integrantes=False):
    data = equipo.to_dict(con_integrantes=con_integrantes and usuario is not None)
    data['goles'] = Gol.query.filter_by(id_equipo=equipo.id_equipo).count()
    data['puede_gestionar'] = puede_gestionar_equipo(usuario, equipo)
    return data


def _validar_docente(id_docente):
    if id_docente is None:
        return None
    docente = db.session.get(Usuario, id_docente)
    if not docente or docente.rol != 'docente' or not docente.activo:
        raise ApiError('El docente responsable indicado no es válido.')
    return docente.id_usuario


def listar_equipos():
    """GET /api/equipos — Filtros: ?id_torneo=&categoria=&curso=&estado=&q=&mios=1"""
    usuario = usuario_actual()
    query = Equipo.query
    id_torneo = v.arg_entero('id_torneo')
    if id_torneo:
        query = query.filter(Equipo.id_torneo == id_torneo)
    for campo in ('categoria', 'curso'):
        valor = request.args.get(campo)
        if valor:
            query = query.filter(getattr(Equipo, campo).ilike(f'%{valor}%'))
    estado = request.args.get('estado', 'activo')
    if estado != 'todos':
        query = query.filter(Equipo.estado == estado)
    q = (request.args.get('q') or '').strip()
    if q:
        query = query.filter(or_(Equipo.nombre.ilike(f'%{q}%'), Equipo.curso.ilike(f'%{q}%')))
    if request.args.get('mios') == '1' and usuario:
        if usuario.rol == 'docente':
            query = query.filter(Equipo.id_docente == usuario.id_usuario)
        elif usuario.rol == 'estudiante' and usuario.perfil_estudiante:
            query = query.join(IntegranteEquipo, IntegranteEquipo.id_equipo == Equipo.id_equipo).filter(
                IntegranteEquipo.id_estudiante == usuario.perfil_estudiante.id_estudiante,
                IntegranteEquipo.activo.is_(True))
    return respuesta_json(paginar(query.order_by(Equipo.nombre), lambda e: _serializar(e, usuario)))


def detalle_equipo(id_equipo):
    """GET /api/equipos/<id> — Detalle; la plantilla solo se muestra a usuarios autenticados."""
    equipo = obtener_o_404(Equipo, id_equipo, 'Equipo no encontrado.')
    return respuesta_json(_serializar(equipo, usuario_actual(), con_integrantes=True))


@roles_requeridos('admin', 'docente')
def crear_equipo():
    usuario = usuario_actual()
    data = v.cuerpo_json()
    torneo = obtener_o_404(Torneo, v.entero(data, 'id_torneo', etiqueta='torneo'), 'El torneo indicado no existe.')
    if torneo.estado == 'finalizado':
        raise ApiError('No se pueden registrar equipos en un torneo finalizado.')
    nombre = v.texto(data, 'nombre', minimo=2, maximo=100)
    if Equipo.query.filter(Equipo.id_torneo == torneo.id_torneo, Equipo.nombre == nombre).first():
        raise ApiError(f'Ya existe un equipo llamado "{nombre}" en este torneo.', 409)

    if usuario.rol == 'admin':
        id_docente = _validar_docente(v.entero(data, 'id_docente', requerido=False))
    else:
        id_docente = usuario.id_usuario  # el docente que lo crea queda como responsable

    equipo = Equipo(
        id_torneo=torneo.id_torneo, nombre=nombre,
        curso=v.texto(data, 'curso', maximo=50),
        categoria=v.texto(data, 'categoria', requerido=False, maximo=50) or torneo.categoria,
        descripcion=v.texto(data, 'descripcion', requerido=False, maximo=1000),
        escudo=v.texto(data, 'escudo', requerido=False, maximo=500),
        estado='activo', id_docente=id_docente,
    )
    db.session.add(equipo)
    db.session.flush()
    auditoria_service.registrar('crear', 'equipo', equipo.id_equipo, {'nombre': nombre, 'torneo': torneo.nombre})

    integrantes = data.get('integrantes') or []
    if not isinstance(integrantes, list):
        raise ApiError('El campo "integrantes" debe ser una lista de estudiantes.')
    for id_est in integrantes:
        equipo_service.agregar_integrante(equipo, v.entero({'id': id_est}, 'id', etiqueta='integrante'))
    db.session.commit()
    return respuesta_json(_serializar(equipo, usuario, con_integrantes=True), 201)


@roles_requeridos('admin', 'docente')
def editar_equipo(id_equipo):
    usuario = usuario_actual()
    equipo = obtener_o_404(Equipo, id_equipo, 'Equipo no encontrado.')
    exigir(puede_gestionar_equipo(usuario, equipo), 'Solo el docente responsable o un administrador puede editar este equipo.')
    data = v.cuerpo_json()
    cambios = {}

    if 'nombre' in data:
        nombre = v.texto(data, 'nombre', minimo=2, maximo=100)
        if Equipo.query.filter(Equipo.id_torneo == equipo.id_torneo, Equipo.nombre == nombre,
                               Equipo.id_equipo != equipo.id_equipo).first():
            raise ApiError(f'Ya existe un equipo llamado "{nombre}" en este torneo.', 409)
        equipo.nombre = nombre
    for campo, maximo in (('curso', 50), ('categoria', 50), ('descripcion', 1000), ('escudo', 500)):
        if campo in data:
            valor = v.texto(data, campo, requerido=campo == 'curso', maximo=maximo)
            setattr(equipo, campo, valor if valor is not None or campo != 'categoria' else equipo.categoria)
    if 'estado' in data:
        equipo.estado = v.opcion(data, 'estado', ('activo', 'inactivo'))
    if 'id_torneo' in data and data['id_torneo'] != equipo.id_torneo:
        if Partido.query.filter(or_(Partido.id_equipo_local == equipo.id_equipo,
                                    Partido.id_equipo_visitante == equipo.id_equipo)).count():
            raise ApiError('No se puede cambiar el torneo de un equipo que ya tiene partidos.', 409)
        equipo.id_torneo = obtener_o_404(Torneo, v.entero(data, 'id_torneo'), 'El torneo indicado no existe.').id_torneo
    if 'id_docente' in data:
        if usuario.rol != 'admin':
            raise ApiError('Solo un administrador puede cambiar el docente responsable.', 403)
        cambios['id_docente'] = [equipo.id_docente, data['id_docente']]
        equipo.id_docente = _validar_docente(v.entero(data, 'id_docente', requerido=False))

    auditoria_service.registrar('editar', 'equipo', equipo.id_equipo,
                                {**{k: data[k] for k in data if k != 'id_docente'}, **cambios})
    db.session.commit()
    return respuesta_json(_serializar(equipo, usuario, con_integrantes=True))


@roles_requeridos('admin', 'docente')
def eliminar_equipo(id_equipo):
    usuario = usuario_actual()
    equipo = obtener_o_404(Equipo, id_equipo, 'Equipo no encontrado.')
    exigir(puede_gestionar_equipo(usuario, equipo))
    if equipo.partidos_local or equipo.partidos_visitante:
        raise ApiError('El equipo tiene partidos registrados. Márcalo como inactivo en lugar de eliminarlo.', 409)
    if Gol.query.filter_by(id_equipo=equipo.id_equipo).count():
        raise ApiError('El equipo tiene goles registrados. Márcalo como inactivo en lugar de eliminarlo.', 409)
    for est in equipo.estudiantes:  # columna heredada
        est.id_equipo = None
    auditoria_service.registrar('eliminar', 'equipo', equipo.id_equipo, {'nombre': equipo.nombre})
    db.session.delete(equipo)
    db.session.commit()
    return respuesta_json({'mensaje': 'Equipo eliminado correctamente.'})


# -----------------------------------------------------------------------------
# Plantilla
# -----------------------------------------------------------------------------
@roles_requeridos('admin', 'docente')
def agregar_integrante(id_equipo):
    """POST /api/equipos/<id>/integrantes — {id_estudiante, dorsal?}"""
    usuario = usuario_actual()
    equipo = obtener_o_404(Equipo, id_equipo, 'Equipo no encontrado.')
    exigir(puede_gestionar_equipo(usuario, equipo), 'Solo el docente responsable o un administrador puede gestionar la plantilla.')
    data = v.cuerpo_json()
    integrante = equipo_service.agregar_integrante(
        equipo, v.entero(data, 'id_estudiante', etiqueta='estudiante'),
        v.entero(data, 'dorsal', requerido=False, minimo=0, maximo=99))
    db.session.commit()
    return respuesta_json(integrante.to_dict(), 201)


@roles_requeridos('admin', 'docente')
def quitar_integrante(id_equipo, id_estudiante):
    usuario = usuario_actual()
    equipo = obtener_o_404(Equipo, id_equipo, 'Equipo no encontrado.')
    exigir(puede_gestionar_equipo(usuario, equipo), 'Solo el docente responsable o un administrador puede gestionar la plantilla.')
    equipo_service.quitar_integrante(equipo, id_estudiante)
    db.session.commit()
    return respuesta_json({'mensaje': 'Integrante dado de baja del equipo.'})


@roles_requeridos('admin', 'docente')
def historial_integrantes(id_equipo):
    """GET /api/equipos/<id>/historial — Altas y bajas de la plantilla."""
    equipo = obtener_o_404(Equipo, id_equipo, 'Equipo no encontrado.')
    registros = (IntegranteEquipo.query.filter_by(id_equipo=equipo.id_equipo)
                 .order_by(IntegranteEquipo.fecha_alta.desc()).all())
    return respuesta_json([r.to_dict() for r in registros])
