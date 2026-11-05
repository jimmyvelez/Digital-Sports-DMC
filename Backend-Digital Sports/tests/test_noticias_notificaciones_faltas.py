import pytest

from tests.test_partidos_clasificacion import programar

CONTENIDO = 'Contenido completo de la noticia deportiva del colegio con suficiente longitud.'


@pytest.fixture
def docente(escenario, nuevo_cliente):
    c = nuevo_cliente()
    c.login('doc1@dmc.edu')
    return c


@pytest.fixture
def estudiante(escenario, nuevo_cliente):
    c = nuevo_cliente()
    c.login('est1@dmc.edu')
    return c


# ---------------------------------------------------------------- Noticias
def test_docente_publica_y_estudiante_solo_ve_publicadas(docente, estudiante):
    pub = docente.post('/api/noticias', json={'titulo': 'Gran final', 'contenido': CONTENIDO, 'estado': 'publicada'})
    borrador = docente.post('/api/noticias', json={'titulo': 'Borrador interno', 'contenido': CONTENIDO})
    assert pub.status_code == 201 and borrador.json['estado'] == 'borrador'
    titulos = [n['titulo'] for n in estudiante.get('/api/noticias').json['items']]
    assert titulos == ['Gran final']
    assert estudiante.get(f"/api/noticias/{borrador.json['id_noticia']}").status_code == 404
    # retirar
    docente.patch(f"/api/noticias/{pub.json['id_noticia']}/estado", json={'estado': 'retirada'})
    assert estudiante.get('/api/noticias').json['total'] == 0


def test_docente_solo_edita_sus_noticias(docente, admin, nuevo_cliente):
    n = admin.post('/api/noticias', json={'titulo': 'Noticia del admin', 'contenido': CONTENIDO,
                                          'estado': 'publicada'}).json
    assert docente.put(f"/api/noticias/{n['id_noticia']}", json={'titulo': 'Cambiada'}).status_code == 403
    propia = docente.post('/api/noticias', json={'titulo': 'Mi noticia', 'contenido': CONTENIDO}).json
    assert docente.put(f"/api/noticias/{propia['id_noticia']}", json={'titulo': 'Mi noticia v2'}).status_code == 200
    assert admin.put(f"/api/noticias/{propia['id_noticia']}", json={'estado': 'publicada'}).status_code == 200


def test_noticia_rechaza_imagen_javascript(docente):
    r = docente.post('/api/noticias', json={'titulo': 'Titulo valido', 'contenido': CONTENIDO,
                                            'imagen': 'javascript:alert(1)'})
    assert r.status_code == 400


# ---------------------------------------------------------------- Comentarios
def test_estudiante_comenta_y_gestiona_sus_comentarios(docente, estudiante, nuevo_cliente, app):
    n = docente.post('/api/noticias', json={'titulo': 'Gran final', 'contenido': CONTENIDO, 'estado': 'publicada'}).json
    url = f"/api/noticias/{n['id_noticia']}/comentarios"
    assert estudiante.post(url, json={'contenido': ' '}).status_code == 400
    assert estudiante.post(url, json={'contenido': 'x' * 1001}).status_code == 400
    c = estudiante.post(url, json={'contenido': '<script>alert(1)</script> ¡Vamos!'})
    assert c.status_code == 201
    assert c.json['contenido'] == '<script>alert(1)</script> ¡Vamos!'  # se guarda como texto; el frontend lo escapa
    id_c = c.json['id_comentario']

    otro = nuevo_cliente()
    otro.login('est2@dmc.edu')
    assert otro.put(f'/api/comentarios/{id_c}', json={'contenido': 'editado ajeno'}).status_code == 403
    assert otro.delete(f'/api/comentarios/{id_c}').status_code == 403
    assert otro.post(f'/api/comentarios/{id_c}/reportar').status_code == 200
    assert otro.post(f'/api/comentarios/{id_c}/reportar').status_code == 409

    assert estudiante.put(f'/api/comentarios/{id_c}', json={'contenido': 'Editado propio'}).json['fecha_edicion']
    assert otro.get(url).json['items'][0]['contenido'] == 'Editado propio'
    assert estudiante.delete(f'/api/comentarios/{id_c}').status_code == 200


def test_sin_sesion_no_se_comenta(docente, cliente):
    n = docente.post('/api/noticias', json={'titulo': 'Gran final', 'contenido': CONTENIDO, 'estado': 'publicada'}).json
    assert cliente.post(f"/api/noticias/{n['id_noticia']}/comentarios", json={'contenido': 'hola'}).status_code == 401
    assert cliente.get(f"/api/noticias/{n['id_noticia']}/comentarios").status_code == 200


