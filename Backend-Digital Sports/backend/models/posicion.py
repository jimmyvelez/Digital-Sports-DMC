from backend.extensions import db


class Posicion(db.Model):
    """
    Modelo POSICION (Tabla de Posiciones)
    Representa la posición de un equipo dentro de un torneo.
    Clave compuesta: id_torneo + id_equipo.
    Relaciones:
      - Pertenece a un torneo (FK id_torneo).
      - Pertenece a un equipo (FK id_equipo).
    Campos:
      - pj: Partidos jugados
      - pg: Partidos ganados
      - pe: Partidos empatados
      - pp: Partidos perdidos
      - gf: Goles a favor
      - gc: Goles en contra
      - pts: Puntos
    """
    __tablename__ = 'posicion'

    id_torneo = db.Column(db.Integer, db.ForeignKey('torneo.id_torneo'), primary_key=True)
    id_equipo = db.Column(db.Integer, db.ForeignKey('equipo.id_equipo'), primary_key=True)
    pj = db.Column(db.Integer, nullable=False, default=0)
    pg = db.Column(db.Integer, nullable=False, default=0)
    pe = db.Column(db.Integer, nullable=False, default=0)
    pp = db.Column(db.Integer, nullable=False, default=0)
    gf = db.Column(db.Integer, nullable=False, default=0)
    gc = db.Column(db.Integer, nullable=False, default=0)
    pts = db.Column(db.Integer, nullable=False, default=0)

    def __repr__(self):
        return f'<Posicion Torneo={self.id_torneo} Equipo={self.id_equipo} Pts={self.pts}>'

    def to_dict(self):
        return {
            'id_torneo': self.id_torneo,
            'id_equipo': self.id_equipo,
            'pj': self.pj,
            'pg': self.pg,
            'pe': self.pe,
            'pp': self.pp,
            'gf': self.gf,
            'gc': self.gc,
            'pts': self.pts
        }
