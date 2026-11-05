# =============================================================================
# Rutas: dashboard — solo asocian URL + método HTTP con el controlador.
# La lógica está en backend/controllers/dashboard_controller.py
# =============================================================================
from flask import Blueprint

from backend.controllers import dashboard_controller as controlador

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')

dashboard_bp.add_url_rule('', view_func=controlador.panel, methods=['GET'])
