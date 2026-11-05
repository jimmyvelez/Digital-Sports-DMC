import pytest


def programar(c, esc, local=0, visitante=1, fecha='2026-10-01T15:00', lugar='Cancha 1'):
    return c.post('/api/partidos', json={
        'id_torneo': esc['torneo']['id_torneo'],
        'id_equipo_local': esc['equipos'][local]['id_equipo'],
        'id_equipo_visitante': esc['equipos'][visitante]['id_equipo'],
        'fecha': fecha, 'lugar': lugar})


def tabla(c, esc):
    r = c.get(f"/api/posiciones?id_torneo={esc['torneo']['id_torneo']}")
    return {f['equipo']: f for f in r.json['tabla']}


@pytest.fixture
def docente(escenario, nuevo_cliente):
    c = nuevo_cliente()
    c.login('doc1@dmc.edu')
    return c


# ---------------------------------------------------------------- Partidos
def test_docente_programa_partido(escenario, docente):
    r = programar(docente, escenario)
    assert r.status_code == 201
    assert r.json['estado'] == 'programado'
    assert r.json['goles_local'] is None and r.json['marcador'] is None


def test_equipos_deben_ser_diferentes(escenario, docente):
    assert programar(docente, escenario, local=0, visitante=0).status_code == 400


def test_evita_duplicados_y_choques(escenario, docente, admin):
    assert programar(docente, escenario).status_code == 201
    assert programar(docente, escenario, local=1, visitante=0, fecha='2026-10-01T18:00').status_code == 409  # duplicado
    # choque de horario: 601 ya juega a las 15:00
    assert programar(admin, escenario, local=0, visitante=2, fecha='2026-10-02T15:00').status_code == 201
    r = programar(admin, escenario, local=2, visitante=1, fecha='2026-10-02T15:30', lugar='Cancha 2')
    assert r.status_code == 409
    # cancha ocupada
    r = programar(admin, escenario, local=1, visitante=2, fecha='2026-10-01T16:00', lugar='cancha 1')
    assert r.status_code == 409


def test_fecha_dentro_del_torneo(escenario, admin):
    admin.put(f"/api/torneos/{escenario['torneo']['id_torneo']}", json={'fecha_inicio': '2026-09-01',
                                                                        'fecha_fin': '2026-11-30'})
    assert programar(admin, escenario, fecha='2026-12-10T10:00').status_code == 400


def test_registrar_y_actualizar_resultado(escenario, docente):
    p = programar(docente, escenario).json
    r = docente.put(f"/api/partidos/{p['id_partido']}/resultado", json={'goles_local': 2, 'goles_visitante': 1})
    assert r.status_code == 200 and r.json['estado'] == 'finalizado' and r.json['marcador'] == '2-1'
    r = docente.put(f"/api/partidos/{p['id_partido']}/resultado", json={'goles_local': 2, 'goles_visitante': 2})
    assert r.status_code == 200 and r.json['marcador'] == '2-2'
    assert docente.put(f"/api/partidos/{p['id_partido']}/resultado",
                       json={'goles_local': -1, 'goles_visitante': 0}).status_code == 400


def test_transiciones_de_estado(escenario, docente, admin):
    p = programar(docente, escenario).json
    url = f"/api/partidos/{p['id_partido']}/estado"
    assert docente.patch(url, json={'estado': 'finalizado'}).status_code == 400  # sin resultado
    assert docente.patch(url, json={'estado': 'en_juego'}).json['goles_local'] == 0
    assert docente.patch(url, json={'estado': 'programado'}).status_code == 409  # en_juego -> programado no
    assert docente.patch(url, json={'estado': 'finalizado'}).json['estado'] == 'finalizado'
    assert docente.patch(url, json={'estado': 'cancelado'}).status_code == 403  # solo admin anula
    assert admin.patch(url, json={'estado': 'cancelado'}).json['estado'] == 'cancelado'
    assert admin.patch(url, json={'estado': 'programado'}).status_code == 409  # cancelado es terminal
    assert docente.put(f"/api/partidos/{p['id_partido']}/resultado",
                       json={'goles_local': 1, 'goles_visitante': 0}).status_code == 409


