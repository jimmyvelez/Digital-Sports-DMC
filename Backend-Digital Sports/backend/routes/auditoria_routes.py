# =============================================================================
# Rutas: auditoria — solo asocian URL + método HTTP con el controlador.
# La lógica está en backend/controllers/auditoria_controller.py
# =============================================================================
from flask import Blueprint

from backend.controllers import auditoria_controller as controlador

auditoria_bp = Blueprint('auditoria', __name__, url_prefix='/auditoria')

auditoria_bp.add_url_rule('', view_func=controlador.listar_auditoria, methods=['GET'])
