# =============================================================================
# Controlador: Paneles de control por rol — /api/dashboard
# Todos los datos se calculan en el momento desde la base de datos.
# =============================================================================
from datetime import timedelta

from sqlalchemy import or_

from backend.models.auditoria import Auditoria
from backend.models.comentario import Comentario
from backend.models.equipo import Equipo
from backend.models.falta import Falta
from backend.models.noticia import Noticia
from backend.models.notificacion import Notificacion
from backend.models.partido import Partido
from backend.models.torneo import Torneo
from backend.models.usuario import Usuario
from backend.services.clasificacion_service import posicion_de_equipo
from backend.services.equipo_service import equipos_de_estudiante
from backend.utils.auth import login_requerido, usuario_actual
from backend.utils.respuestas import respuesta_json
from backend.utils.tiempo import ahora


ACTIVOS = ('programado', 'en_juego', 'suspendido')


def _proximos(query, limite=5):
    return [p.to_dict() for p in query.filter(Partido.estado.in_(ACTIVOS),
                                              Partido.fecha >= ahora() - timedelta(hours=3))
            .order_by(Partido.fecha.asc()).limit(limite).all()]


def _recientes(query, limite=5):
    return [p.to_dict() for p in query.filter(Partido.estado == 'finalizado')
            .order_by(Partido.fecha.desc()).limit(limite).all()]


def _noticias_recientes(limite=4):
    return [n.to_dict(resumen=True) for n in Noticia.query.filter(
        Noticia.estado == 'publicada', Noticia.fecha_publicacion <= ahora())
        .order_by(Noticia.fecha_publicacion.desc()).limit(limite).all()]


def _panel_admin():
    usuarios = Usuario.query
    return {
        'totales': {
            'usuarios': usuarios.count(),
            'docentes': usuarios.filter(Usuario.rol == 'docente').count(),
            'estudiantes': Usuario.query.filter(Usuario.rol == 'estudiante').count(),
            'equipos': Equipo.query.filter(Equipo.estado == 'activo').count(),
            'torneos': Torneo.query.count(),
            'partidos_programados': Partido.query.filter(Partido.estado.in_(ACTIVOS)).count(),
            'partidos_finalizados': Partido.query.filter(Partido.estado == 'finalizado').count(),
            'noticias_publicadas': Noticia.query.filter(Noticia.estado == 'publicada').count(),
            'faltas': Falta.query.count(),
            'comentarios_reportados': Comentario.query.filter(Comentario.reportes > 0).count(),
            'usuarios_inactivos': Usuario.query.filter(Usuario.activo.is_(False)).count(),
        },
        'proximos_partidos': _proximos(Partido.query),
        'resultados_recientes': _recientes(Partido.query),
        'noticias_recientes': _noticias_recientes(),
        'actividad_reciente': [a.to_dict() for a in Auditoria.query.order_by(Auditoria.fecha.desc()).limit(8).all()],
    }


def _panel_docente(usuario):
    equipos = Equipo.query.filter(Equipo.id_docente == usuario.id_usuario).order_by(Equipo.nombre).all()
    ids = [e.id_equipo for e in equipos]
    mis_partidos = Partido.query.filter(or_(Partido.id_usuario == usuario.id_usuario,
                                            Partido.id_equipo_local.in_(ids),
                                            Partido.id_equipo_visitante.in_(ids)))
    return {
        'equipos': [e.to_dict() for e in equipos],
        'totales': {
            'equipos': len(equipos),
            'partidos_por_jugar': mis_partidos.filter(Partido.estado.in_(ACTIVOS)).count(),
            'partidos_finalizados': mis_partidos.filter(Partido.estado == 'finalizado').count(),
            'noticias': Noticia.query.filter(Noticia.id_autor == usuario.id_usuario).count(),
            'faltas_registradas': Falta.query.filter(Falta.id_docente == usuario.id_usuario).count(),
        },
        'proximos_partidos': _proximos(mis_partidos),
        'resultados_recientes': _recientes(mis_partidos),
        'noticias_recientes': _noticias_recientes(),
    }


def _panel_estudiante(usuario):
    perfil = usuario.perfil_estudiante
    equipos = equipos_de_estudiante(perfil) if perfil else []
    ids = [e.id_equipo for e in equipos]
    partidos = Partido.query.filter(or_(Partido.id_equipo_local.in_(ids), Partido.id_equipo_visitante.in_(ids)))
    mis_equipos = []
    for e in equipos:
        data = e.to_dict(con_integrantes=True)
        data['clasificacion'] = posicion_de_equipo(e)
        mis_equipos.append(data)
    proximos = _proximos(partidos, limite=5)
    return {
        'equipos': mis_equipos,
        'proximo_partido': proximos[0] if proximos else None,
        'proximos_partidos': proximos,
        'resultados_recientes': _recientes(partidos),
        'noticias_recientes': _noticias_recientes(),
        'notificaciones_pendientes': Notificacion.query.filter(
            Notificacion.id_usuario == usuario.id_usuario, Notificacion.leida.is_(False)).count(),
    }


@login_requerido
def panel():
    usuario = usuario_actual()
    if usuario.rol == 'admin':
        datos = _panel_admin()
    elif usuario.rol == 'docente':
        datos = _panel_docente(usuario)
    else:
        datos = _panel_estudiante(usuario)
    datos['rol'] = usuario.rol
    datos['usuario'] = usuario.nombre
    return respuesta_json(datos)
