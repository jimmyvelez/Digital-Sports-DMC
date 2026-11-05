# =============================================================================
# Rutas: equipo — solo asocian URL + método HTTP con el controlador.
# La lógica está en backend/controllers/equipo_controller.py
# =============================================================================
from flask import Blueprint

from backend.controllers import equipo_controller as controlador

equipo_bp = Blueprint('equipos', __name__, url_prefix='/equipos')

equipo_bp.add_url_rule('', view_func=controlador.listar_equipos, methods=['GET'])
equipo_bp.add_url_rule('/<int:id_equipo>', view_func=controlador.detalle_equipo, methods=['GET'])
equipo_bp.add_url_rule('', view_func=controlador.crear_equipo, methods=['POST'])
equipo_bp.add_url_rule('/<int:id_equipo>', view_func=controlador.editar_equipo, methods=['PUT'])
equipo_bp.add_url_rule('/<int:id_equipo>', view_func=controlador.eliminar_equipo, methods=['DELETE'])
equipo_bp.add_url_rule('/<int:id_equipo>/integrantes', view_func=controlador.agregar_integrante, methods=['POST'])
equipo_bp.add_url_rule('/<int:id_equipo>/integrantes/<int:id_estudiante>', view_func=controlador.quitar_integrante, methods=['DELETE'])
equipo_bp.add_url_rule('/<int:id_equipo>/historial', view_func=controlador.historial_integrantes, methods=['GET'])
