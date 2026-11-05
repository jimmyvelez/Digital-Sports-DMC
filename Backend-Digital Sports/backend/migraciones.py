"""
Migraciones de esquema y datos — Digital Sports DMC
====================================================

El proyecto usa db.create_all() (decisión original: sin Flask-Migrate).
create_all() crea tablas NUEVAS pero no agrega columnas a tablas existentes,
por eso este módulo:

  1. Agrega las columnas nuevas a las tablas que ya existían (ALTER TABLE ADD COLUMN).
  2. Ajusta restricciones compatibles (p. ej. estudiante.id_equipo pasa a ser opcional).
  3. Transforma datos heredados SIN borrar información.

Cada migración tiene un número de versión y se registra en la tabla
schema_version; todas son idempotentes (se pueden ejecutar varias veces).
Se ejecutan al iniciar el servidor y también con:  flask --app run.py migrar
"""
import re

from sqlalchemy import inspect, text

from backend.extensions import db
from backend.utils.tiempo import ahora

# (tabla, columna, DDL portable MySQL/SQLite)
COLUMNAS_NUEVAS = [
    ('usuario', 'activo', 'BOOLEAN NOT NULL DEFAULT 1'),
    ('usuario', 'foto_perfil', 'VARCHAR(500) NULL'),
    ('usuario', 'google_id', 'VARCHAR(128) NULL'),
    ('usuario', 'fecha_creacion', 'DATETIME NULL'),
    ('usuario', 'ultimo_acceso', 'DATETIME NULL'),

    ('torneo', 'descripcion', 'TEXT NULL'),
    ('torneo', 'fecha_inicio', 'DATE NULL'),
    ('torneo', 'fecha_fin', 'DATE NULL'),
    ('torneo', 'sistema_competicion', "VARCHAR(30) NOT NULL DEFAULT 'liga'"),
    ('torneo', 'estado', "VARCHAR(20) NOT NULL DEFAULT 'activo'"),
    ('torneo', 'puntos_victoria', 'INTEGER NOT NULL DEFAULT 3'),
    ('torneo', 'puntos_empate', 'INTEGER NOT NULL DEFAULT 1'),
    ('torneo', 'puntos_derrota', 'INTEGER NOT NULL DEFAULT 0'),
    ('torneo', 'criterios_desempate', "VARCHAR(100) NOT NULL DEFAULT 'pts,dg,gf'"),

    ('equipo', 'descripcion', 'TEXT NULL'),
    ('equipo', 'escudo', 'VARCHAR(500) NULL'),
    ('equipo', 'estado', "VARCHAR(20) NOT NULL DEFAULT 'activo'"),
    ('equipo', 'id_docente', 'INTEGER NULL'),
    ('equipo', 'fecha_creacion', 'DATETIME NULL'),

    ('estudiante', 'id_usuario', 'INTEGER NULL'),
    ('estudiante', 'curso', 'VARCHAR(50) NULL'),

    ('partido', 'id_docente', 'INTEGER NULL'),
    ('partido', 'lugar', 'VARCHAR(150) NULL'),
    ('partido', 'goles_local', 'INTEGER NULL'),
    ('partido', 'goles_visitante', 'INTEGER NULL'),
    ('partido', 'observaciones', 'TEXT NULL'),
    ('partido', 'fecha_creacion', 'DATETIME NULL'),
    ('partido', 'fecha_actualizacion', 'DATETIME NULL'),

    # Las noticias existentes ya estaban visibles: quedan como 'publicada'.
    ('noticia', 'id_autor', 'INTEGER NULL'),
    ('noticia', 'estado', "VARCHAR(20) NOT NULL DEFAULT 'publicada'"),
    ('noticia', 'fecha_creacion', 'DATETIME NULL'),
    ('noticia', 'fecha_publicacion', 'DATETIME NULL'),
    ('noticia', 'fecha_actualizacion', 'DATETIME NULL'),

    ('gol', 'id_equipo', 'INTEGER NULL'),
    ('gol', 'minuto', 'INTEGER NULL'),

    ('reporte_comentario', 'motivo', "VARCHAR(50) NOT NULL DEFAULT 'ofensivo'"),
    ('reporte_comentario', 'detalles', 'VARCHAR(500) NULL'),

    ('notificacion', 'id_comentario', 'INTEGER NULL'),
]

