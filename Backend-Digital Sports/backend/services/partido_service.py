"""
Lógica de negocio de los partidos: validación de programación, transiciones
de estado, registro de resultados, auditoría y notificaciones.
"""
from datetime import timedelta

from backend.extensions import db
from backend.models.equipo import Equipo
from backend.models.partido import ESTADOS_PARTIDO, TRANSICIONES_PARTIDO, Partido
from backend.models.torneo import Torneo
from backend.services import auditoria_service, notificacion_service
from backend.utils.respuestas import ApiError

# Duración de referencia de un partido para detectar choques de horario.
DURACION_PARTIDO = timedelta(minutes=90)
ESTADOS_ACTIVOS = ('programado', 'en_juego', 'suspendido')
MAX_GOLES = 99

NOMBRE_ESTADO = {
    'programado': 'Programado', 'en_juego': 'En juego', 'finalizado': 'Finalizado',
    'suspendido': 'Suspendido', 'cancelado': 'Cancelado',
}


def _fmt(fecha):
    return fecha.strftime('%d/%m/%Y %I:%M %p') if fecha else 'por definir'


def _nombre(partido):
    return f'{partido.equipo_local.nombre} vs {partido.equipo_visitante.nombre}'


def _validar_equipos(torneo, id_local, id_visitante):
    if id_local == id_visitante:
        raise ApiError('El equipo local y el visitante no pueden ser el mismo.')
    local = db.session.get(Equipo, id_local)
    visitante = db.session.get(Equipo, id_visitante)
    if not local or not visitante:
        raise ApiError('Alguno de los equipos indicados no existe.', 404)
    for eq in (local, visitante):
        if eq.id_torneo != torneo.id_torneo:
            raise ApiError(f'El equipo "{eq.nombre}" no pertenece al torneo "{torneo.nombre}".')
        if eq.estado != 'activo':
            raise ApiError(f'El equipo "{eq.nombre}" está inactivo.')
    return local, visitante


def _validar_programacion(torneo, id_local, id_visitante, fecha, lugar, excluir_id=None):
    """Evita duplicados y choques de horario de equipos o de cancha."""
    if torneo.fecha_inicio and fecha.date() < torneo.fecha_inicio:
        raise ApiError('La fecha del partido es anterior al inicio del torneo.')
    if torneo.fecha_fin and fecha.date() > torneo.fecha_fin:
        raise ApiError('La fecha del partido es posterior a la finalización del torneo.')

    ventana_ini, ventana_fin = fecha - DURACION_PARTIDO, fecha + DURACION_PARTIDO
    candidatos = Partido.query.filter(
        Partido.estado.in_(ESTADOS_ACTIVOS + ('finalizado',)),
        Partido.fecha > fecha - timedelta(days=1),
        Partido.fecha < fecha + timedelta(days=1),
    )
    if excluir_id:
        candidatos = candidatos.filter(Partido.id_partido != excluir_id)

    equipos = {id_local, id_visitante}
    for otro in candidatos.all():
        mismos_equipos = {otro.id_equipo_local, otro.id_equipo_visitante} == equipos
        if mismos_equipos and otro.id_torneo == torneo.id_torneo and otro.fecha.date() == fecha.date():
            raise ApiError('Ya existe un partido entre estos equipos en esa fecha (posible duplicado).', 409)
        if not (ventana_ini < otro.fecha < ventana_fin):
            continue
        if equipos & {otro.id_equipo_local, otro.id_equipo_visitante}:
            raise ApiError(f'Choque de horario: uno de los equipos ya juega "{_nombre(otro)}" '
                           f'el {_fmt(otro.fecha)}.', 409)
        if lugar and otro.lugar and otro.lugar.strip().lower() == lugar.strip().lower():
            raise ApiError(f'El lugar "{lugar}" ya está ocupado por "{_nombre(otro)}" el {_fmt(otro.fecha)}.', 409)


def crear_partido(usuario, datos):
    torneo = db.session.get(Torneo, datos['id_torneo'])
    if not torneo:
        raise ApiError('El torneo indicado no existe.', 404)
    if torneo.estado == 'finalizado':
        raise ApiError('No se pueden programar partidos en un torneo finalizado.')

    _validar_equipos(torneo, datos['id_equipo_local'], datos['id_equipo_visitante'])
    _validar_programacion(torneo, datos['id_equipo_local'], datos['id_equipo_visitante'],
                          datos['fecha'], datos.get('lugar'))

    partido = Partido(
        id_torneo=torneo.id_torneo,
        id_equipo_local=datos['id_equipo_local'],
        id_equipo_visitante=datos['id_equipo_visitante'],
        id_usuario=datos.get('id_usuario') or usuario.id_usuario,
        fecha=datos['fecha'],
        lugar=datos.get('lugar'),
        observaciones=datos.get('observaciones'),
        estado='programado',
    )
    db.session.add(partido)
    db.session.flush()

    auditoria_service.registrar('crear', 'partido', partido.id_partido, {
        'partido': _nombre(partido), 'fecha': partido.fecha, 'lugar': partido.lugar})
    notificacion_service.notificar_partido(
        partido, 'partido_nuevo', 'Nuevo partido programado',
        f'{_nombre(partido)} — {_fmt(partido.fecha)}'
        + (f' en {partido.lugar}' if partido.lugar else '') + f' ({torneo.nombre}).')
    db.session.commit()
    return partido


