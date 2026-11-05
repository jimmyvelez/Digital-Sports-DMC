# =============================================================================
# Rutas: estudiante — solo asocian URL + método HTTP con el controlador.
# La lógica está en backend/controllers/estudiante_controller.py
# =============================================================================
from flask import Blueprint

from backend.controllers import estudiante_controller as controlador

estudiante_bp = Blueprint('estudiantes', __name__, url_prefix='/estudiantes')

estudiante_bp.add_url_rule('', view_func=controlador.listar_estudiantes, methods=['GET'])
estudiante_bp.add_url_rule('/<int:id_estudiante>', view_func=controlador.detalle_estudiante, methods=['GET'])
estudiante_bp.add_url_rule('', view_func=controlador.crear_estudiante, methods=['POST'])
estudiante_bp.add_url_rule('/<int:id_estudiante>', view_func=controlador.editar_estudiante, methods=['PUT'])
estudiante_bp.add_url_rule('/<int:id_estudiante>', view_func=controlador.eliminar_estudiante, methods=['DELETE'])
