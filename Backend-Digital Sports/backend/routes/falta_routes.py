# =============================================================================
# Rutas: falta — solo asocian URL + método HTTP con el controlador.
# La lógica está en backend/controllers/falta_controller.py
# =============================================================================
from flask import Blueprint

from backend.controllers import falta_controller as controlador

falta_bp = Blueprint('faltas', __name__, url_prefix='/faltas')

falta_bp.add_url_rule('', view_func=controlador.listar_faltas, methods=['GET'])
falta_bp.add_url_rule('/<int:id_falta>', view_func=controlador.detalle_falta, methods=['GET'])
falta_bp.add_url_rule('', view_func=controlador.crear_falta, methods=['POST'])
falta_bp.add_url_rule('/<int:id_falta>', view_func=controlador.editar_falta, methods=['PUT'])
falta_bp.add_url_rule('/<int:id_falta>', view_func=controlador.eliminar_falta, methods=['DELETE'])
