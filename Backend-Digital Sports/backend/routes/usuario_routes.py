# =============================================================================
# Rutas: usuario — solo asocian URL + método HTTP con el controlador.
# La lógica está en backend/controllers/usuario_controller.py
# =============================================================================
from flask import Blueprint

from backend.controllers import usuario_controller as controlador

usuario_bp = Blueprint('usuarios', __name__, url_prefix='/usuarios')

usuario_bp.add_url_rule('/registro', view_func=controlador.registrar_usuario, methods=['POST'])
usuario_bp.add_url_rule('/login', view_func=controlador.login_usuario, methods=['POST'])
usuario_bp.add_url_rule('/google-login', view_func=controlador.google_login, methods=['POST'])
usuario_bp.add_url_rule('/auth-config', view_func=controlador.configuracion_auth, methods=['GET'])
usuario_bp.add_url_rule('/logout', view_func=controlador.logout_usuario, methods=['POST'])
usuario_bp.add_url_rule('/sesion', view_func=controlador.sesion_actual, methods=['GET'])
usuario_bp.add_url_rule('/recuperar', view_func=controlador.solicitar_recuperacion, methods=['POST'])
usuario_bp.add_url_rule('/restablecer', view_func=controlador.restablecer_contrasena, methods=['POST'])
usuario_bp.add_url_rule('/perfil', view_func=controlador.ver_perfil, methods=['GET'])
usuario_bp.add_url_rule('/perfil', view_func=controlador.actualizar_perfil, methods=['PUT'])
usuario_bp.add_url_rule('', view_func=controlador.listar_usuarios, methods=['GET'])
usuario_bp.add_url_rule('/docentes', view_func=controlador.listar_docentes, methods=['GET'])
usuario_bp.add_url_rule('', view_func=controlador.crear_usuario, methods=['POST'])
usuario_bp.add_url_rule('/<int:id_usuario>', view_func=controlador.detalle_usuario, methods=['GET'])
usuario_bp.add_url_rule('/<int:id_usuario>', view_func=controlador.editar_usuario, methods=['PUT'])
