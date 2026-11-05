"""
Autenticación por sesión (cookie firmada HttpOnly) y autorización por rol.

- La sesión solo guarda id_usuario; el usuario y su rol se leen de la BD en
  cada petición, así un cambio de rol o una desactivación aplica de inmediato.
- Toda operación protegida se valida aquí, en el backend.
"""
from functools import wraps

from flask import request, session

from backend.extensions import db
from backend.utils.respuestas import ApiError

METODOS_MUTANTES = ('POST', 'PUT', 'PATCH', 'DELETE')


def usuario_actual():
    """Usuario autenticado y activo de la petición en curso, o None."""
    # La caché se guarda en la propia petición (no en flask.g, que puede ser
    # compartido por varias peticiones dentro de un mismo contexto de aplicación).
    if hasattr(request, '_usuario_actual'):
        return request._usuario_actual
    from backend.models.usuario import Usuario
    usuario = None
    id_usuario = session.get('id_usuario')
    if id_usuario is not None:
        usuario = db.session.get(Usuario, id_usuario)
        if usuario is None or not usuario.activo:
            session.clear()
            usuario = None
    request._usuario_actual = usuario
    return usuario


def login_requerido(f):
    """Exige una sesión activa."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        if usuario_actual() is None:
            raise ApiError('Debes iniciar sesión.', 401)
        return f(*args, **kwargs)
    return wrapper


def roles_requeridos(*roles):
    """Exige sesión activa y uno de los roles indicados."""
    def decorador(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            usuario = usuario_actual()
            if usuario is None:
                raise ApiError('Debes iniciar sesión.', 401)
            if usuario.rol not in roles:
                raise ApiError('No tienes permisos para realizar esta acción.', 403)
            return f(*args, **kwargs)
        return wrapper
    return decorador


def es_admin(usuario=None):
    usuario = usuario or usuario_actual()
    return bool(usuario and usuario.rol == 'admin')


def proteger_csrf():
    """
    Protección CSRF para la API: las peticiones que modifican datos deben
    incluir la cabecera X-Requested-With. Un formulario de otro sitio no puede
    enviarla sin una petición CORS previa, que el servidor rechaza para
    orígenes no permitidos.
    """
    if request.method in METODOS_MUTANTES and request.path.startswith('/api'):
        if not request.headers.get('X-Requested-With'):
            raise ApiError('Solicitud rechazada: falta la cabecera X-Requested-With.', 403)
