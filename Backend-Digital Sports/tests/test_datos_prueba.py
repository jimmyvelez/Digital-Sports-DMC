import pytest

from backend.datos_prueba import CLAVE_DOCENTE, CLAVE_ESTUDIANTE, sembrar
from tests.conftest import Cliente


def test_datos_de_prueba_para_todos_los_roles(app):
    with app.app_context():
        resumen = sembrar(app, log=lambda *_: None)
    roles = {c[0] for c in resumen['cuentas']}
    assert {'admin', 'docente', 'estudiante'} <= roles

    admin = Cliente(app)
    admin.login('admin@digitalsports.com', 'Admin12345')
    panel = admin.get('/api/dashboard').json['totales']
    assert panel['torneos'] == 4 and panel['docentes'] == 3
    assert panel['partidos_finalizados'] > 0 and panel['partidos_programados'] > 0
    assert panel['comentarios_reportados'] == 1 and panel['usuarios_inactivos'] == 1

    # La clasificación se calculó sola con los resultados cargados
    tabla = admin.get('/api/posiciones?id_torneo=1').json['tabla']
    assert sum(f['pj'] for f in tabla) > 0 and tabla[0]['pts'] >= tabla[-1]['pts']

    # Un docente y un estudiante de prueba pueden iniciar sesión y ven sus datos
    doc = Cliente(app)
    doc.login('carlos.rodriguez@dmc.edu.co', CLAVE_DOCENTE)
    assert doc.get('/api/dashboard').json['totales']['equipos'] >= 3
    correo_est = next(c[1] for c in resumen['cuentas'] if c[0] == 'estudiante')
    est = Cliente(app)
    est.login(correo_est, CLAVE_ESTUDIANTE)
    d = est.get('/api/dashboard').json
    assert d['equipos'] and d['notificaciones_pendientes'] > 0

    # No se puede volver a cargar sobre una base con datos
    with app.app_context(), pytest.raises(RuntimeError):
        sembrar(app, log=lambda *_: None)