def actualizar_partido(usuario, partido, datos):
    """Edita programación (equipos, fecha, lugar, observaciones). Notifica cambios."""
    if not datos:
        return partido
    if partido.estado in ('finalizado', 'cancelado') and any(
            k in datos for k in ('id_equipo_local', 'id_equipo_visitante', 'fecha', 'lugar')):
        raise ApiError(f'No se puede reprogramar un partido {partido.estado}.')

    antes = {'fecha': partido.fecha, 'lugar': partido.lugar,
             'local': partido.id_equipo_local, 'visitante': partido.id_equipo_visitante}

    id_local = datos.get('id_equipo_local', partido.id_equipo_local)
    id_visitante = datos.get('id_equipo_visitante', partido.id_equipo_visitante)
    fecha = datos.get('fecha', partido.fecha)
    lugar = datos['lugar'] if 'lugar' in datos else partido.lugar

    if (id_local, id_visitante) != (partido.id_equipo_local, partido.id_equipo_visitante):
        if partido.goles or partido.tiene_resultado:
            raise ApiError('No se pueden cambiar los equipos de un partido con goles o resultado registrados.')
        _validar_equipos(partido.torneo, id_local, id_visitante)

    cambios_programacion = (fecha != antes['fecha'] or (lugar or '') != (antes['lugar'] or '')
                            or (id_local, id_visitante) != (antes['local'], antes['visitante']))
    if cambios_programacion:
        _validar_programacion(partido.torneo, id_local, id_visitante, fecha, lugar, excluir_id=partido.id_partido)

    partido.id_equipo_local, partido.id_equipo_visitante = id_local, id_visitante
    partido.fecha, partido.lugar = fecha, lugar
    if 'observaciones' in datos:
        partido.observaciones = datos['observaciones']
    if 'id_usuario' in datos and datos['id_usuario']:
        partido.id_usuario = datos['id_usuario']
    db.session.flush()

    detalle = {}
    if fecha != antes['fecha']:
        detalle['fecha'] = [antes['fecha'], fecha]
        notificacion_service.notificar_partido(
            partido, 'cambio_horario', 'Cambio de fecha u hora',
            f'{_nombre(partido)}: se movió del {_fmt(antes["fecha"])} al {_fmt(fecha)}.')
    if (lugar or '') != (antes['lugar'] or ''):
        detalle['lugar'] = [antes['lugar'], lugar]
        notificacion_service.notificar_partido(
            partido, 'cambio_lugar', 'Cambio de lugar',
            f'{_nombre(partido)} ({_fmt(partido.fecha)}) ahora se jugará en {lugar or "lugar por definir"}.')
    if (id_local, id_visitante) != (antes['local'], antes['visitante']):
        detalle['equipos'] = [[antes['local'], antes['visitante']], [id_local, id_visitante]]
        notificacion_service.notificar_partido(
            partido, 'partido_nuevo', 'Partido reprogramado',
            f'Se actualizaron los equipos del partido: {_nombre(partido)} — {_fmt(partido.fecha)}.')
    auditoria_service.registrar('editar', 'partido', partido.id_partido, detalle or {'observaciones': True})
    db.session.commit()
    return partido


def _validar_goles(valor, campo):
    if valor is None or isinstance(valor, bool):
        raise ApiError(f'El campo "{campo}" es obligatorio.')
    try:
        valor = int(valor)
    except (TypeError, ValueError):
        raise ApiError(f'El campo "{campo}" debe ser un número entero.')
    if valor < 0 or valor > MAX_GOLES:
        raise ApiError(f'El campo "{campo}" debe estar entre 0 y {MAX_GOLES}.')
    return valor


