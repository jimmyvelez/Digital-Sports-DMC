"""
Reglas de autorización sobre recursos concretos (centralizadas en el backend).

Reglas de asignación:
  - admin: acceso global.
  - docente:
      * Equipos: gestiona los equipos de los que es docente responsable.
      * Partidos: gestiona los partidos que creó / de los que es responsable,
        y los partidos en los que juega un equipo a su cargo.
      * Noticias: gestiona solo las noticias de su autoría.
      * Faltas: registra faltas en partidos que puede gestionar y edita las que registró.
  - estudiante: solo consulta; gestiona sus propios comentarios y notificaciones.
"""
from backend.utils.respuestas import ApiError


def _es_admin(usuario):
    return usuario is not None and usuario.rol == 'admin'


def puede_gestionar_equipo(usuario, equipo):
    if _es_admin(usuario):
        return True
    return usuario is not None and usuario.rol == 'docente' and equipo.id_docente == usuario.id_usuario


def puede_gestionar_partido(usuario, partido):
    if _es_admin(usuario):
        return True
    if usuario is None or usuario.rol != 'docente':
        return False
    if partido.id_usuario == usuario.id_usuario:
        return True
    return any(e is not None and e.id_docente == usuario.id_usuario
               for e in (partido.equipo_local, partido.equipo_visitante))


def puede_gestionar_noticia(usuario, noticia):
    if _es_admin(usuario):
        return True
    return usuario is not None and usuario.rol == 'docente' and noticia.id_autor == usuario.id_usuario


def puede_editar_falta(usuario, falta):
    if _es_admin(usuario):
        return True
    return usuario is not None and usuario.rol == 'docente' and falta.id_docente == usuario.id_usuario


def exigir(condicion, mensaje='No tienes permisos para gestionar este recurso.'):
    if not condicion:
        raise ApiError(mensaje, 403)
