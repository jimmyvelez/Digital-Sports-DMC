# =============================================================================
# Rutas: posicion — solo asocian URL + método HTTP con el controlador.
# La lógica está en backend/controllers/posicion_controller.py
# =============================================================================
from flask import Blueprint

from backend.controllers import posicion_controller as controlador

posicion_bp = Blueprint('posiciones', __name__, url_prefix='/posiciones')

posicion_bp.add_url_rule('', view_func=controlador.listar_posiciones, methods=['GET'])
