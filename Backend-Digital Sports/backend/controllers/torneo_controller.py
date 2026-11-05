# =============================================================================
# Controlador: Torneos — /api/torneos
# Consulta pública; creación/edición/eliminación solo administrador.
# =============================================================================
from flask import request

from backend.extensions import db
from backend.models.torneo import CRITERIOS_DESEMPATE, ESTADOS_TORNEO, SISTEMAS_COMPETICION, Torneo
from backend.services import auditoria_service
from backend.services.clasificacion_service import calcular_tabla
from backend.utils.auth import roles_requeridos
from backend.utils.consultas import obtener_o_404
from backend.utils.respuestas import ApiError, paginar, respuesta_json
from backend.utils import validacion as v


def _aplicar_datos(torneo, data, parcial):
    def presente(campo):
        return not parcial or campo in data

    if presente('nombre'):
        torneo.nombre = v.texto(data, 'nombre', minimo=3, maximo=100)
    if presente('categoria'):
        torneo.categoria = v.texto(data, 'categoria', maximo=50, etiqueta='categoría')
    if presente('descripcion'):
        torneo.descripcion = v.texto(data, 'descripcion', requerido=False, maximo=2000)
    if presente('fecha_inicio'):
        torneo.fecha_inicio = v.solo_fecha(data, 'fecha_inicio')
    if presente('fecha_fin'):
        torneo.fecha_fin = v.solo_fecha(data, 'fecha_fin')
    if presente('sistema_competicion'):
        torneo.sistema_competicion = v.opcion(data, 'sistema_competicion', SISTEMAS_COMPETICION, defecto='liga')
    if presente('estado'):
        torneo.estado = v.opcion(data, 'estado', ESTADOS_TORNEO, defecto='planificacion')
    for campo, defecto in (('puntos_victoria', 3), ('puntos_empate', 1), ('puntos_derrota', 0)):
        if presente(campo):
            valor = v.entero(data, campo, requerido=False, minimo=0, maximo=10)
            setattr(torneo, campo, defecto if valor is None else valor)
    if presente('criterios_desempate'):
        criterios = data.get('criterios_desempate') or ['pts', 'dg', 'gf']
        if isinstance(criterios, str):
            criterios = [c.strip() for c in criterios.split(',') if c.strip()]
        if not isinstance(criterios, list) or any(c not in CRITERIOS_DESEMPATE for c in criterios):
            raise ApiError(f'Criterios de desempate inválidos. Opciones: {", ".join(CRITERIOS_DESEMPATE)}.')
        if 'pts' not in criterios:
            criterios.insert(0, 'pts')
        torneo.criterios_desempate = ','.join(dict.fromkeys(criterios))

    if torneo.fecha_inicio and torneo.fecha_fin and torneo.fecha_fin < torneo.fecha_inicio:
        raise ApiError('La fecha de finalización no puede ser anterior a la de inicio.')
    if torneo.puntos_victoria < torneo.puntos_empate:
        raise ApiError('Los puntos por victoria no pueden ser menores que los puntos por empate.')


def _nombre_disponible(nombre, categoria, excluir_id=None):
    q = Torneo.query.filter(Torneo.nombre == nombre, Torneo.categoria == categoria)
    if excluir_id:
        q = q.filter(Torneo.id_torneo != excluir_id)
    if q.first():
        raise ApiError(f'Ya existe el torneo "{nombre}" en la categoría "{categoria}".', 409)


def listar_torneos():
    """GET /api/torneos — Filtros: ?categoria=&estado="""
    query = Torneo.query
    if request.args.get('categoria'):
        query = query.filter(Torneo.categoria == request.args['categoria'])
    if request.args.get('estado'):
        query = query.filter(Torneo.estado == request.args['estado'])
    return respuesta_json(paginar(query.order_by(Torneo.id_torneo), lambda t: t.to_dict(con_conteos=True)))


def detalle_torneo(id_torneo):
    """GET /api/torneos/<id> — Detalle con equipos participantes."""
    torneo = obtener_o_404(Torneo, id_torneo, 'Torneo no encontrado.')
    data = torneo.to_dict(con_conteos=True)
    data['equipos'] = [e.to_dict() for e in sorted(torneo.equipos, key=lambda e: e.nombre) if e.estado == 'activo']
    return respuesta_json(data)


def clasificacion_torneo(id_torneo):
    """GET /api/torneos/<id>/clasificacion — Tabla calculada desde los resultados oficiales."""
    torneo = obtener_o_404(Torneo, id_torneo, 'Torneo no encontrado.')
    return respuesta_json({'torneo': torneo.to_dict(), 'tabla': calcular_tabla(torneo)})


@roles_requeridos('admin')
def crear_torneo():
    data = v.cuerpo_json()
    torneo = Torneo()
    _aplicar_datos(torneo, data, parcial=False)
    _nombre_disponible(torneo.nombre, torneo.categoria)
    db.session.add(torneo)
    db.session.flush()
    auditoria_service.registrar('crear', 'torneo', torneo.id_torneo, {'nombre': torneo.nombre})
    db.session.commit()
    return respuesta_json(torneo.to_dict(con_conteos=True), 201)


@roles_requeridos('admin')
def editar_torneo(id_torneo):
    torneo = obtener_o_404(Torneo, id_torneo, 'Torneo no encontrado.')
    data = v.cuerpo_json()
    _aplicar_datos(torneo, data, parcial=True)
    _nombre_disponible(torneo.nombre, torneo.categoria, excluir_id=torneo.id_torneo)
    auditoria_service.registrar('editar', 'torneo', torneo.id_torneo, {k: data[k] for k in data})
    db.session.commit()
    return respuesta_json(torneo.to_dict(con_conteos=True))


@roles_requeridos('admin')
def eliminar_torneo(id_torneo):
    torneo = obtener_o_404(Torneo, id_torneo, 'Torneo no encontrado.')
    if torneo.partidos:
        raise ApiError(f'No se puede eliminar: tiene {len(torneo.partidos)} partido(s) asociado(s).', 409)
    if torneo.equipos:
        raise ApiError(f'No se puede eliminar: tiene {len(torneo.equipos)} equipo(s) asociado(s).', 409)
    auditoria_service.registrar('eliminar', 'torneo', torneo.id_torneo, {'nombre': torneo.nombre})
    db.session.delete(torneo)
    db.session.commit()
    return respuesta_json({'mensaje': 'Torneo eliminado correctamente.'})
