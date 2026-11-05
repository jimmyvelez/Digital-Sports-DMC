from tests.conftest import CLAVE


def registrar(c, correo='nuevo@dmc.edu', **extra):
    return c.post('/api/usuarios/registro', json={'nombre': 'Nuevo Estudiante', 'correo': correo,
                                                  'contrasena': CLAVE, **extra})


def test_estudiante_se_registra_e_inicia_sesion(cliente, nuevo_cliente):
    r = registrar(cliente)
    assert r.status_code == 201
    assert r.json['usuario']['rol'] == 'estudiante'
    assert 'contrasena' not in r.json['usuario']
    assert r.json['usuario']['id_estudiante']  # perfil deportivo creado

    otro = nuevo_cliente()
    usuario = otro.login('nuevo@dmc.edu')
    assert usuario['rol'] == 'estudiante'
    assert otro.get('/api/usuarios/sesion').json['autenticado'] is True
    otro.post('/api/usuarios/logout')
    assert otro.get('/api/usuarios/sesion').json['autenticado'] is False


def test_registro_publico_ignora_rol_privilegiado(cliente):
    r = registrar(cliente, correo='hacker@dmc.edu', rol='admin')
    assert r.status_code == 201
    assert r.json['usuario']['rol'] == 'estudiante'


def test_registro_valida_datos(cliente):
    assert cliente.post('/api/usuarios/registro', json={'nombre': 'Ana', 'correo': 'mal', 'contrasena': CLAVE}).status_code == 400
    assert cliente.post('/api/usuarios/registro', json={'nombre': 'Ana María', 'correo': 'a@b.co', 'contrasena': 'corta'}).status_code == 400
    assert cliente.post('/api/usuarios/registro', json={'nombre': 'Ana María', 'correo': 'a@b.co', 'contrasena': 'soloLetras'}).status_code == 400
    assert registrar(cliente, correo='dup@dmc.edu').status_code == 201
    assert registrar(cliente, correo='DUP@dmc.edu').status_code == 409


def test_contrasena_se_guarda_con_hash(app, cliente):
    registrar(cliente, correo='hash@dmc.edu')
    from backend.models import Usuario
    with app.app_context():
        u = Usuario.query.filter_by(correo='hash@dmc.edu').first()
        assert u.contrasena != CLAVE and u.contrasena.startswith(('scrypt:', 'pbkdf2:'))


def test_login_incorrecto(cliente):
    registrar(cliente, correo='x@dmc.edu')
    r = cliente.post('/api/usuarios/login', json={'correo': 'x@dmc.edu', 'contrasena': 'Otra12345'})
    assert r.status_code == 401


def test_estudiante_no_accede_a_funciones_administrativas(escenario, nuevo_cliente):
    est = nuevo_cliente()
    est.login('est1@dmc.edu')
    t = escenario['torneo']['id_torneo']
    assert est.get('/api/usuarios').status_code == 403
    assert est.post('/api/torneos', json={'nombre': 'X torneo', 'categoria': 'Mixto'}).status_code == 403
    assert est.post('/api/equipos', json={'id_torneo': t, 'nombre': 'Hack', 'curso': 'x'}).status_code == 403
    assert est.post('/api/partidos', json={}).status_code == 403
    assert est.put(f"/api/partidos/1/resultado", json={'goles_local': 1, 'goles_visitante': 0}).status_code == 403
    assert est.post('/api/noticias', json={'titulo': 'Titulo', 'contenido': 'x' * 30}).status_code == 403
    assert est.get('/api/faltas').status_code == 403
    assert est.get('/api/auditoria').status_code == 403