def test_admin_modera_comentarios(docente, estudiante, admin):
    n = docente.post('/api/noticias', json={'titulo': 'Gran final', 'contenido': CONTENIDO, 'estado': 'publicada'}).json
    c = estudiante.post(f"/api/noticias/{n['id_noticia']}/comentarios", json={'contenido': 'Comentario feo'}).json
    admin.post(f"/api/comentarios/{c['id_comentario']}/reportar")
    assert admin.get('/api/comentarios?reportados=1').json['total'] == 1
    admin.patch(f"/api/comentarios/{c['id_comentario']}/moderar", json={'estado': 'oculto'})
    assert docente.get(f"/api/noticias/{n['id_noticia']}/comentarios").json['total'] == 0


# ---------------------------------------------------------------- Notificaciones
def test_programar_partido_notifica_a_estudiantes_de_ambos_equipos(escenario, docente, estudiante, nuevo_cliente):
    programar(docente, escenario)  # 601 vs 602
    n1 = estudiante.get('/api/notificaciones').json
    assert n1['no_leidas'] == 1 and n1['items'][0]['tipo'] == 'partido_nuevo'
    est2 = nuevo_cliente()
    est2.login('est2@dmc.edu')
    assert est2.get('/api/notificaciones/conteo').json['no_leidas'] == 1


def test_estudiante_de_otro_equipo_no_recibe(escenario, admin, estudiante):
    programar(admin, escenario, local=1, visitante=2)  # 602 vs 701: est1 (601) no juega
    assert estudiante.get('/api/notificaciones/conteo').json['no_leidas'] == 0


def test_cambios_importantes_y_resultado_notifican(escenario, docente, estudiante):
    p = programar(docente, escenario).json
    url = f"/api/partidos/{p['id_partido']}"
    docente.put(url, json={'fecha': '2026-10-02T15:00'})
    docente.put(url, json={'lugar': 'Coliseo'})
    docente.patch(url + '/estado', json={'estado': 'suspendido'})
    docente.patch(url + '/estado', json={'estado': 'programado'})
    docente.put(url + '/resultado', json={'goles_local': 1, 'goles_visitante': 0})
    tipos = [n['tipo'] for n in estudiante.get('/api/notificaciones').json['items']]
    assert tipos == ['resultado', 'cambio_estado', 'cambio_estado', 'cambio_lugar', 'cambio_horario', 'partido_nuevo']
    assert all(n['id_partido'] == p['id_partido']
               for n in estudiante.get('/api/notificaciones').json['items'])


def test_estado_de_lectura_y_propiedad(escenario, docente, estudiante, nuevo_cliente):
    programar(docente, escenario)
    programar(docente, escenario, fecha='2026-10-09T15:00')
    notis = estudiante.get('/api/notificaciones').json['items']
    est2 = nuevo_cliente()
    est2.login('est2@dmc.edu')
    # no puede marcar notificaciones ajenas
    assert est2.patch(f"/api/notificaciones/{notis[0]['id_notificacion']}/leida").status_code == 404
    assert estudiante.patch(f"/api/notificaciones/{notis[0]['id_notificacion']}/leida").json['leida'] is True
    assert estudiante.get('/api/notificaciones/conteo').json['no_leidas'] == 1
    assert estudiante.patch('/api/notificaciones/leer-todas').json['actualizadas'] == 1
    assert estudiante.get('/api/notificaciones?no_leidas=1').json['total'] == 0
    assert est2.get('/api/notificaciones/conteo').json['no_leidas'] == 2


# ---------------------------------------------------------------- Faltas
def test_docente_registra_falta_asociada(escenario, docente, admin, nuevo_cliente):
    p = programar(docente, escenario).json
    docente.patch(f"/api/partidos/{p['id_partido']}/estado", json={'estado': 'en_juego'})
    est1 = escenario['estudiantes'][0]['id_estudiante']
    eq601, eq602 = escenario['equipos'][0]['id_equipo'], escenario['equipos'][1]['id_equipo']
    datos = {'id_partido': p['id_partido'], 'id_equipo': eq601, 'id_estudiante': est1,
             'tipo': 'tarjeta_amarilla', 'descripcion': 'Juego brusco', 'minuto': 20}
    r = docente.post('/api/faltas', json=datos)
    assert r.status_code == 201
    assert (r.json['partido'], r.json['estudiante'], r.json['equipo']) == ('601 vs 602', 'Estudiante 1', '601')
    # estudiante que no pertenece al equipo indicado
    assert docente.post('/api/faltas', json={**datos, 'id_equipo': eq602}).status_code == 400
    # tipo inválido
    assert docente.post('/api/faltas', json={**datos, 'tipo': 'expulsion_eterna'}).status_code == 400

    # filtros
    assert docente.get(f"/api/faltas?id_estudiante={est1}").json['total'] == 1
    assert docente.get(f"/api/faltas?id_partido={p['id_partido']}").json['total'] == 1

    doc2 = nuevo_cliente()
    doc2.login('doc2@dmc.edu')
    assert doc2.post('/api/faltas', json=datos).status_code == 403
    assert doc2.put(f"/api/faltas/{r.json['id_falta']}", json={'estado': 'anulada'}).status_code == 403
    assert doc2.get('/api/faltas').json['total'] == 0  # no ve faltas de partidos ajenos
    assert docente.put(f"/api/faltas/{r.json['id_falta']}", json={'estado': 'cerrada'}).json['estado'] == 'cerrada'
    assert docente.delete(f"/api/faltas/{r.json['id_falta']}").status_code == 403
    assert admin.get('/api/faltas').json['total'] == 1
    # las faltas no afectan la clasificación
    docente.put(f"/api/partidos/{p['id_partido']}/resultado", json={'goles_local': 1, 'goles_visitante': 0})
    fila = next(f for f in admin.get('/api/posiciones?id_torneo=1').json['tabla'] if f['equipo'] == '601')
    assert fila['pts'] == 3


