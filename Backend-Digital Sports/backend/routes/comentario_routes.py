# =============================================================================
# Rutas: comentario — solo asocian URL + método HTTP con el controlador.
# La lógica está en backend/controllers/comentario_controller.py
# =============================================================================
from flask import Blueprint

from backend.controllers import comentario_controller as controlador
from backend.routes.noticia_routes import noticia_bp

comentario_bp = Blueprint('comentarios', __name__, url_prefix='/comentarios')

noticia_bp.add_url_rule('/<int:id_noticia>/comentarios', view_func=controlador.listar_comentarios, methods=['GET'])
noticia_bp.add_url_rule('/<int:id_noticia>/comentarios', view_func=controlador.crear_comentario, methods=['POST'])
comentario_bp.add_url_rule('', view_func=controlador.listar_para_moderacion, methods=['GET'])
comentario_bp.add_url_rule('/<int:id_comentario>', view_func=controlador.editar_comentario, methods=['PUT'])
comentario_bp.add_url_rule('/<int:id_comentario>', view_func=controlador.eliminar_comentario, methods=['DELETE'])
comentario_bp.add_url_rule('/<int:id_comentario>/reportar', view_func=controlador.reportar_comentario, methods=['POST'])
comentario_bp.add_url_rule('/<int:id_comentario>/reportes', view_func=controlador.listar_reportes_comentario, methods=['GET'])
comentario_bp.add_url_rule('/<int:id_comentario>/moderar', view_func=controlador.moderar_comentario, methods=['PATCH'])

