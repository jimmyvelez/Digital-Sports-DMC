"""
Generación de notificaciones a partir de eventos reales de los partidos.
Los destinatarios son los estudiantes con cuenta activa que integran
(actualmente) alguno de los dos equipos del partido.
"""
from backend.extensions import db
from backend.models.estudiante import Estudiante, IntegranteEquipo
from backend.models.notificacion import Notificacion
from backend.models.usuario import Usuario


def destinatarios_partido(partido):
    """IDs de usuario de los estudiantes activos de ambos equipos (sin duplicados)."""
    filas = (db.session.query(Usuario.id_usuario)
             .join(Estudiante, Estudiante.id_usuario == Usuario.id_usuario)
             .join(IntegranteEquipo, IntegranteEquipo.id_estudiante == Estudiante.id_estudiante)
             .filter(IntegranteEquipo.id_equipo.in_([partido.id_equipo_local, partido.id_equipo_visitante]),
                     IntegranteEquipo.activo.is_(True),
                     Usuario.activo.is_(True))
             .distinct()
             .all())
    return [f[0] for f in filas]


def notificar_partido(partido, tipo, titulo, mensaje):
    """Crea una notificación por destinatario. No hace commit (misma transacción)."""
    ids = destinatarios_partido(partido)
    for id_usuario in ids:
        db.session.add(Notificacion(
            id_usuario=id_usuario, titulo=titulo[:150], mensaje=mensaje,
            tipo=tipo, id_partido=partido.id_partido,
        ))
    return len(ids)


def notificar_reporte_comentario(comentario, reporte, usuario_reportante):
    """
    Notifica a los administradores activos cuando un usuario reporta un comentario.
    Si ya existe una notificación no leída para este comentario, actualiza el mensaje,
    la fecha y el conteo acumulado para no saturar al administrador con notificaciones duplicadas.
    """
    from backend.models.comentario import MOTIVOS_REPORTE
    from backend.utils.tiempo import ahora

    admins = Usuario.query.filter_by(rol='admin', activo=True).all()
    if not admins:
        return 0

    autor = comentario.usuario.nombre if comentario.usuario else 'Usuario'
    noticia_titulo = comentario.noticia.titulo if comentario.noticia else 'Noticia'
    motivo_texto = MOTIVOS_REPORTE.get(reporte.motivo, reporte.motivo or 'Inapropiado')
    contenido_preview = comentario.contenido.strip()
    if len(contenido_preview) > 160:
        contenido_preview = contenido_preview[:157] + '...'

    fecha_fmt = reporte.fecha.strftime('%d/%m/%Y %H:%M')
    total_reportes = comentario.reportes or 1
    s_plural = 's' if total_reportes > 1 else ''

    titulo = f"Comentario reportado ({total_reportes} reporte{s_plural}) — Noticia: {noticia_titulo[:35]}"
    
    mensaje_partes = [
        f"Comentario: «{contenido_preview}»",
        f"Autor del comentario: {autor}",
        f"Noticia: {noticia_titulo}",
        f"Reportes acumulados: {total_reportes}",
        f"Último motivo: {motivo_texto}" + (f" ({reporte.detalles})" if reporte.detalles else ""),
        f"Reportado por: {usuario_reportante.nombre}",
        f"Fecha y hora del reporte: {fecha_fmt}"
    ]
    mensaje = "\n".join(mensaje_partes)

    for admin in admins:
        noti_existente = Notificacion.query.filter_by(
            id_usuario=admin.id_usuario,
            tipo='reporte_comentario',
            id_comentario=comentario.id_comentario,
            leida=False
        ).first()

        if noti_existente:
            noti_existente.titulo = titulo[:150]
            noti_existente.mensaje = mensaje
            noti_existente.fecha_creacion = ahora()
        else:
            db.session.add(Notificacion(
                id_usuario=admin.id_usuario,
                titulo=titulo[:150],
                mensaje=mensaje,
                tipo='reporte_comentario',
                id_comentario=comentario.id_comentario,
                leida=False,
                fecha_creacion=ahora()
            ))

    return len(admins)