# Claves foráneas para las columnas agregadas (solo MySQL: SQLite no permite
# agregarlas a una tabla existente; en SQLite las crea create_all en BD nuevas).
CLAVES_FORANEAS = [
    ('equipo', 'id_docente', 'usuario', 'id_usuario', 'fk_equipo_docente'),
    ('estudiante', 'id_usuario', 'usuario', 'id_usuario', 'fk_estudiante_usuario'),
    ('noticia', 'id_autor', 'usuario', 'id_usuario', 'fk_noticia_autor'),
    ('gol', 'id_equipo', 'equipo', 'id_equipo', 'fk_gol_equipo'),
    ('notificacion', 'id_comentario', 'comentario', 'id_comentario', 'fk_notificacion_comentario'),
]

ESTADOS_HEREDADOS = {
    'jugado': 'finalizado', 'finalizado': 'finalizado', 'terminado': 'finalizado',
    'proximo': 'programado', 'próximo': 'programado', 'pendiente': 'programado', 'programado': 'programado',
    'en juego': 'en_juego', 'en_juego': 'en_juego', 'jugando': 'en_juego',
    'cancelado': 'cancelado', 'suspendido': 'suspendido', 'aplazado': 'suspendido',
}


def _columnas(tabla):
    return {c['name'] for c in inspect(db.engine).get_columns(tabla)}


def _tablas():
    return set(inspect(db.engine).get_table_names())


def _es_mysql():
    return db.engine.dialect.name == 'mysql'


def _sqlite_estudiante_id_equipo_opcional():
    """
    SQLite no permite quitar un NOT NULL con ALTER TABLE: se reconstruye la
    tabla estudiante copiando TODAS sus filas (procedimiento oficial de SQLite).
    """
    columnas = {c['name']: c for c in inspect(db.engine).get_columns('estudiante')}
    if columnas.get('id_equipo', {}).get('nullable', True):
        return
    from backend.models import Estudiante
    nombres = ', '.join(columnas)
    with db.engine.begin() as conn:
        conn.execute(text('PRAGMA foreign_keys=OFF'))
        conn.execute(text('ALTER TABLE estudiante RENAME TO estudiante_migracion'))
        Estudiante.__table__.create(conn)
        conn.execute(text(f'INSERT INTO estudiante ({nombres}) SELECT {nombres} FROM estudiante_migracion'))
        conn.execute(text('DROP TABLE estudiante_migracion'))
        conn.execute(text('PRAGMA foreign_keys=ON'))
    print('  [MIGRACIÓN] estudiante.id_equipo ahora es opcional (tabla reconstruida con sus datos).')


