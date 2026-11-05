# =============================================================================
# Controlador: Tabla de posiciones — /api/posiciones (solo lectura)
# La clasificación se calcula automáticamente a partir de los resultados
# oficiales. No existen endpoints para modificar puntos manualmente.
# =============================================================================

from backend.models.torneo import Torneo
from backend.services.clasificacion_service import calcular_tabla
from backend.utils.consultas import obtener_o_404
from backend.utils.respuestas import respuesta_json
from backend.utils import validacion as v


def listar_posiciones():
    """
    GET /api/posiciones?id_torneo=<id>  -> {torneo, tabla}
    GET /api/posiciones                  -> [{torneo, tabla}, ...] de todos los torneos
    """
    id_torneo = v.arg_entero('id_torneo')
    if id_torneo:
        torneo = obtener_o_404(Torneo, id_torneo, 'Torneo no encontrado.')
        return respuesta_json({'torneo': torneo.to_dict(), 'tabla': calcular_tabla(torneo)})
    torneos = Torneo.query.order_by(Torneo.id_torneo).all()
    return respuesta_json([{'torneo': t.to_dict(), 'tabla': calcular_tabla(t)} for t in torneos])
