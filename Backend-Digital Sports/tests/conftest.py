import pytest

from backend import create_app
from backend.extensions import db

ADMIN = {'correo': 'admin@digitalsports.com', 'contrasena': 'Admin12345'}
CLAVE = 'Clave12345'


class Cliente:
    """Cliente de pruebas que envía la cabecera CSRF como lo hace el frontend."""

    def __init__(self, app):
        self._c = app.test_client()

    def _h(self, kwargs):
        kwargs.setdefault('headers', {})['X-Requested-With'] = 'fetch'
        return kwargs

    def get(self, url, **kw):
        return self._c.get(url, **kw)

    def post(self, url, **kw):
        return self._c.post(url, **self._h(kw))

    def put(self, url, **kw):
        return self._c.put(url, **self._h(kw))

    def patch(self, url, **kw):
        return self._c.patch(url, **self._h(kw))

    def delete(self, url, **kw):
        return self._c.delete(url, **self._h(kw))

    @property
    def raw(self):
        return self._c

    def login(self, correo, contrasena=CLAVE):
        r = self.post('/api/usuarios/login', json={'correo': correo, 'contrasena': contrasena})
        assert r.status_code == 200, r.json
        return r.json['usuario']


@pytest.fixture
def app():
    app = create_app('testing')
    yield app
    with app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture
def cliente(app):
    return Cliente(app)


@pytest.fixture
def nuevo_cliente(app):
    return lambda: Cliente(app)


@pytest.fixture
def admin(app):
    c = Cliente(app)
    c.login(ADMIN['correo'], ADMIN['contrasena'])
    return c


@pytest.fixture
def escenario(app, admin):
    """
    Datos base: 1 torneo activo, 2 docentes, 3 equipos (2 del docente1),
    2 estudiantes registrados asignados a equipos distintos.
    """
    def crear_usuario(nombre, correo, rol):
        r = admin.post('/api/usuarios', json={'nombre': nombre, 'correo': correo, 'contrasena': CLAVE, 'rol': rol})
        assert r.status_code == 201, r.json
        return r.json

    doc1 = crear_usuario('Docente Uno', 'doc1@dmc.edu', 'docente')
    doc2 = crear_usuario('Docente Dos', 'doc2@dmc.edu', 'docente')

    torneo = admin.post('/api/torneos', json={'nombre': 'Masculino A', 'categoria': 'Masculino',
                                              'estado': 'activo'}).json
    equipos = []
    for nombre, docente in (('601', doc1), ('602', doc1), ('701', doc2)):
        r = admin.post('/api/equipos', json={'id_torneo': torneo['id_torneo'], 'nombre': nombre,
                                             'curso': 'Sexto', 'id_docente': docente['id_usuario']})
        assert r.status_code == 201, r.json
        equipos.append(r.json)

    estudiantes = []
    for i, eq in ((1, equipos[0]), (2, equipos[1])):
        c = Cliente(app)
        r = c.post('/api/usuarios/registro', json={'nombre': f'Estudiante {i}', 'correo': f'est{i}@dmc.edu',
                                                   'contrasena': CLAVE, 'curso': '601'})
        assert r.status_code == 201, r.json
        perfil = r.json['usuario']
        r = admin.post(f"/api/equipos/{eq['id_equipo']}/integrantes", json={'id_estudiante': perfil['id_estudiante']})
        assert r.status_code == 201, r.json
        estudiantes.append(perfil)

    return {'torneo': torneo, 'equipos': equipos, 'docentes': [doc1, doc2], 'estudiantes': estudiantes}
