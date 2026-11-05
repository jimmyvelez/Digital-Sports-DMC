from unittest.mock import patch
from google.auth.exceptions import GoogleAuthError
from backend.models import Usuario, Estudiante


def test_auth_config_devuelve_none_si_no_esta_configurado(cliente, app):
    app.config['GOOGLE_CLIENT_ID'] = 'TU_GOOGLE_CLIENT_ID'
    r = cliente.get('/api/usuarios/auth-config')
    assert r.status_code == 200
    assert r.json['google_client_id'] is None


def test_auth_config_devuelve_client_id_configurado(cliente, app):
    app.config['GOOGLE_CLIENT_ID'] = '123456789-test.apps.googleusercontent.com'
    r = cliente.get('/api/usuarios/auth-config')
    assert r.status_code == 200
    assert r.json['google_client_id'] == '123456789-test.apps.googleusercontent.com'


def test_google_login_sin_credencial_responde_400(cliente, app):
    app.config['GOOGLE_CLIENT_ID'] = '123456789-test.apps.googleusercontent.com'
    r = cliente.post('/api/usuarios/google-login', json={})
    assert r.status_code == 400
    assert 'No se recibió credencial' in r.json['error']


def test_google_login_servidor_no_configurado_responde_500(cliente, app):
    app.config['GOOGLE_CLIENT_ID'] = 'TU_GOOGLE_CLIENT_ID'
    r = cliente.post('/api/usuarios/google-login', json={'credential': 'fake-token'})
    assert r.status_code == 500
    assert 'no está configurado' in r.json['error']


def test_google_login_token_invalido_responde_401(cliente, app):
    app.config['GOOGLE_CLIENT_ID'] = '123456789-test.apps.googleusercontent.com'
    with patch('google.oauth2.id_token.verify_oauth2_token', side_effect=ValueError('Token inválido')):
        r = cliente.post('/api/usuarios/google-login', json={'credential': 'token-invalido'})
        assert r.status_code == 401
        assert 'inválido' in r.json['error']


def test_google_login_error_comunicacion_google_responde_502(cliente, app):
    app.config['GOOGLE_CLIENT_ID'] = '123456789-test.apps.googleusercontent.com'
    with patch('google.oauth2.id_token.verify_oauth2_token', side_effect=GoogleAuthError('Conexión fallida')):
        r = cliente.post('/api/usuarios/google-login', json={'credential': 'token-error-red'})
        assert r.status_code == 502
        assert 'conexión' in r.json['error'] or 'autenticación' in r.json['error']


def test_google_login_nuevo_usuario_crea_cuenta_y_sesion(cliente, app):
    app.config['GOOGLE_CLIENT_ID'] = '123456789-test.apps.googleusercontent.com'
    token_payload = {
        'email': 'estudiante.google@dmc.edu.co',
        'name': 'Estudiante Google',
        'picture': 'https://lh3.googleusercontent.com/avatar.jpg'
    }

    with patch('google.oauth2.id_token.verify_oauth2_token', return_value=token_payload):
        r = cliente.post('/api/usuarios/google-login', json={'credential': 'valid-google-jwt'})
        assert r.status_code == 200
        data = r.json['usuario']
        assert data['correo'] == 'estudiante.google@dmc.edu.co'
        assert data['nombre'] == 'Estudiante Google'
        assert data['rol'] == 'estudiante'
        assert data['foto_perfil'] == 'https://lh3.googleusercontent.com/avatar.jpg'
        assert data.get('id_estudiante') is not None

    # Verificar que el usuario y perfil existan en la base de datos
    with app.app_context():
        u = Usuario.query.filter_by(correo='estudiante.google@dmc.edu.co').first()
        assert u is not None
        assert u.activo is True
        assert u.perfil_estudiante is not None
        assert u.perfil_estudiante.nombre == 'Estudiante Google'

    # Verificar persistencia de sesión en peticiones subsecuentes
    sesion_resp = cliente.get('/api/usuarios/sesion')
    assert sesion_resp.status_code == 200
    assert sesion_resp.json['autenticado'] is True
    assert sesion_resp.json['usuario']['correo'] == 'estudiante.google@dmc.edu.co'

    # Verificar acceso a recurso protegido que exige sesión
    dash_resp = cliente.get('/api/dashboard')
    assert dash_resp.status_code == 200

    # Cerrar sesión
    logout_resp = cliente.post('/api/usuarios/logout')
    assert logout_resp.status_code == 200
    assert cliente.get('/api/usuarios/sesion').json['autenticado'] is False


def test_google_login_usuario_existente_inicia_sesion_y_mantiene_rol(escenario, cliente, app):
    app.config['GOOGLE_CLIENT_ID'] = '123456789-test.apps.googleusercontent.com'
    # 'doc1@dmc.edu' existe en el escenario con rol docente
    token_payload = {
        'email': 'doc1@dmc.edu',
        'name': 'Docente Uno Google',
        'picture': 'https://lh3.googleusercontent.com/docente.jpg'
    }

    with patch('google.oauth2.id_token.verify_oauth2_token', return_value=token_payload):
        r = cliente.post('/api/usuarios/google-login', json={'credential': 'valid-jwt-docente'})
        assert r.status_code == 200
        data = r.json['usuario']
        assert data['correo'] == 'doc1@dmc.edu'
        assert data['rol'] == 'docente'  # No debe sobreescribir el rol a estudiante
        assert data['foto_perfil'] == 'https://lh3.googleusercontent.com/docente.jpg'

    # Sesión activa como docente
    sesion_resp = cliente.get('/api/usuarios/sesion')
    assert sesion_resp.json['autenticado'] is True
    assert sesion_resp.json['usuario']['rol'] == 'docente'


def test_google_login_cuenta_desactivada_rechaza_acceso(escenario, admin, cliente, app):
    app.config['GOOGLE_CLIENT_ID'] = '123456789-test.apps.googleusercontent.com'
    uid = escenario['estudiantes'][0]['id_usuario']
    correo_inactivo = escenario['estudiantes'][0]['correo']
    admin.put(f'/api/usuarios/{uid}', json={'activo': False})

    token_payload = {
        'email': correo_inactivo,
        'name': 'Estudiante Desactivado',
    }

    with patch('google.oauth2.id_token.verify_oauth2_token', return_value=token_payload):
        r = cliente.post('/api/usuarios/google-login', json={'credential': 'jwt-inactivo'})
        assert r.status_code == 403
        assert 'desactivada' in r.json['error']

    # La sesión no debe quedar iniciada
    assert cliente.get('/api/usuarios/sesion').json['autenticado'] is False
