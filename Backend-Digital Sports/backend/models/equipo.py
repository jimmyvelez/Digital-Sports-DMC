from backend.extensions import db
from backend.utils.tiempo import ahora, iso


class Equipo(db.Model):
    """
    Modelo EQUIPO
    Representa un equipo dentro de un torneo.
    Relaciones:
      - Un equipo pertenece a un torneo (FK id_torneo).
      - Un equipo tiene un docente responsable (FK id_docente -> usuario).
      - Un equipo INTEGRA muchos estudiantes (tabla integrante_equipo).
      - Un equipo JUEGA partidos como local o visitante.
    """
    __tablename__ = 'equipo'

    id_equipo = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_torneo = db.Column(db.Integer, db.ForeignKey('torneo.id_torneo'), nullable=False)
    nombre = db.Column(db.String(100), nullable=False)
    curso = db.Column(db.String(50), nullable=False)
    categoria = db.Column(db.String(50), nullable=False)
    descripcion = db.Column(db.Text, nullable=True)
    escudo = db.Column(db.String(500), nullable=True)
    estado = db.Column(db.String(20), nullable=False, default='activo')
    id_docente = db.Column(db.Integer, db.ForeignKey('usuario.id_usuario'), nullable=True)
    fecha_creacion = db.Column(db.DateTime, nullable=True, default=ahora)

    # Relaciones
    # Columna heredada estudiante.id_equipo: se conserva por compatibilidad,
    # la pertenencia oficial vive en integrante_equipo.
    estudiantes = db.relationship('Estudiante', backref='equipo_legacy', lazy=True)
    integrantes = db.relationship('IntegranteEquipo', backref='equipo', lazy=True,
                                  cascade='all, delete-orphan')
    partidos_local = db.relationship('Partido', foreign_keys='Partido.id_equipo_local', backref='equipo_local', lazy=True)
    partidos_visitante = db.relationship('Partido', foreign_keys='Partido.id_equipo_visitante', backref='equipo_visitante', lazy=True)
    posiciones = db.relationship('Posicion', backref='equipo', lazy=True)
    docente = db.relationship('Usuario', foreign_keys=[id_docente], lazy=True)

    def __repr__(self):
        return f'<Equipo {self.id_equipo}: {self.nombre}>'

    def integrantes_activos(self):
        return [i for i in self.integrantes if i.activo]

    def to_dict(self, con_integrantes=False):
        data = {
            'id_equipo': self.id_equipo,
            'id_torneo': self.id_torneo,
            'torneo': self.torneo.nombre if self.torneo else None,
            'nombre': self.nombre,
            'curso': self.curso,
            'categoria': self.categoria,
            'descripcion': self.descripcion,
            'escudo': self.escudo,
            'estado': self.estado,
            'id_docente': self.id_docente,
            'docente': self.docente.nombre if self.docente else None,
            'total_integrantes': len(self.integrantes_activos()),
            'fecha_creacion': iso(self.fecha_creacion),
        }
        if con_integrantes:
            data['integrantes'] = [i.to_dict() for i in self.integrantes_activos()]
        return data