def test_falta_en_partido_programado_no_se_permite(escenario, docente):
    p = programar(docente, escenario).json
    r = docente.post('/api/faltas', json={'id_partido': p['id_partido'], 'id_equipo': escenario['equipos'][0]['id_equipo'],
                                          'tipo': 'otra'})
    assert r.status_code == 409


# ---------------------------------------------------------------- Dashboards y auditoría
def test_dashboards_por_rol(escenario, admin, docente, estudiante):
    programar(docente, escenario)
    a = admin.get('/api/dashboard').json
    assert a['rol'] == 'admin' and a['totales']['docentes'] == 2 and a['totales']['partidos_programados'] == 1
    d = docente.get('/api/dashboard').json
    assert d['totales']['equipos'] == 2 and len(d['proximos_partidos']) == 1
    e = estudiante.get('/api/dashboard').json
    assert e['proximo_partido']['equipo_local'] == '601'
    assert e['equipos'][0]['clasificacion']['posicion'] >= 1
    assert e['notificaciones_pendientes'] == 1


def test_auditoria_registra_cambios(escenario, admin, docente):
    p = programar(docente, escenario).json
    docente.put(f"/api/partidos/{p['id_partido']}/resultado", json={'goles_local': 1, 'goles_visitante': 0})
    acciones = [a['accion'] for a in admin.get('/api/auditoria?entidad=partido').json['items']]
    assert acciones[:2] == ['resultado', 'crear']


def test_reporte_comentario_notifica_y_acumula_al_admin(escenario, admin, docente, estudiante, nuevo_cliente):
    # 1. Crear noticia y comentario
    n = docente.post('/api/noticias', json={'titulo': 'Noticia deportiva', 'contenido': CONTENIDO, 'estado': 'publicada'}).json
    c = estudiante.post(f"/api/noticias/{n['id_noticia']}/comentarios", json={'contenido': 'Comentario con contenido inapropiado'}).json
    id_c = c['id_comentario']

    # 2. Estudiante 1 no puede auto-reportarse
    assert estudiante.post(f"/api/comentarios/{id_c}/reportar", json={'motivo': 'ofensivo'}).status_code == 400

    # 3. Usuario 2 reporta el comentario
    est2 = nuevo_cliente()
    est2.login('est2@dmc.edu')
    r1 = est2.post(f"/api/comentarios/{id_c}/reportar", json={'motivo': 'ofensivo', 'detalles': 'Usa malas palabras'})
    assert r1.status_code == 200

    # Verificar que el admin recibió la notificación
    notis_admin = admin.get('/api/notificaciones?no_leidas=1').json
    assert notis_admin['no_leidas'] == 1
    noti = notis_admin['items'][0]
    assert noti['tipo'] == 'reporte_comentario'
    assert 'Comentario con contenido inapropiado' in noti['mensaje']
    assert 'Lenguaje ofensivo o inapropiado' in noti['mensaje']
    assert noti['id_comentario'] == id_c

    # 4. Usuario 3 reporta el mismo comentario -> no debe crear otra notificación sino actualizar la existente
    est3 = nuevo_cliente()
    est3.login('doc1@dmc.edu')
    r2 = est3.post(f"/api/comentarios/{id_c}/reportar", json={'motivo': 'spam', 'detalles': 'Spam reiterado'})
    assert r2.status_code == 200

    notis_admin2 = admin.get('/api/notificaciones?no_leidas=1').json
    assert notis_admin2['no_leidas'] == 1  # Sigue habiendo 1 sola notificación no leída acumulada
    noti_act = notis_admin2['items'][0]
    assert '2 reportes' in noti_act['titulo'] or 'Reportes acumulados: 2' in noti_act['mensaje']

    # 5. Admin consulta historial de reportes
    historial = admin.get(f"/api/comentarios/{id_c}/reportes").json
    assert historial['total_reportes'] == 2
    assert len(historial['reportes']) == 2

    # 6. Admin modera el comentario (marca como visible y descarta reportes)
    mod = admin.patch(f"/api/comentarios/{id_c}/moderar", json={'estado': 'visible', 'limpiar_reportes': True})
    assert mod.status_code == 200
    assert mod.json['reportes'] == 0

    # Notificaciones del admin quedan marcadas como leídas
    assert admin.get('/api/notificaciones?no_leidas=1').json['no_leidas'] == 0

