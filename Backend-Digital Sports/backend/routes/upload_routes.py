# =============================================================================
# Rutas: upload — solo asocian URL + método HTTP con el controlador.
# La lógica está en backend/controllers/upload_controller.py
# =============================================================================
from flask import Blueprint

from backend.controllers import upload_controller as controlador

upload_bp = Blueprint('uploads', __name__, url_prefix='/uploads')

upload_bp.add_url_rule('', view_func=controlador.subir_imagen, methods=['POST'])
