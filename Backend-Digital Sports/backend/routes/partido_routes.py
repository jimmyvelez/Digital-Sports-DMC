# =============================================================================
# Rutas: partido — solo asocian URL + método HTTP con el controlador.
# La lógica está en backend/controllers/partido_controller.py
# =============================================================================
from flask import Blueprint

from backend.controllers import partido_controller as controlador

partido_bp = Blueprint('partidos', __name__, url_prefix='/partidos')

partido_bp.add_url_rule('', view_func=controlador.listar_partidos, methods=['GET'])
partido_bp.add_url_rule('/<int:id_partido>', view_func=controlador.detalle_partido, methods=['GET'])
partido_bp.add_url_rule('', view_func=controlador.crear_partido, methods=['POST'])
partido_bp.add_url_rule('/<int:id_partido>', view_func=controlador.editar_partido, methods=['PUT'])
partido_bp.add_url_rule('/<int:id_partido>/estado', view_func=controlador.cambiar_estado, methods=['PATCH'])
partido_bp.add_url_rule('/<int:id_partido>/resultado', view_func=controlador.registrar_resultado, methods=['PUT'])
partido_bp.add_url_rule('/<int:id_partido>', view_func=controlador.eliminar_partido, methods=['DELETE'])
