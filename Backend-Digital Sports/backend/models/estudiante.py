from backend.extensions import db
from backend.utils.tiempo import ahora, iso


class Estudiante(db.Model):
    """
    Modelo ESTUDIANTE (perfil deportivo)
    Representa a un jugador. Si el estudiante se registró en la plataforma,
    queda vinculado a su cuenta mediante id_usuario.
    Relaciones:
      - Un estudiante pertenece a equipos mediante integrante_equipo.
      - Un estudiante ANOTA muchos goles.
    Nota: la columna id_equipo es heredada del diseño original. Se conserva
    (ahora opcional) para no perder datos; la pertenencia vigente se consulta
    en integrante_equipo.
    """
    __tablename__ = 'estudiante'

    id_estudiante = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_equipo = db.Column(db.Integer, db.ForeignKey('equipo.id_equipo'), nullable=True)
    id_usuario = db.Column(db.Integer, db.ForeignKey('usuario.id_usuario'), nullable=True, unique=True)
    nombre = db.Column(db.String(100), nullable=False)
    curso = db.Column(db.String(50), nullable=True)

    # Relaciones
    goles = db.relationship('Gol', backref='estudiante', lazy=True)
    membresias = db.relationship('IntegranteEquipo', backref='estudiante', lazy=True)
    usuario = db.relationship('Usuario', backref=db.backref('perfil_estudiante', uselist=False), lazy=True)

    def __repr__(self):
        return f'<Estudiante {self.id_estudiante}: {self.nombre}>'

    def equipos_activos(self):
        return [m.equipo for m in self.membresias if m.activo]

    def to_dict(self, con_equipos=False):
        data = {
            'id_estudiante': self.id_estudiante,
            'id_usuario': self.id_usuario,
            'nombre': self.nombre,
            'curso': self.curso,
            'tiene_cuenta': self.id_usuario is not None,
        }
        if con_equipos:
            data['equipos'] = [
                {'id_equipo': e.id_equipo, 'nombre': e.nombre, 'id_torneo': e.id_torneo,
                 'torneo': e.torneo.nombre if e.torneo else None}
                for e in self.equipos_activos()
            ]
        return data


class IntegranteEquipo(db.Model):
    """
    Modelo INTEGRANTE_EQUIPO
    Pertenencia de un estudiante a un equipo, con historial de altas y bajas.
    Un registro activo = el estudiante forma parte de la plantilla actual.
    """
    __tablename__ = 'integrante_equipo'
    __table_args__ = (
        db.Index('ix_integrante_equipo_estudiante', 'id_equipo', 'id_estudiante'),
    )

    id_integrante = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_equipo = db.Column(db.Integer, db.ForeignKey('equipo.id_equipo'), nullable=False)
    id_estudiante = db.Column(db.Integer, db.ForeignKey('estudiante.id_estudiante'), nullable=False)
    dorsal = db.Column(db.Integer, nullable=True)
    activo = db.Column(db.Boolean, nullable=False, default=True)
    fecha_alta = db.Column(db.DateTime, nullable=False, default=ahora)
    fecha_baja = db.Column(db.DateTime, nullable=True)

    def to_dict(self):
        return {
            'id_integrante': self.id_integrante,
            'id_equipo': self.id_equipo,
            'id_estudiante': self.id_estudiante,
            'nombre': self.estudiante.nombre if self.estudiante else None,
            'curso': self.estudiante.curso if self.estudiante else None,
            'tiene_cuenta': bool(self.estudiante and self.estudiante.id_usuario),
            'dorsal': self.dorsal,
            'activo': bool(self.activo),
            'fecha_alta': iso(self.fecha_alta),
            'fecha_baja': iso(self.fecha_baja),
        }
