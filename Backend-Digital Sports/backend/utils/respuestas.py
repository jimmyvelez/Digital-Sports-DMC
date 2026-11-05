"""
Respuestas JSON consistentes y manejo centralizado de errores de la API.

Formato de éxito:  el recurso (objeto) o {"items": [...], "total", "pagina", "por_pagina", "paginas"}
Formato de error:  {"error": "mensaje legible", "detalles": {...opcional}}
"""
import json
import logging

from flask import make_response, request
from werkzeug.exceptions import HTTPException

log = logging.getLogger('digital_sports')


class ApiError(Exception):
    """Error de negocio o de validación que se devuelve al cliente tal cual."""

    def __init__(self, mensaje, status=400, detalles=None):
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.status = status
        self.detalles = detalles


def respuesta_json(data, status_code=200):
    """Crea una respuesta HTTP con cuerpo JSON (UTF-8, sin escapar tildes)."""
    resp = make_response(json.dumps(data, ensure_ascii=False, default=str), status_code)
    resp.headers['Content-Type'] = 'application/json; charset=utf-8'
    return resp


def paginar(query, serializar, por_pagina_defecto=50, por_pagina_max=500):
    """Aplica ?pagina=&por_pagina= a una query y devuelve el sobre estándar."""
    try:
        pagina = max(int(request.args.get('pagina', 1)), 1)
        por_pagina = int(request.args.get('por_pagina', por_pagina_defecto))
    except (TypeError, ValueError):
        raise ApiError('Los parámetros pagina y por_pagina deben ser números enteros.')
    por_pagina = min(max(por_pagina, 1), por_pagina_max)
    total = query.order_by(None).count()
    items = query.limit(por_pagina).offset((pagina - 1) * por_pagina).all()
    return {
        'items': [serializar(i) for i in items],
        'total': total,
        'pagina': pagina,
        'por_pagina': por_pagina,
        'paginas': (total + por_pagina - 1) // por_pagina if total else 0,
    }


def registrar_manejadores_error(app):
    """Todas las rutas /api/* responden errores en JSON y sin filtrar detalles internos."""
    from backend.extensions import db

    @app.errorhandler(ApiError)
    def _api_error(err):
        db.session.rollback()
        cuerpo = {'error': err.mensaje}
        if err.detalles:
            cuerpo['detalles'] = err.detalles
        return respuesta_json(cuerpo, err.status)

    @app.errorhandler(HTTPException)
    def _http_error(err):
        if not request.path.startswith('/api'):
            return err
        mensajes = {
            400: 'Solicitud inválida.',
            401: 'Debes iniciar sesión.',
            403: 'No tienes permisos para realizar esta acción.',
            404: 'Recurso no encontrado.',
            405: 'Método no permitido para este recurso.',
            413: 'El archivo supera el tamaño máximo permitido (3 MB).',
            415: 'Tipo de contenido no soportado. Envía JSON.',
        }
        return respuesta_json({'error': mensajes.get(err.code, err.description)}, err.code)

    @app.errorhandler(Exception)
    def _error_interno(err):
        db.session.rollback()
        log.exception('Error no controlado en %s %s', request.method, request.path)
        if app.config.get('TESTING'):
            raise err
        return respuesta_json({'error': 'Ocurrió un error interno. Inténtalo de nuevo más tarde.'}, 500)
