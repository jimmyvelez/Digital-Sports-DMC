"""La migración debe actualizar una BD con el esquema ORIGINAL sin perder datos."""
import sqlite3

from backend import create_app
from backend.config import TestingConfig, config
from tests.conftest import Cliente

ESQUEMA_ORIGINAL = """
CREATE TABLE torneo (id_torneo INTEGER PRIMARY KEY AUTOINCREMENT, nombre VARCHAR(100) NOT NULL, categoria VARCHAR(50) NOT NULL);
CREATE TABLE docente (id_docente INTEGER PRIMARY KEY AUTOINCREMENT, nombre VARCHAR(100) NOT NULL);
CREATE TABLE usuario (id_usuario INTEGER PRIMARY KEY AUTOINCREMENT, nombre VARCHAR(100) NOT NULL,
    correo VARCHAR(150) NOT NULL UNIQUE, contrasena VARCHAR(255) NOT NULL, rol VARCHAR(100) NOT NULL);
CREATE TABLE equipo (id_equipo INTEGER PRIMARY KEY AUTOINCREMENT, id_torneo INTEGER NOT NULL REFERENCES torneo(id_torneo),
    nombre VARCHAR(100) NOT NULL, curso VARCHAR(50) NOT NULL, categoria VARCHAR(50) NOT NULL);
CREATE TABLE estudiante (id_estudiante INTEGER PRIMARY KEY AUTOINCREMENT, id_equipo INTEGER NOT NULL REFERENCES equipo(id_equipo),
    nombre VARCHAR(100) NOT NULL);
CREATE TABLE partido (id_partido INTEGER PRIMARY KEY AUTOINCREMENT, id_torneo INTEGER NOT NULL, id_equipo_local INTEGER NOT NULL,
    id_equipo_visitante INTEGER NOT NULL, id_usuario INTEGER, fecha DATETIME NOT NULL, estado VARCHAR(30) NOT NULL,
    marcador VARCHAR(20));
CREATE TABLE gol (id_gol INTEGER PRIMARY KEY AUTOINCREMENT, id_partido INTEGER NOT NULL, id_estudiante INTEGER NOT NULL,
    fecha DATETIME NOT NULL);
CREATE TABLE posicion (id_torneo INTEGER NOT NULL, id_equipo INTEGER NOT NULL, pj INTEGER NOT NULL, pg INTEGER NOT NULL,
    pe INTEGER NOT NULL, pp INTEGER NOT NULL, gf INTEGER NOT NULL, gc INTEGER NOT NULL, pts INTEGER NOT NULL,
    PRIMARY KEY (id_torneo, id_equipo));
CREATE TABLE noticia (id_noticia INTEGER PRIMARY KEY AUTOINCREMENT, titulo VARCHAR(200) NOT NULL, descripcion TEXT NOT NULL,
    imagen VARCHAR(500));

INSERT INTO torneo VALUES (1, 'Masculino Sección A', 'Masculino A');
INSERT INTO usuario VALUES (1, 'Profe Carlos', 'carlos@dmc.edu', 'x', 'profesor');
INSERT INTO usuario VALUES (2, 'Laura', 'laura@dmc.edu', 'x', 'estudiante');
INSERT INTO equipo VALUES (1, 1, '601', 'Sexto', 'masculino');
INSERT INTO equipo VALUES (2, 1, '702', 'Septimo', 'masculino');
INSERT INTO estudiante VALUES (1, 1, 'Juan Pérez');
INSERT INTO partido VALUES (1, 1, 1, 2, 1, '2026-06-01 10:00:00', 'jugado', '3 – 2');
INSERT INTO partido VALUES (2, 1, 2, 1, 1, '2026-06-10 10:00:00', 'proximo', '0-0');
INSERT INTO partido VALUES (3, 1, 2, 1, 1, '2026-06-05 10:00:00', 'jugado', '– –');
INSERT INTO gol VALUES (1, 1, 1, '2026-06-01 10:20:00');
INSERT INTO posicion VALUES (1, 1, 9, 9, 0, 0, 30, 0, 27);
INSERT INTO noticia VALUES (1, 'Noticia antigua', 'Contenido existente de la noticia.', '../assets/img/noticia1.jpg');
"""


def test_migra_bd_original_sin_perder_datos(tmp_path):
    ruta = tmp_path / 'legacy.db'
    con = sqlite3.connect(ruta)
    con.executescript(ESQUEMA_ORIGINAL)
    con.commit()
    con.close()

    class Legacy(TestingConfig):
        SQLALCHEMY_DATABASE_URI = f'sqlite:///{ruta.as_posix()}'

    config['legacy'] = Legacy
    app = create_app('legacy')
    c = Cliente(app)

    # Datos existentes conservados y normalizados
    partidos = {p['id_partido']: p for p in c.get('/api/partidos').json['items']}
    assert partidos[1]['estado'] == 'finalizado' and (partidos[1]['goles_local'], partidos[1]['goles_visitante']) == (3, 2)
    assert partidos[2]['estado'] == 'programado' and partidos[2]['marcador'] is None
    assert partidos[3]['estado'] == 'programado' and 'Migración' in partidos[3]['observaciones']

    # Clasificación calculada desde resultados (se ignoran los puntos manuales heredados: 27)
    tabla = {f['equipo']: f for f in c.get('/api/posiciones?id_torneo=1').json['tabla']}
    assert tabla['601']['pts'] == 3 and tabla['702']['pts'] == 0

    # Noticia heredada visible como publicada
    assert c.get('/api/noticias').json['items'][0]['titulo'] == 'Noticia antigua'

    # Pertenencia heredada migrada a integrante_equipo
    admin = Cliente(app)
    admin.login('admin@digitalsports.com', 'Admin12345')
    assert [i['nombre'] for i in admin.get('/api/equipos/1').json['integrantes']] == ['Juan Pérez']
    assert admin.get('/api/goles').json['items'][0]['equipo'] == '601'

    # Rol 'profesor' -> 'docente', y estudiante registrado con perfil deportivo
    usuarios = {u['correo']: u for u in admin.get('/api/usuarios').json['items']}
    assert usuarios['carlos@dmc.edu']['rol'] == 'docente'
    assert admin.get('/api/estudiantes?q=Laura').json['total'] == 1

    # Tabla heredada 'posicion' intacta (no se borra información)
    con = sqlite3.connect(ruta)
    assert con.execute('SELECT pts FROM posicion').fetchone()[0] == 27
    con.close()

    # Idempotente: reiniciar la app no vuelve a aplicar ni duplica datos
    app2 = create_app('legacy')
    assert Cliente(app2).get('/api/equipos/1').json['total_integrantes'] == 1