# -----------------------------------------------------------------------------
# Migración 1: columnas nuevas y restricciones
# -----------------------------------------------------------------------------
def _m1_esquema():
    tablas = _tablas()
    with db.engine.begin() as conn:
        for tabla, columna, ddl in COLUMNAS_NUEVAS:
            if tabla in tablas and columna not in _columnas(tabla):
                conn.execute(text(f'ALTER TABLE {tabla} ADD COLUMN {columna} {ddl}'))
                print(f'  [MIGRACIÓN] Columna agregada: {tabla}.{columna}')

    if db.engine.dialect.name == 'sqlite':
        _sqlite_estudiante_id_equipo_opcional()

    if _es_mysql():
        with db.engine.begin() as conn:
            # estudiante.id_equipo pasa a ser opcional (la pertenencia vive en integrante_equipo)
            info = conn.execute(text("SHOW COLUMNS FROM estudiante LIKE 'id_equipo'")).fetchone()
            if info and str(info[2]).upper() == 'NO':
                conn.execute(text('ALTER TABLE estudiante MODIFY id_equipo INT NULL'))
            # partido.marcador sin valor por defecto '0-0' (un partido sin jugar no tiene marcador)
            conn.execute(text('ALTER TABLE partido MODIFY marcador VARCHAR(20) NULL DEFAULT NULL'))

            existentes = {r[0] for r in conn.execute(text(
                'SELECT CONSTRAINT_NAME FROM information_schema.TABLE_CONSTRAINTS '
                "WHERE CONSTRAINT_SCHEMA = DATABASE() AND CONSTRAINT_TYPE = 'FOREIGN KEY'"))}
            for tabla, col, ref_tabla, ref_col, nombre in CLAVES_FORANEAS:
                if nombre not in existentes:
                    conn.execute(text(f'ALTER TABLE {tabla} ADD CONSTRAINT {nombre} '
                                      f'FOREIGN KEY ({col}) REFERENCES {ref_tabla}({ref_col})'))

        indices = {i['name'] for i in inspect(db.engine).get_indexes('estudiante')}
        if 'ux_estudiante_usuario' not in indices and not any(
                u['column_names'] == ['id_usuario'] for u in inspect(db.engine).get_unique_constraints('estudiante')):
            with db.engine.begin() as conn:
                conn.execute(text('CREATE UNIQUE INDEX ux_estudiante_usuario ON estudiante (id_usuario)'))


# -----------------------------------------------------------------------------
# Migración 2: normalización de datos heredados (sin borrar nada)
# -----------------------------------------------------------------------------
def _parsear_marcador(marcador):
    m = re.match(r'^\s*(\d{1,2})\s*[-–—:]\s*(\d{1,2})\s*$', marcador or '')
    return (int(m.group(1)), int(m.group(2))) if m else None


def _m2_datos():
    from backend.models import Equipo, Estudiante, Gol, IntegranteEquipo, Noticia, Partido, Usuario

    # Roles: 'profesor' -> 'docente'
    Usuario.query.filter(Usuario.rol.in_(('profesor', 'Profesor', 'Docente'))).update(
        {'rol': 'docente'}, synchronize_session=False)
    Usuario.query.filter(Usuario.rol == 'Admin').update({'rol': 'admin'}, synchronize_session=False)
    Usuario.query.filter(Usuario.fecha_creacion.is_(None)).update({'fecha_creacion': ahora()},
                                                                  synchronize_session=False)

    # Partidos: estados normalizados y marcador de texto -> goles numéricos
    for p in Partido.query.all():
        estado = ESTADOS_HEREDADOS.get((p.estado or '').strip().lower(), 'programado')
        if p.goles_local is None and estado in ('finalizado', 'en_juego'):
            goles = _parsear_marcador(p.marcador)
            if goles:
                p.goles_local, p.goles_visitante = goles
                p.sincronizar_marcador()
        if estado == 'finalizado' and p.goles_local is None:
            # Sin marcador legible no puede contarse en la clasificación
            estado = 'programado'
            p.observaciones = ((p.observaciones or '') + ' [Migración: estado "finalizado" sin marcador '
                               f'válido ("{p.marcador}"), revisar resultado.]').strip()
        if estado == 'programado' and p.goles_local is None:
            p.marcador = None
        p.estado = estado
        if p.fecha_creacion is None:
            p.fecha_creacion = p.fecha or ahora()

    # Noticias existentes: se consideran publicadas en su fecha de creación
    for n in Noticia.query.filter(Noticia.fecha_publicacion.is_(None)).all():
        n.fecha_creacion = n.fecha_creacion or ahora()
        if n.estado == 'publicada':
            n.fecha_publicacion = n.fecha_creacion

    # Pertenencia heredada estudiante.id_equipo -> integrante_equipo
    for est in Estudiante.query.filter(Estudiante.id_equipo.isnot(None)).all():
        existe = IntegranteEquipo.query.filter_by(id_equipo=est.id_equipo, id_estudiante=est.id_estudiante).first()
        if not existe:
            db.session.add(IntegranteEquipo(id_equipo=est.id_equipo, id_estudiante=est.id_estudiante, activo=True))

    # Goles heredados: equipo del goleador
    for gol in Gol.query.filter(Gol.id_equipo.is_(None)).all():
        est = gol.estudiante
        partido = gol.partido
        if est and partido:
            candidatos = {partido.id_equipo_local, partido.id_equipo_visitante}
            if est.id_equipo in candidatos:
                gol.id_equipo = est.id_equipo
            else:
                m = IntegranteEquipo.query.filter(IntegranteEquipo.id_estudiante == est.id_estudiante,
                                                  IntegranteEquipo.id_equipo.in_(candidatos)).first()
                gol.id_equipo = m.id_equipo if m else None

    # Equipos sin fecha de creación
    Equipo.query.filter(Equipo.fecha_creacion.is_(None)).update({'fecha_creacion': ahora()},
                                                                 synchronize_session=False)
    db.session.commit()