def cambiar_estado(usuario, partido, nuevo_estado, motivo=None):
    if nuevo_estado not in ESTADOS_PARTIDO:
        raise ApiError(f'Estado inválido. Opciones: {", ".join(ESTADOS_PARTIDO)}.')
    if nuevo_estado == partido.estado:
        return partido
    if nuevo_estado not in TRANSICIONES_PARTIDO[partido.estado]:
        raise ApiError(f'Transición no permitida: de "{NOMBRE_ESTADO[partido.estado]}" '
                       f'a "{NOMBRE_ESTADO[nuevo_estado]}".', 409)
    if partido.estado == 'finalizado' and usuario.rol != 'admin':
        raise ApiError('Solo un administrador puede anular un partido finalizado.', 403)
    if nuevo_estado == 'finalizado' and not partido.tiene_resultado:
        raise ApiError('Registra el resultado antes de finalizar el partido.')
    if nuevo_estado == 'en_juego' and partido.goles_local is None:
        partido.goles_local, partido.goles_visitante = 0, 0
        partido.sincronizar_marcador()

    anterior = partido.estado
    partido.estado = nuevo_estado
    auditoria_service.registrar('cambiar_estado', 'partido', partido.id_partido,
                                {'de': anterior, 'a': nuevo_estado, 'motivo': motivo})
    if nuevo_estado == 'finalizado':
        _notificar_resultado(partido, 'Resultado final')
    else:
        texto = f'{_nombre(partido)} ({_fmt(partido.fecha)}) cambió a "{NOMBRE_ESTADO[nuevo_estado]}".'
        if motivo:
            texto += f' Motivo: {motivo}'
        notificacion_service.notificar_partido(partido, 'cambio_estado', 'Cambio de estado del partido', texto)
    db.session.commit()
    return partido


def _notificar_resultado(partido, titulo):
    notificacion_service.notificar_partido(
        partido, 'resultado', titulo,
        f'{partido.equipo_local.nombre} {partido.goles_local} - {partido.goles_visitante} '
        f'{partido.equipo_visitante.nombre} ({partido.torneo.nombre}).')


def registrar_resultado(usuario, partido, goles_local, goles_visitante, finalizar=True):
    """
    Registra o corrige el resultado. Si finalizar=True el partido queda
    'finalizado' y la clasificación (calculada) se actualiza automáticamente.
    """
    goles_local = _validar_goles(goles_local, 'goles_local')
    goles_visitante = _validar_goles(goles_visitante, 'goles_visitante')

    if partido.estado in ('cancelado', 'suspendido'):
        raise ApiError(f'No se puede registrar el resultado de un partido {partido.estado}. '
                       'Reprograma el partido primero.', 409)

    from backend.models.gol import Gol
    for id_equipo, goles in ((partido.id_equipo_local, goles_local), (partido.id_equipo_visitante, goles_visitante)):
        registrados = Gol.query.filter_by(id_partido=partido.id_partido, id_equipo=id_equipo).count()
        if registrados > goles:
            raise ApiError(f'Hay {registrados} gol(es) de goleadores registrados para un equipo que marcaría '
                           f'{goles}. Elimina primero los goles sobrantes.', 409)

    anterior = (partido.goles_local, partido.goles_visitante)
    era_finalizado = partido.estado == 'finalizado'
    partido.goles_local, partido.goles_visitante = goles_local, goles_visitante
    partido.sincronizar_marcador()

    if finalizar and not era_finalizado:
        partido.estado = 'finalizado'
    elif not finalizar and partido.estado == 'programado':
        partido.estado = 'en_juego'

    auditoria_service.registrar('resultado', 'partido', partido.id_partido, {
        'antes': anterior, 'despues': (goles_local, goles_visitante), 'estado': partido.estado})

    if partido.estado == 'finalizado':
        if not era_finalizado:
            _notificar_resultado(partido, 'Resultado final')
        elif anterior != (goles_local, goles_visitante):
            _notificar_resultado(partido, 'Resultado corregido')
    db.session.commit()
    return partido


def eliminar_partido(usuario, partido):
    if partido.estado not in ('programado', 'cancelado'):
        raise ApiError('Solo se pueden eliminar partidos programados o cancelados. '
                       'Para los demás, cambia su estado a "cancelado".', 409)
    from backend.models.falta import Falta
    from backend.models.notificacion import Notificacion
    if partido.goles or Falta.query.filter_by(id_partido=partido.id_partido).count():
        raise ApiError('El partido tiene goles o faltas registradas; cancélalo en lugar de eliminarlo.', 409)

    if partido.estado == 'programado':
        notificacion_service.notificar_partido(
            partido, 'cambio_estado', 'Partido eliminado de la programación',
            f'{_nombre(partido)} del {_fmt(partido.fecha)} fue retirado del calendario.')
        db.session.flush()
    Notificacion.query.filter_by(id_partido=partido.id_partido).update({'id_partido': None})
    auditoria_service.registrar('eliminar', 'partido', partido.id_partido, {'partido': _nombre(partido)})
    db.session.delete(partido)
    db.session.commit()
