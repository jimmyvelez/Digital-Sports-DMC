"""
Servicios de autenticación: control de intentos de login y recuperación de contraseña.
"""
import logging
import smtplib
import time
from email.message import EmailMessage
from threading import Lock

from flask import current_app
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from backend.extensions import db
from backend.models.usuario import Usuario

log = logging.getLogger('digital_sports')

# ---------------------------------------------------------------------------
# Límite de intentos fallidos (en memoria, por IP + correo).
# Suficiente para un único proceso; con varios procesos usar un almacén común.
# ---------------------------------------------------------------------------
_intentos = {}
_lock = Lock()


def _clave(ip, correo):
    return f'{ip}|{(correo or "").lower()}'


def login_bloqueado(ip, correo):
    cfg = current_app.config
    with _lock:
        registro = _intentos.get(_clave(ip, correo))
        if not registro:
            return 0
        fallos, desde = registro
        restante = cfg['LOGIN_BLOQUEO_MINUTOS'] * 60 - (time.time() - desde)
        if restante <= 0:
            _intentos.pop(_clave(ip, correo), None)
            return 0
        return int(restante) if fallos >= cfg['LOGIN_MAX_INTENTOS'] else 0


def registrar_fallo(ip, correo):
    with _lock:
        fallos, desde = _intentos.get(_clave(ip, correo), (0, time.time()))
        _intentos[_clave(ip, correo)] = (fallos + 1, desde)


def limpiar_fallos(ip, correo):
    with _lock:
        _intentos.pop(_clave(ip, correo), None)


# ---------------------------------------------------------------------------
# Recuperación de contraseña con token firmado de un solo uso.
# El token incluye un fragmento del hash actual: al cambiar la contraseña,
# todos los tokens anteriores dejan de ser válidos.
# ---------------------------------------------------------------------------
def _serializador():
    return URLSafeTimedSerializer(current_app.config['SECRET_KEY'], salt='recuperar-contrasena')


def generar_token_reset(usuario):
    return _serializador().dumps({'id': usuario.id_usuario, 'h': usuario.contrasena[-16:]})


def validar_token_reset(token):
    """Devuelve el usuario si el token es válido; si no, None."""
    try:
        datos = _serializador().loads(token, max_age=current_app.config['RESET_TOKEN_MINUTOS'] * 60)
    except (SignatureExpired, BadSignature):
        return None
    usuario = db.session.get(Usuario, datos.get('id'))
    if not usuario or not usuario.activo or usuario.contrasena[-16:] != datos.get('h'):
        return None
    return usuario


def enviar_correo_reset(usuario, token):
    cfg = current_app.config
    enlace = f"{cfg['FRONTEND_URL'].rstrip('/')}/pages/recuperar.html?token={token}"
    if not cfg.get('MAIL_SERVER'):
        # Modo desarrollo: sin servidor de correo configurado, el enlace se
        # muestra en la consola del backend para que el administrador lo entregue.
        log.warning('[RECUPERACION] Enlace para %s: %s', usuario.correo, enlace)
        print(f'  [RECUPERACIÓN DE CONTRASEÑA] {usuario.correo}: {enlace}')
        return False
    msg = EmailMessage()
    msg['Subject'] = 'Recupera tu contraseña — Digital Sports DMC'
    msg['From'] = cfg['MAIL_FROM']
    msg['To'] = usuario.correo
    msg.set_content(
        f'Hola {usuario.nombre},\n\nRecibimos una solicitud para restablecer tu contraseña.\n'
        f'Abre este enlace (válido por {cfg["RESET_TOKEN_MINUTOS"]} minutos):\n\n{enlace}\n\n'
        'Si no solicitaste el cambio, ignora este mensaje.\n\nDigital Sports DMC')
    try:
        with smtplib.SMTP(cfg['MAIL_SERVER'], cfg['MAIL_PORT'], timeout=10) as smtp:
            if cfg.get('MAIL_USE_TLS'):
                smtp.starttls()
            if cfg.get('MAIL_USERNAME'):
                smtp.login(cfg['MAIL_USERNAME'], cfg['MAIL_PASSWORD'])
            smtp.send_message(msg)
        return True
    except (OSError, smtplib.SMTPException):
        log.exception('No se pudo enviar el correo de recuperación a %s', usuario.correo)
        return False