# -----------------------------------------------------------------------------
# Migración 3: perfiles deportivos para estudiantes registrados sin perfil
# -----------------------------------------------------------------------------
def _m3_perfiles():
    from backend.models import Estudiante, Usuario
    for u in Usuario.query.filter(Usuario.rol == 'estudiante').all():
        if not Estudiante.query.filter_by(id_usuario=u.id_usuario).first():
            db.session.add(Estudiante(nombre=u.nombre, id_usuario=u.id_usuario))
    db.session.commit()


# -----------------------------------------------------------------------------
# Migración 4: índice UNIQUE para google_id (si existe la columna)
# -----------------------------------------------------------------------------
def _m4_google_id_index():
    tablas = _tablas()
    if 'usuario' not in tablas:
        return
    if 'google_id' not in _columnas('usuario'):
        return
    if _es_mysql():
        with db.engine.begin() as conn:
            existe = conn.execute(text(
                "SELECT INDEX_NAME FROM information_schema.STATISTICS "
                "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'usuario' "
                "AND INDEX_NAME = 'ux_usuario_google_id'"
            )).fetchone()
            if not existe:
                conn.execute(text(
                    'CREATE UNIQUE INDEX ux_usuario_google_id ON usuario (google_id)'
                ))
                print('  [MIGRACIÓN] Índice UNIQUE creado: usuario.google_id')
    else:
        indices = {i['name'] for i in inspect(db.engine).get_indexes('usuario')}
        if 'ux_usuario_google_id' not in indices:
            with db.engine.begin() as conn:
                conn.execute(text(
                    'CREATE UNIQUE INDEX IF NOT EXISTS ux_usuario_google_id ON usuario (google_id)'
                ))


# -----------------------------------------------------------------------------
# Migración 5: columnas de reportes y notificaciones de moderación
# -----------------------------------------------------------------------------
def _m5_reportes_notificaciones():
    _m1_esquema()


MIGRACIONES = [
    (1, 'Columnas nuevas y restricciones', _m1_esquema),
    (2, 'Normalización de datos heredados', _m2_datos),
    (3, 'Perfiles deportivos de estudiantes', _m3_perfiles),
    (4, 'Índice único google_id en usuario', _m4_google_id_index),
    (5, 'Reportes detallados y notificaciones de moderación', _m5_reportes_notificaciones),
]


def ejecutar_migraciones():
    """Aplica en orden las migraciones pendientes."""
    from backend.models import SchemaVersion
    aplicadas = {v.version for v in SchemaVersion.query.all()}
    for version, descripcion, funcion in MIGRACIONES:
        if version in aplicadas:
            continue
        funcion()
        db.session.add(SchemaVersion(version=version, descripcion=descripcion))
        db.session.commit()
        print(f'  [MIGRACIÓN] v{version} aplicada: {descripcion}')