def test_suspendido_se_reprograma(escenario, docente):
    p = programar(docente, escenario).json
    url = f"/api/partidos/{p['id_partido']}"
    assert docente.patch(url + '/estado', json={'estado': 'suspendido', 'motivo': 'Lluvia'}).status_code == 200
    assert docente.put(url + '/resultado', json={'goles_local': 1, 'goles_visitante': 0}).status_code == 409
    assert docente.patch(url + '/estado', json={'estado': 'programado'}).status_code == 200
    assert docente.put(url, json={'fecha': '2026-10-08T15:00'}).json['fecha'].startswith('2026-10-08')


def test_docente_no_gestiona_partido_ajeno(escenario, nuevo_cliente, admin):
    p = programar(admin, escenario, local=0, visitante=1).json  # equipos de doc1
    doc2 = nuevo_cliente()
    doc2.login('doc2@dmc.edu')
    assert doc2.put(f"/api/partidos/{p['id_partido']}/resultado",
                    json={'goles_local': 1, 'goles_visitante': 0}).status_code == 403
    assert doc2.delete(f"/api/partidos/{p['id_partido']}").status_code == 403


def test_eliminar_solo_programados(escenario, docente):
    p = programar(docente, escenario).json
    q = programar(docente, escenario, fecha='2026-10-05T10:00').json
    docente.put(f"/api/partidos/{q['id_partido']}/resultado", json={'goles_local': 0, 'goles_visitante': 0})
    assert docente.delete(f"/api/partidos/{q['id_partido']}").status_code == 409
    assert docente.delete(f"/api/partidos/{p['id_partido']}").status_code == 200


def test_filtros_de_partidos(escenario, docente, nuevo_cliente):
    programar(docente, escenario, fecha='2026-10-01T15:00')
    p2 = programar(docente, escenario, local=0, visitante=2, fecha='2026-10-03T15:00').json
    docente.put(f"/api/partidos/{p2['id_partido']}/resultado", json={'goles_local': 3, 'goles_visitante': 0})
    assert docente.get('/api/partidos?estado=finalizado').json['total'] == 1
    assert docente.get('/api/partidos?desde=2026-10-02').json['total'] == 1
    eq3 = escenario['equipos'][2]['id_equipo']
    assert docente.get(f'/api/partidos?id_equipo={eq3}').json['total'] == 1
    est = nuevo_cliente()
    est.login('est2@dmc.edu')  # integra 602
    assert est.get('/api/partidos?mios=1').json['total'] == 1


# ---------------------------------------------------------------- Clasificación
def test_victoria_suma_tres_puntos(escenario, docente):
    p = programar(docente, escenario).json
    docente.put(f"/api/partidos/{p['id_partido']}/resultado", json={'goles_local': 3, 'goles_visitante': 1})
    t = tabla(docente, escenario)
    assert (t['601']['pts'], t['601']['pg'], t['601']['gf'], t['601']['gc'], t['601']['dg']) == (3, 1, 3, 1, 2)
    assert (t['602']['pts'], t['602']['pp'], t['602']['dg']) == (0, 1, -2)
    assert t['601']['posicion'] == 1


def test_empate_suma_un_punto(escenario, docente):
    p = programar(docente, escenario).json
    docente.put(f"/api/partidos/{p['id_partido']}/resultado", json={'goles_local': 1, 'goles_visitante': 1})
    t = tabla(docente, escenario)
    assert t['601']['pts'] == t['602']['pts'] == 1
    assert t['601']['pe'] == t['602']['pe'] == 1
    assert t['601']['posicion'] == t['602']['posicion'] == 1  # empate total: comparten posición


