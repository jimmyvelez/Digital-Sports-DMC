from tests.conftest import CLAVE


def test_docente_crea_equipo_y_queda_como_responsable(escenario, nuevo_cliente):
    doc = nuevo_cliente()
    yo = doc.login('doc1@dmc.edu')
    r = doc.post('/api/equipos', json={'id_torneo': escenario['torneo']['id_torneo'], 'nombre': '603',
                                       'curso': 'Sexto', 'id_docente': escenario['docentes'][1]['id_usuario']})
    assert r.status_code == 201
    assert r.json['id_docente'] == yo['id_usuario']  # ignora intento de asignar otro responsable


def test_nombre_de_equipo_duplicado_en_torneo(escenario, admin):
    r = admin.post('/api/equipos', json={'id_torneo': escenario['torneo']['id_torneo'], 'nombre': '601',
                                         'curso': 'Sexto'})
    assert r.status_code == 409


def test_docente_asigna_estudiantes_sin_duplicados(escenario, admin, nuevo_cliente):
    doc = nuevo_cliente()
    doc.login('doc1@dmc.edu')
    est = admin.post('/api/estudiantes', json={'nombre': 'Jugador Sin Cuenta', 'curso': '602'}).json
    eq = escenario['equipos'][1]['id_equipo']
    assert doc.post(f'/api/equipos/{eq}/integrantes', json={'id_estudiante': est['id_estudiante'], 'dorsal': 10}).status_code == 201
    # duplicado en el mismo equipo
    assert doc.post(f'/api/equipos/{eq}/integrantes', json={'id_estudiante': est['id_estudiante']}).status_code == 409
    # otro equipo del mismo torneo (regla por defecto: un equipo por torneo)
    eq_otro = escenario['equipos'][0]['id_equipo']
    assert doc.post(f'/api/equipos/{eq_otro}/integrantes', json={'id_estudiante': est['id_estudiante']}).status_code == 409
    # dorsal repetido
    est2 = admin.post('/api/estudiantes', json={'nombre': 'Jugador Dos', 'curso': '602'}).json
    assert doc.post(f'/api/equipos/{eq}/integrantes', json={'id_estudiante': est2['id_estudiante'], 'dorsal': 10}).status_code == 409

    detalle = doc.get(f'/api/equipos/{eq}').json
    assert [i['nombre'] for i in detalle['integrantes']].count('Jugador Sin Cuenta') == 1


def test_estudiante_puede_estar_en_equipos_de_torneos_distintos(escenario, admin):
    t2 = admin.post('/api/torneos', json={'nombre': 'Interroscas', 'categoria': 'Roscas', 'estado': 'activo'}).json
    eq = admin.post('/api/equipos', json={'id_torneo': t2['id_torneo'], 'nombre': 'Roscas FC', 'curso': 'Mixto'}).json
    id_est = escenario['estudiantes'][0]['id_estudiante']
    assert admin.post(f"/api/equipos/{eq['id_equipo']}/integrantes", json={'id_estudiante': id_est}).status_code == 201


def test_regla_configurable_multiples_equipos(app, escenario, admin):
    app.config['PERMITIR_MULTIPLES_EQUIPOS_POR_TORNEO'] = True
    id_est = escenario['estudiantes'][0]['id_estudiante']
    eq = escenario['equipos'][1]['id_equipo']
    assert admin.post(f'/api/equipos/{eq}/integrantes', json={'id_estudiante': id_est}).status_code == 201


def test_docente_no_gestiona_equipo_ajeno(escenario, nuevo_cliente):
    doc2 = nuevo_cliente()
    doc2.login('doc2@dmc.edu')
    eq_doc1 = escenario['equipos'][0]['id_equipo']
    assert doc2.put(f'/api/equipos/{eq_doc1}', json={'nombre': 'Hackeado'}).status_code == 403
    assert doc2.post(f'/api/equipos/{eq_doc1}/integrantes', json={'id_estudiante': 1}).status_code == 403
    assert doc2.delete(f'/api/equipos/{eq_doc1}').status_code == 403


def test_baja_de_integrante_conserva_historial(escenario, admin):
    eq = escenario['equipos'][0]['id_equipo']
    id_est = escenario['estudiantes'][0]['id_estudiante']
    assert admin.delete(f'/api/equipos/{eq}/integrantes/{id_est}').status_code == 200
    assert admin.get(f'/api/equipos/{eq}').json['total_integrantes'] == 0
    historial = admin.get(f'/api/equipos/{eq}/historial').json
    assert historial[0]['activo'] is False and historial[0]['fecha_baja']
    # puede volver a darse de alta
    assert admin.post(f'/api/equipos/{eq}/integrantes', json={'id_estudiante': id_est}).status_code == 201


def test_estudiante_consulta_su_equipo(escenario, nuevo_cliente):
    est = nuevo_cliente()
    est.login('est1@dmc.edu')
    sesion = est.get('/api/usuarios/sesion').json['usuario']
    assert sesion['equipos'][0]['nombre'] == '601'
    mios = est.get('/api/equipos?mios=1').json['items']
    assert [e['nombre'] for e in mios] == ['601']
    detalle = est.get(f"/api/equipos/{mios[0]['id_equipo']}").json
    assert detalle['integrantes'][0]['nombre'] == 'Estudiante 1'
    assert detalle['puede_gestionar'] is False
    panel = est.get('/api/dashboard').json
    assert panel['equipos'][0]['nombre'] == '601'


def test_plantilla_oculta_para_visitantes(escenario, cliente):
    eq = escenario['equipos'][0]['id_equipo']
    assert 'integrantes' not in cliente.get(f'/api/equipos/{eq}').json


def test_listado_de_estudiantes_disponibles_por_torneo(escenario, admin):
    t = escenario['torneo']['id_torneo']
    nuevo = admin.post('/api/usuarios', json={'nombre': 'Libre Total', 'correo': 'libre@dmc.edu',
                                              'contrasena': CLAVE, 'rol': 'estudiante'})
    assert nuevo.status_code == 201
    disponibles = admin.get(f'/api/estudiantes?disponibles_torneo={t}').json['items']
    assert [d['nombre'] for d in disponibles] == ['Libre Total']