def test_docente_no_accede_a_operaciones_de_admin(escenario, nuevo_cliente):
    doc = nuevo_cliente()
    doc.login('doc1@dmc.edu')
    assert doc.get('/api/usuarios').status_code == 403
    assert doc.post('/api/usuarios', json={'nombre': 'Otro Admin', 'correo': 'o@a.co', 'contrasena': CLAVE,
                                           'rol': 'admin'}).status_code == 403
    assert doc.post('/api/torneos', json={'nombre': 'Nuevo', 'categoria': 'Mixto'}).status_code == 403
    assert doc.get('/api/auditoria').status_code == 403
    uid = escenario['estudiantes'][0]['id_usuario']
    assert doc.put(f'/api/usuarios/{uid}', json={'rol': 'admin'}).status_code == 403


def test_sin_sesion_responde_401(cliente):
    assert cliente.get('/api/dashboard').status_code == 401
    assert cliente.get('/api/notificaciones').status_code == 401


def test_peticion_sin_cabecera_csrf_es_rechazada(app, escenario):
    raw = app.test_client()
    raw.post('/api/usuarios/login', json={'correo': 'admin@digitalsports.com', 'contrasena': 'Admin12345'},
             headers={'X-Requested-With': 'fetch'})
    r = raw.post('/api/torneos', json={'nombre': 'CSRF', 'categoria': 'x'})
    assert r.status_code == 403


def test_admin_gestiona_roles_y_cuentas(escenario, admin, nuevo_cliente):
    uid = escenario['estudiantes'][0]['id_usuario']
    assert admin.put(f'/api/usuarios/{uid}', json={'activo': False}).status_code == 200
    c = nuevo_cliente()
    r = c.post('/api/usuarios/login', json={'correo': 'est1@dmc.edu', 'contrasena': CLAVE})
    assert r.status_code == 403  # cuenta desactivada

    yo = admin.get('/api/usuarios/sesion').json['usuario']['id_usuario']
    assert admin.put(f'/api/usuarios/{yo}', json={'activo': False}).status_code == 409
    assert admin.put(f'/api/usuarios/{yo}', json={'rol': 'docente'}).status_code == 409


def test_desactivar_cuenta_cierra_sesion_activa(escenario, admin, nuevo_cliente):
    est = nuevo_cliente()
    est.login('est2@dmc.edu')
    assert est.get('/api/dashboard').status_code == 200
    admin.put(f"/api/usuarios/{escenario['estudiantes'][1]['id_usuario']}", json={'activo': False})
    assert est.get('/api/dashboard').status_code == 401


def test_recuperacion_de_contrasena(app, cliente, nuevo_cliente):
    registrar(cliente, correo='olvido@dmc.edu')
    assert cliente.post('/api/usuarios/recuperar', json={'correo': 'olvido@dmc.edu'}).status_code == 200
    assert cliente.post('/api/usuarios/recuperar', json={'correo': 'noexiste@dmc.edu'}).status_code == 200

    from backend.models import Usuario
    from backend.services.auth_service import generar_token_reset
    with app.test_request_context():
        token = generar_token_reset(Usuario.query.filter_by(correo='olvido@dmc.edu').first())

    r = cliente.post('/api/usuarios/restablecer', json={'token': token, 'contrasena': 'NuevaClave99'})
    assert r.status_code == 200
    # token de un solo uso
    assert cliente.post('/api/usuarios/restablecer', json={'token': token, 'contrasena': 'OtraClave99'}).status_code == 400
    nuevo_cliente().login('olvido@dmc.edu', 'NuevaClave99')


def test_perfil_cambio_de_contrasena_requiere_la_actual(cliente):
    registrar(cliente, correo='perfil@dmc.edu')
    r = cliente.put('/api/usuarios/perfil', json={'contrasena_actual': 'mala', 'contrasena_nueva': 'Nueva12345'})
    assert r.status_code == 400
    r = cliente.put('/api/usuarios/perfil', json={'contrasena_actual': CLAVE, 'contrasena_nueva': 'Nueva12345',
                                                   'curso': '1101'})
    assert r.status_code == 200 and r.json['usuario']['curso'] == '1101'