def test_partidos_no_finalizados_no_cuentan(escenario, docente, admin):
    p = programar(docente, escenario).json
    docente.put(f"/api/partidos/{p['id_partido']}/resultado", json={'goles_local': 2, 'goles_visitante': 0,
                                                                     'finalizar': False})
    assert tabla(docente, escenario)['601']['pj'] == 0  # en juego
    docente.patch(f"/api/partidos/{p['id_partido']}/estado", json={'estado': 'finalizado'})
    assert tabla(docente, escenario)['601']['pts'] == 3
    admin.patch(f"/api/partidos/{p['id_partido']}/estado", json={'estado': 'cancelado'})  # anulado
    t = tabla(docente, escenario)
    assert t['601']['pj'] == 0 and t['601']['pts'] == 0


def test_modificar_resultado_recalcula_sin_duplicar(escenario, docente):
    p = programar(docente, escenario).json
    url = f"/api/partidos/{p['id_partido']}/resultado"
    docente.put(url, json={'goles_local': 2, 'goles_visitante': 0})
    docente.put(url, json={'goles_local': 2, 'goles_visitante': 0})  # guardar dos veces
    t = tabla(docente, escenario)
    assert t['601']['pj'] == 1 and t['601']['pts'] == 3
    docente.put(url, json={'goles_local': 0, 'goles_visitante': 1})
    t = tabla(docente, escenario)
    assert (t['601']['pts'], t['602']['pts'], t['601']['pj'], t['602']['pj']) == (0, 3, 1, 1)
    assert t['602']['posicion'] == 1


def test_orden_por_diferencia_y_goles_a_favor(escenario, admin):
    # 601 gana 1-0 a 602; 701 gana 3-0 a 602; 601 y 701 empatan 2-2
    # 601: 4 pts, dg +1, gf 3 | 701: 4 pts, dg +3, gf 5 -> 701 primero
    for loc, vis, fecha, gl, gv in ((0, 1, '2026-10-01T08:00', 1, 0), (2, 1, '2026-10-02T08:00', 3, 0),
                                   (0, 2, '2026-10-03T08:00', 2, 2)):
        p = programar(admin, escenario, local=loc, visitante=vis, fecha=fecha).json
        admin.put(f"/api/partidos/{p['id_partido']}/resultado", json={'goles_local': gl, 'goles_visitante': gv})
    filas = admin.get(f"/api/torneos/{escenario['torneo']['id_torneo']}/clasificacion").json['tabla']
    assert [f['equipo'] for f in filas] == ['701', '601', '602']
    assert [f['pts'] for f in filas] == [4, 4, 0]


def test_puntuacion_y_criterios_configurables(escenario, admin):
    admin.put(f"/api/torneos/{escenario['torneo']['id_torneo']}",
              json={'puntos_victoria': 2, 'criterios_desempate': ['pts', 'gf']})
    p = programar(admin, escenario).json
    admin.put(f"/api/partidos/{p['id_partido']}/resultado", json={'goles_local': 1, 'goles_visitante': 0})
    assert tabla(admin, escenario)['601']['pts'] == 2


def test_no_existe_edicion_manual_de_puntos(escenario, admin):
    assert admin.post('/api/posiciones', json={'id_torneo': 1, 'id_equipo': 1, 'pts': 99}).status_code == 405
    assert admin.put('/api/posiciones/1/1', json={'pts': 99}).status_code in (404, 405)


def test_goles_coherentes_con_resultado(escenario, docente):
    p = programar(docente, escenario).json
    docente.put(f"/api/partidos/{p['id_partido']}/resultado", json={'goles_local': 1, 'goles_visitante': 0})
    est1 = escenario['estudiantes'][0]['id_estudiante']  # de 601 (local)
    assert docente.post('/api/goles', json={'id_partido': p['id_partido'], 'id_estudiante': est1}).status_code == 201
    assert docente.post('/api/goles', json={'id_partido': p['id_partido'], 'id_estudiante': est1}).status_code == 409
    goleadores = docente.get('/api/goles/goleadores').json
    assert goleadores[0]['goles'] == 1 and goleadores[0]['equipo'] == '601'
    # no se puede bajar el resultado por debajo de los goles registrados
    assert docente.put(f"/api/partidos/{p['id_partido']}/resultado",
                       json={'goles_local': 0, 'goles_visitante': 0}).status_code == 409
