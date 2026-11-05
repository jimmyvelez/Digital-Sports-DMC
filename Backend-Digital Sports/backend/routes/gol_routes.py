# =============================================================================
# Rutas: gol — solo asocian URL + método HTTP con el controlador.
# La lógica está en backend/controllers/gol_controller.py
# =============================================================================
from flask import Blueprint

from backend.controllers import gol_controller as controlador

gol_bp = Blueprint('goles', __name__, url_prefix='/goles')

gol_bp.add_url_rule('', view_func=controlador.listar_goles, methods=['GET'])
gol_bp.add_url_rule('/goleadores', view_func=controlador.goleadores, methods=['GET'])
gol_bp.add_url_rule('', view_func=controlador.crear_gol, methods=['POST'])
gol_bp.add_url_rule('/<int:id_gol>', view_func=controlador.eliminar_gol, methods=['DELETE'])
