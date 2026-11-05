# =============================================================================
# backend/__init__.py
# Factoría de la aplicación Flask — Digital Sports DMC
# =============================================================================
import logging
import os
from urllib.parse import unquote, urlparse

import click
from flask import Flask, abort, redirect, send_from_directory
from flask_cors import CORS
from werkzeug.security import generate_password_hash

from backend.config import config
from backend.extensions import db


def _crear_base_de_datos_si_no_existe(uri):
    """
    Crea la base de datos en MySQL automáticamente si no existe.
    Solo aplica a URIs mysql://; SQLite crea el archivo por sí mismo.
    """
    if not uri.startswith('mysql'):
        return
    import pymysql
    partes = urlparse(uri)
    usuario = unquote(partes.username or 'root')
    contrasena = unquote(partes.password or '')
    host, puerto = partes.hostname or 'localhost', partes.port or 3306
    db_name = partes.path.lstrip('/').split('?')[0]
    try:
        conexion = pymysql.connect(host=host, port=puerto, user=usuario, password=contrasena)
        with conexion.cursor() as cursor:
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}` "
                           "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        conexion.close()
        print(f"  [OK] Base de datos '{db_name}' verificada/creada en MySQL.")
    except pymysql.err.OperationalError as e:
        codigo = e.args[0] if e.args else 0
        print('\n' + '=' * 60)
        print('  [ERROR DE CONEXIÓN A MYSQL]')
        if codigo == 2003 or '10061' in str(e):
            print(f'  -> MySQL no está activo o no responde en {host}:{puerto}.')
            print("  -> SOLUCIÓN: Abre el panel de XAMPP y presiona 'Start' en MySQL.")
        elif codigo == 1045:
            print(f"  -> Acceso denegado para el usuario '{usuario}'.")
            print('  -> SOLUCIÓN: Verifica DATABASE_URL en el archivo .env.')
        else:
            print(f'  -> Detalle del error: {e}')
        print('=' * 60 + '\n')


def _crear_admin(nombre, correo, contrasena):
    from backend.models import Usuario
    from backend.utils.validacion import contrasena_segura
    contrasena_segura(contrasena)
    existente = Usuario.query.filter_by(correo=correo.lower()).first()
    if existente:
        existente.rol, existente.activo = 'admin', True
        existente.contrasena = generate_password_hash(contrasena)
        db.session.commit()
        return existente, False
    admin = Usuario(nombre=nombre, correo=correo.lower(), contrasena=generate_password_hash(contrasena),
                    rol='admin', activo=True)
    db.session.add(admin)
    db.session.commit()
    return admin, True


def _inicializar_bd(app):
    from backend import models  # noqa: F401  (registra todos los modelos)
    from backend.migraciones import ejecutar_migraciones
    from backend.models import Usuario

    db.create_all()
    ejecutar_migraciones()

    if not Usuario.query.filter_by(rol='admin').first():
        if app.config.get('ADMIN_INICIAL_PASSWORD'):
            _crear_admin(app.config['ADMIN_INICIAL_NOMBRE'], app.config['ADMIN_INICIAL_CORREO'],
                         app.config['ADMIN_INICIAL_PASSWORD'])
            if not app.config.get('TESTING'):
                print(f"  [OK] Administrador inicial creado: {app.config['ADMIN_INICIAL_CORREO']}")
        elif not app.config.get('TESTING'):
            print('  [AVISO] No existe ningún administrador. Créalo con:')
            print('          flask --app run.py crear-admin')


def _registrar_frontend(app):
    """Sirve el frontend y las imágenes subidas desde el mismo origen que la API."""
    frontend = app.config['FRONTEND_DIR']

    @app.route('/')
    def inicio():
        from flask import session
        if session.get('id_usuario'):
            return redirect('/inicio.html')
        return redirect('/pages/login.html')

    @app.route('/uploads/<path:nombre>')
    def archivos_subidos(nombre):
        return send_from_directory(app.config['UPLOAD_DIR'], nombre)

    @app.route('/<path:ruta>')
    def frontend_estatico(ruta):
        if ruta.startswith('api/') or not os.path.isdir(frontend):
            abort(404)
        return send_from_directory(frontend, ruta)


def _registrar_comandos(app):
    @app.cli.command('crear-admin')
    @click.option('--nombre', prompt='Nombre del administrador', default='Administrador')
    @click.option('--correo', prompt='Correo del administrador')
    @click.password_option('--contrasena', prompt='Contraseña (mín. 8, letras y números)')
    def crear_admin(nombre, correo, contrasena):
        """Crea (o promueve) una cuenta de administrador."""
        from backend.utils.respuestas import ApiError
        try:
            usuario, nuevo = _crear_admin(nombre, correo, contrasena)
        except ApiError as e:
            raise click.ClickException(e.mensaje)
        click.echo(f"{'Creado' if nuevo else 'Actualizado'} el administrador {usuario.correo}.")

    @app.cli.command('datos-prueba')
    def datos_prueba():
        """Carga datos de prueba (torneos, equipos, partidos, noticias...) en una BD vacía."""
        from backend.datos_prueba import sembrar
        try:
            resumen = sembrar(app, log=click.echo)
        except RuntimeError as e:
            raise click.ClickException(str(e))
        click.echo('\nCuentas de prueba (NO usar en producción):')
        for fila in resumen['cuentas']:
            click.echo('  ' + ' | '.join(fila))

    @app.cli.command('migrar')
    def migrar():
        """Crea tablas nuevas y aplica las migraciones pendientes."""
        _inicializar_bd(app)
        click.echo('Migraciones aplicadas.')


def create_app(config_name=None):
    """
    Crea y configura la aplicación Flask:
      1. Carga la configuración (FLASK_CONFIG: development | production | testing).
      2. Crea la base de datos MySQL si no existe, las tablas y aplica migraciones.
      3. Registra la API REST (/api), manejo de errores, CORS y seguridad.
      4. Sirve el frontend en http://localhost:5000/.
    """
    config_name = config_name or os.getenv('FLASK_CONFIG', 'default')
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    logging.basicConfig(level=logging.INFO if app.debug else logging.WARNING)

    if config_name == 'production' and app.config['SECRET_KEY'].startswith('solo-desarrollo'):
        raise RuntimeError('Define la variable de entorno SECRET_KEY antes de ejecutar en producción.')

    CORS(app, resources={r'/api/*': {'origins': app.config['CORS_ORIGINS']}}, supports_credentials=True)

    _crear_base_de_datos_si_no_existe(app.config['SQLALCHEMY_DATABASE_URI'])
    db.init_app(app)

    from backend.utils.auth import proteger_csrf
    from backend.utils.respuestas import registrar_manejadores_error
    registrar_manejadores_error(app)
    app.before_request(proteger_csrf)

    @app.after_request
    def cabeceras_seguridad(resp):
        resp.headers.setdefault('X-Content-Type-Options', 'nosniff')
        resp.headers.setdefault('X-Frame-Options', 'SAMEORIGIN')
        resp.headers.setdefault('Referrer-Policy', 'strict-origin-when-cross-origin')
        return resp

    try:
        with app.app_context():
            _inicializar_bd(app)
            if not app.config.get('TESTING'):
                print('  [OK] Tablas y migraciones verificadas.')
    except Exception as e:  # la app arranca para mostrar el error de conexión
        if app.config.get('TESTING'):
            raise
        print(f'  [AVISO] No se pudo inicializar la base de datos: {e}')

    from backend.routes import api_bp
    app.register_blueprint(api_bp)
    _registrar_frontend(app)
    _registrar_comandos(app)
    return app
