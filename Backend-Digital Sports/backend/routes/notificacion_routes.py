# =============================================================================
# Rutas: notificacion — solo asocian URL + método HTTP con el controlador.
# La lógica está en backend/controllers/notificacion_controller.py
# =============================================================================
from flask import Blueprint

from backend.controllers import notificacion_controller as controlador

notificacion_bp = Blueprint('notificaciones', __name__, url_prefix='/notificaciones')

notificacion_bp.add_url_rule('', view_func=controlador.listar_notificaciones, methods=['GET'])
notificacion_bp.add_url_rule('/conteo', view_func=controlador.conteo_no_leidas, methods=['GET'])
notificacion_bp.add_url_rule('/<int:id_notificacion>/leida', view_func=controlador.marcar_leida, methods=['PATCH'])
notificacion_bp.add_url_rule('/leer-todas', view_func=controlador.marcar_todas, methods=['PATCH'])
