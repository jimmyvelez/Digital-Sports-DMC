from backend.extensions import db
from backend.utils.tiempo import ahora, iso


class Gol(db.Model):
    """
    Modelo GOL
    Representa un gol anotado por un estudiante en un partido (estadística de goleadores).
    El resultado oficial del partido se registra en partido.goles_local/goles_visitante.
    Relaciones:
      - Un gol pertenece a un partido (FK id_partido).
      - Un gol es anotado por un estudiante (FK id_estudiante).
      - Un gol se atribuye a un equipo (FK id_equipo).
    """
    __tablename__ = 'gol'

    id_gol = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_partido = db.Column(db.Integer, db.ForeignKey('partido.id_partido'), nullable=False)
    id_estudiante = db.Column(db.Integer, db.ForeignKey('estudiante.id_estudiante'), nullable=False)
    id_equipo = db.Column(db.Integer, db.ForeignKey('equipo.id_equipo'), nullable=True)
    minuto = db.Column(db.Integer, nullable=True)
    fecha = db.Column(db.DateTime, nullable=False, default=ahora)

    equipo = db.relationship('Equipo', lazy=True)

    def __repr__(self):
        return f'<Gol {self.id_gol}: Partido {self.id_partido}, Estudiante {self.id_estudiante}>'

    def to_dict(self):
        p = self.partido
        return {
            'id_gol': self.id_gol,
            'id_partido': self.id_partido,
            'partido': (f'{p.equipo_local.nombre} vs {p.equipo_visitante.nombre}' if p else None),
            'fecha_partido': iso(p.fecha) if p else None,
            'id_estudiante': self.id_estudiante,
            'estudiante': self.estudiante.nombre if self.estudiante else None,
            'id_equipo': self.id_equipo,
            'equipo': self.equipo.nombre if self.equipo else None,
            'minuto': self.minuto,
            'fecha': iso(self.fecha),
        }
