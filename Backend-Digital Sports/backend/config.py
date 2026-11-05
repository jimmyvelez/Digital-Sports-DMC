import os
from datetime import timedelta

# Carga opcional de un archivo .env (python-dotenv). Si no está instalado,
# se usan solo las variables de entorno del sistema.
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))
except ImportError:  # pragma: no cover
    pass


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROYECTO_DIR = os.path.dirname(os.path.dirname(BASE_DIR))


def _bool(nombre, defecto=False):
    valor = os.getenv(nombre)
    if valor is None:
        return defecto
    return valor.strip().lower() in ('1', 'true', 'si', 'sí', 'yes', 'on')


class Config:
    """Configuración base. Todo valor sensible se lee de variables de entorno."""

    # Clave secreta para firmar la cookie de sesión y los tokens de recuperación.
    # En producción DEBE definirse SECRET_KEY en el entorno.
    SECRET_KEY = os.getenv('SECRET_KEY', 'solo-desarrollo-cambiar-en-produccion')

    # =========================================================================
    # Base de datos — MySQL con XAMPP
    # Formato: mysql+pymysql://usuario:contraseña@host:puerto/nombre_bd
    # =========================================================================
    SQLALCHEMY_DATABASE_URI = os.getenv(
        'DATABASE_URL',
        'mysql+pymysql://root:@localhost:3306/digital_sports_dmc'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {'pool_pre_ping': True}

    # =========================================================================
    # Sesión (cookie firmada, HttpOnly)
    # =========================================================================
    SESSION_COOKIE_NAME = 'dsdmc_sesion'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SECURE = _bool('SESSION_COOKIE_SECURE', False)
    PERMANENT_SESSION_LIFETIME = timedelta(hours=int(os.getenv('SESION_HORAS', '8')))

    # Orígenes permitidos para CORS (separados por coma). Solo necesario si el
    # frontend NO se sirve desde el mismo Flask (http://localhost:5000).
    CORS_ORIGINS = [o.strip() for o in os.getenv(
        'CORS_ORIGINS', 'http://localhost:5500,http://localhost:5000,http://127.0.0.1:5500,http://127.0.0.1:5000'
    ).split(',') if o.strip()]

    # Carpeta del frontend que Flask sirve como archivos estáticos.
    FRONTEND_DIR = os.getenv('FRONTEND_DIR', os.path.join(PROYECTO_DIR, 'Frontend-Digital Sports'))

    # Subida de imágenes (noticias / escudos)
    UPLOAD_DIR = os.getenv('UPLOAD_DIR', os.path.join(os.path.dirname(BASE_DIR), 'uploads'))
    MAX_CONTENT_LENGTH = 3 * 1024 * 1024  # 3 MB por petición
    EXTENSIONES_IMAGEN = {'png', 'jpg', 'jpeg', 'webp', 'gif', 'avif'}

    # =========================================================================
    # Reglas de negocio configurables
    # =========================================================================
    # Si es False, un estudiante solo puede estar activo en UN equipo por torneo
    # (sí puede jugar en equipos de torneos distintos, p. ej. Masculino e Interroscas).
    PERMITIR_MULTIPLES_EQUIPOS_POR_TORNEO = _bool('PERMITIR_MULTIPLES_EQUIPOS_POR_TORNEO', False)

    # Recuperación de contraseña: validez del enlace (minutos)
    RESET_TOKEN_MINUTOS = int(os.getenv('RESET_TOKEN_MINUTOS', '30'))
    # URL pública del frontend usada en el enlace del correo de recuperación
    FRONTEND_URL = os.getenv('FRONTEND_URL', 'http://localhost:5000')

    # Correo (opcional). Si no se configura MAIL_SERVER, el enlace de
    # recuperación solo se escribe en la consola del servidor (modo desarrollo).
    MAIL_SERVER = os.getenv('MAIL_SERVER', '')
    MAIL_PORT = int(os.getenv('MAIL_PORT', '587'))
    MAIL_USERNAME = os.getenv('MAIL_USERNAME', '')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD', '')
    MAIL_USE_TLS = _bool('MAIL_USE_TLS', True)
    MAIL_FROM = os.getenv('MAIL_FROM', 'no-reply@digitalsportsdmc.local')

    # Protección básica contra fuerza bruta en el login
    LOGIN_MAX_INTENTOS = int(os.getenv('LOGIN_MAX_INTENTOS', '5'))
    LOGIN_BLOQUEO_MINUTOS = int(os.getenv('LOGIN_BLOQUEO_MINUTOS', '10'))

    # Autenticación con Google
    GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID', 'TU_GOOGLE_CLIENT_ID')

    # Credenciales del administrador inicial (solo se usan si no existe ningún admin)
    ADMIN_INICIAL_CORREO = os.getenv('ADMIN_CORREO', 'admin@digitalsports.com')
    ADMIN_INICIAL_NOMBRE = os.getenv('ADMIN_NOMBRE', 'admin')
    ADMIN_INICIAL_PASSWORD = os.getenv('ADMIN_PASSWORD', '')

    TESTING = False


class DevelopmentConfig(Config):
    """Configuración para desarrollo"""
    DEBUG = True


class ProductionConfig(Config):
    """Configuración para producción"""
    DEBUG = False
    SESSION_COOKIE_SECURE = _bool('SESSION_COOKIE_SECURE', True)


class TestingConfig(Config):
    """Configuración para pruebas automatizadas (SQLite en memoria)."""
    TESTING = True
    DEBUG = False
    SECRET_KEY = 'clave-de-pruebas'
    SQLALCHEMY_DATABASE_URI = 'sqlite://'
    SQLALCHEMY_ENGINE_OPTIONS = {}
    LOGIN_MAX_INTENTOS = 1000
    ADMIN_INICIAL_PASSWORD = 'Admin12345'


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
