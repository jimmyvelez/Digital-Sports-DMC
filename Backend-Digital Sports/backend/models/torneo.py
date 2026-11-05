from backend.extensions import db
from backend.utils.tiempo import iso


ESTADOS_TORNEO = ('planificacion', 'activo', 'finalizado')
SISTEMAS_COMPETICION = ('liga', 'eliminacion', 'grupos_eliminacion')
# Criterios de desempate disponibles para la tabla de posiciones
CRITERIOS_DESEMPATE = ('pts', 'dg', 'gf', 'pg', 'gc_menor')
CRITERIOS_POR_DEFECTO = 'pts,dg,gf'


class Torneo(db.Model):
    """
    Modelo TORNEO
    Representa un torneo deportivo (p. ej. Masculino Sección A, Femenino, Interroscas).
    Relaciones:
      - Un torneo INCLUYE muchos equipos.
      - Un torneo PROGRAMA muchos partidos.
    La puntuación y los criterios de desempate son configurables por torneo.
    """
    __tablename__ = 'torneo'

    id_torneo = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nombre = db.Column(db.String(100), nullable=False)
    categoria = db.Column(db.String(50), nullable=False)
    descripcion = db.Column(db.Text, nullable=True)
    fecha_inicio = db.Column(db.Date, nullable=True)
    fecha_fin = db.Column(db.Date, nullable=True)
    sistema_competicion = db.Column(db.String(30), nullable=False, default='liga')
    estado = db.Column(db.String(20), nullable=False, default='planificacion')
    puntos_victoria = db.Column(db.Integer, nullable=False, default=3)
    puntos_empate = db.Column(db.Integer, nullable=False, default=1)
    puntos_derrota = db.Column(db.Integer, nullable=False, default=0)
    criterios_desempate = db.Column(db.String(100), nullable=False, default=CRITERIOS_POR_DEFECTO)

    # Relaciones
    equipos = db.relationship('Equipo', backref='torneo', lazy=True)
    partidos = db.relationship('Partido', backref='torneo', lazy=True)
    posiciones = db.relationship('Posicion', backref='torneo', lazy=True)

    def __repr__(self):
        return f'<Torneo {self.id_torneo}: {self.nombre}>'

    def lista_criterios(self):
        criterios = [c.strip() for c in (self.criterios_desempate or CRITERIOS_POR_DEFECTO).split(',')]
        return [c for c in criterios if c in CRITERIOS_DESEMPATE] or CRITERIOS_POR_DEFECTO.split(',')

    def to_dict(self, con_conteos=False):
        data = {
            'id_torneo': self.id_torneo,
            'nombre': self.nombre,
            'categoria': self.categoria,
            'descripcion': self.descripcion,
            'fecha_inicio': iso(self.fecha_inicio),
            'fecha_fin': iso(self.fecha_fin),
            'sistema_competicion': self.sistema_competicion,
            'estado': self.estado,
            'puntos_victoria': self.puntos_victoria,
            'puntos_empate': self.puntos_empate,
            'puntos_derrota': self.puntos_derrota,
            'criterios_desempate': self.lista_criterios(),
        }
        if con_conteos:
            data['total_equipos'] = sum(1 for e in self.equipos if e.estado == 'activo')
            data['total_partidos'] = len(self.partidos)
        return data
