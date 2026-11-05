"""Reglas de conformación de plantillas (altas y bajas de integrantes)."""
from flask import current_app

from backend.extensions import db
from backend.models.equipo import Equipo
from backend.models.estudiante import Estudiante, IntegranteEquipo
from backend.services import auditoria_service
from backend.utils.respuestas import ApiError
from backend.utils.tiempo import ahora


def agregar_integrante(equipo, id_estudiante, dorsal=None):
    """
    Da de alta a un estudiante en la plantilla del equipo.
    Reglas:
      - No se permiten asignaciones duplicadas (mismo estudiante activo en el mismo equipo).
      - Si PERMITIR_MULTIPLES_EQUIPOS_POR_TORNEO es False (por defecto), el
        estudiante no puede estar activo en otro equipo del MISMO torneo.
      - El dorsal, si se indica, no puede repetirse dentro del equipo.
    """
    if equipo.estado != 'activo':
        raise ApiError('No se pueden agregar integrantes a un equipo inactivo.')
    estudiante = db.session.get(Estudiante, id_estudiante)
    if not estudiante:
        raise ApiError('El estudiante indicado no existe.', 404)
    if estudiante.usuario is not None and not estudiante.usuario.activo:
        raise ApiError('La cuenta del estudiante está desactivada.')

    activos = IntegranteEquipo.query.filter_by(id_estudiante=estudiante.id_estudiante, activo=True).all()
    if any(m.id_equipo == equipo.id_equipo for m in activos):
        raise ApiError(f'{estudiante.nombre} ya forma parte de este equipo.', 409)

    if not current_app.config.get('PERMITIR_MULTIPLES_EQUIPOS_POR_TORNEO', False):
        for m in activos:
            if m.equipo.id_torneo == equipo.id_torneo:
                raise ApiError(f'{estudiante.nombre} ya integra el equipo "{m.equipo.nombre}" '
                               f'en el mismo torneo.', 409)

    if dorsal is not None and any(i.dorsal == dorsal for i in equipo.integrantes_activos()):
        raise ApiError(f'El dorsal {dorsal} ya está asignado en este equipo.', 409)

    integrante = IntegranteEquipo(id_equipo=equipo.id_equipo, id_estudiante=estudiante.id_estudiante,
                                  dorsal=dorsal, activo=True)
    db.session.add(integrante)
    db.session.flush()
    auditoria_service.registrar('alta_integrante', 'equipo', equipo.id_equipo,
                                {'estudiante': estudiante.nombre, 'id_estudiante': estudiante.id_estudiante})
    return integrante


def quitar_integrante(equipo, id_estudiante):
    """Da de baja (no borra): conserva el historial de participación."""
    integrante = IntegranteEquipo.query.filter_by(id_equipo=equipo.id_equipo, id_estudiante=id_estudiante,
                                                  activo=True).first()
    if not integrante:
        raise ApiError('El estudiante no forma parte activa de este equipo.', 404)
    integrante.activo = False
    integrante.fecha_baja = ahora()
    auditoria_service.registrar('baja_integrante', 'equipo', equipo.id_equipo,
                                {'estudiante': integrante.estudiante.nombre, 'id_estudiante': id_estudiante})
    return integrante


def equipos_de_estudiante(estudiante):
    """Equipos activos a los que pertenece el estudiante."""
    return (Equipo.query.join(IntegranteEquipo, IntegranteEquipo.id_equipo == Equipo.id_equipo)
            .filter(IntegranteEquipo.id_estudiante == estudiante.id_estudiante,
                    IntegranteEquipo.activo.is_(True))
            .all())
