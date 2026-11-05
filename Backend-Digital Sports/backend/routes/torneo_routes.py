# =============================================================================
# Rutas: torneo — solo asocian URL + método HTTP con el controlador.
# La lógica está en backend/controllers/torneo_controller.py
# =============================================================================
from flask import Blueprint

from backend.controllers import torneo_controller as controlador

torneo_bp = Blueprint('torneos', __name__, url_prefix='/torneos')

torneo_bp.add_url_rule('', view_func=controlador.listar_torneos, methods=['GET'])
torneo_bp.add_url_rule('/<int:id_torneo>', view_func=controlador.detalle_torneo, methods=['GET'])
torneo_bp.add_url_rule('/<int:id_torneo>/clasificacion', view_func=controlador.clasificacion_torneo, methods=['GET'])
torneo_bp.add_url_rule('', view_func=controlador.crear_torneo, methods=['POST'])
torneo_bp.add_url_rule('/<int:id_torneo>', view_func=controlador.editar_torneo, methods=['PUT'])
torneo_bp.add_url_rule('/<int:id_torneo>', view_func=controlador.eliminar_torneo, methods=['DELETE'])
