# =============================================================================
# backend/routes/__init__.py
# Blueprint raíz de la API REST — agrupa las rutas de cada recurso bajo /api.
#
# Arquitectura MVC del backend:
#   models/       (M) Modelos SQLAlchemy: tablas y relaciones.
#   controllers/  (C) Funciones que atienden cada petición: permisos,
#                     validación, uso de modelos/servicios y respuesta JSON.
#   routes/           Mapa URL + método HTTP -> función del controlador.
#   services/         Reglas de negocio compartidas (clasificación, partidos,
#                     notificaciones, permisos, auditoría).
#   (V) La vista es la respuesta JSON que consume el frontend.
# =============================================================================
from flask import Blueprint

from backend.routes.auditoria_routes import auditoria_bp
from backend.routes.comentario_routes import comentario_bp
from backend.routes.dashboard_routes import dashboard_bp
from backend.routes.equipo_routes import equipo_bp
from backend.routes.estudiante_routes import estudiante_bp
from backend.routes.falta_routes import falta_bp
from backend.routes.gol_routes import gol_bp
from backend.routes.noticia_routes import noticia_bp
from backend.routes.notificacion_routes import notificacion_bp
from backend.routes.partido_routes import partido_bp
from backend.routes.posicion_routes import posicion_bp
from backend.routes.torneo_routes import torneo_bp
from backend.routes.upload_routes import upload_bp
from backend.routes.usuario_routes import usuario_bp
from backend.utils.respuestas import respuesta_json

api_bp = Blueprint('api', __name__, url_prefix='/api')

for _bp in (usuario_bp, torneo_bp, equipo_bp, estudiante_bp, partido_bp, gol_bp, posicion_bp,
            noticia_bp, comentario_bp, notificacion_bp, falta_bp, dashboard_bp, auditoria_bp, upload_bp):
    api_bp.register_blueprint(_bp)


def salud():
    """GET /api/salud — Comprobación rápida de que el backend responde."""
    return respuesta_json({'estado': 'ok'})


api_bp.add_url_rule('/salud', view_func=salud, methods=['GET'])
