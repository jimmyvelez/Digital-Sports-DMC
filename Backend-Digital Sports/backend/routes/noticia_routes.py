# =============================================================================
# Rutas: noticia — solo asocian URL + método HTTP con el controlador.
# La lógica está en backend/controllers/noticia_controller.py
# =============================================================================
from flask import Blueprint

from backend.controllers import noticia_controller as controlador

noticia_bp = Blueprint('noticias', __name__, url_prefix='/noticias')

noticia_bp.add_url_rule('', view_func=controlador.listar_noticias, methods=['GET'])
noticia_bp.add_url_rule('/<int:id_noticia>', view_func=controlador.detalle_noticia, methods=['GET'])
noticia_bp.add_url_rule('', view_func=controlador.crear_noticia, methods=['POST'])
noticia_bp.add_url_rule('/<int:id_noticia>', view_func=controlador.editar_noticia, methods=['PUT'])
noticia_bp.add_url_rule('/<int:id_noticia>/estado', view_func=controlador.cambiar_estado_noticia, methods=['PATCH'])
noticia_bp.add_url_rule('/<int:id_noticia>', view_func=controlador.eliminar_noticia, methods=['DELETE'])
