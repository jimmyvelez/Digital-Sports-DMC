from backend.extensions import db
from backend.utils.tiempo import ahora, iso


TIPOS_FALTA = ('tarjeta_amarilla', 'tarjeta_roja', 'conducta_antideportiva', 'agresion', 'inasistencia', 'otra')
ESTADOS_FALTA = ('registrada', 'en_revision', 'cerrada', 'anulada')


class Falta(db.Model):
    """
    Modelo FALTA
    Falta o incidencia disciplinaria ocurrida en un partido. No genera
    sanciones automáticas ni afecta la tabla de posiciones.
    """
    __tablename__ = 'falta'

    id_falta = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_partido = db.Column(db.Integer, db.ForeignKey('partido.id_partido'), nullable=False, index=True)
    id_equipo = db.Column(db.Integer, db.ForeignKey('equipo.id_equipo'), nullable=False)
    id_estudiante = db.Column(db.Integer, db.ForeignKey('estudiante.id_estudiante'), nullable=True)
    id_docente = db.Column(db.Integer, db.ForeignKey('usuario.id_usuario'), nullable=False)
    tipo = db.Column(db.String(40), nullable=False)
    descripcion = db.Column(db.Text, nullable=True)
    minuto = db.Column(db.Integer, nullable=True)
    fecha = db.Column(db.DateTime, nullable=False, default=ahora)
    estado = db.Column(db.String(20), nullable=False, default='registrada')
    fecha_actualizacion = db.Column(db.DateTime, nullable=True, default=ahora, onupdate=ahora)

    partido = db.relationship('Partido', lazy=True)
    equipo = db.relationship('Equipo', lazy=True)
    estudiante = db.relationship('Estudiante', lazy=True)
    docente = db.relationship('Usuario', lazy=True)

    def to_dict(self):
        p = self.partido
        return {
            'id_falta': self.id_falta,
            'id_partido': self.id_partido,
            'partido': (f'{p.equipo_local.nombre} vs {p.equipo_visitante.nombre}' if p else None),
            'fecha_partido': iso(p.fecha) if p else None,
            'id_equipo': self.id_equipo,
            'equipo': self.equipo.nombre if self.equipo else None,
            'id_estudiante': self.id_estudiante,
            'estudiante': self.estudiante.nombre if self.estudiante else None,
            'id_docente': self.id_docente,
            'docente': self.docente.nombre if self.docente else None,
            'tipo': self.tipo,
            'descripcion': self.descripcion,
            'minuto': self.minuto,
            'fecha': iso(self.fecha),
            'estado': self.estado,
        }
