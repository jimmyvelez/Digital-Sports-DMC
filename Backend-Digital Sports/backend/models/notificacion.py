from backend.extensions import db
from backend.utils.tiempo import ahora, iso


TIPOS_NOTIFICACION = (
    'partido_nuevo', 'cambio_horario', 'cambio_lugar', 'cambio_estado', 'resultado',
    'reporte_comentario', 'general'
)


class Notificacion(db.Model):
    """
    Modelo NOTIFICACION
    Aviso persistente dirigido a un usuario. Se genera en el backend cuando
    ocurre un evento real (partido de su equipo, reporte de comentario para admin, etc.).
    """
    __tablename__ = 'notificacion'
    __table_args__ = (db.Index('ix_notificacion_usuario_leida', 'id_usuario', 'leida'),)

    id_notificacion = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_usuario = db.Column(db.Integer, db.ForeignKey('usuario.id_usuario'), nullable=False)
    titulo = db.Column(db.String(150), nullable=False)
    mensaje = db.Column(db.Text, nullable=False)
    tipo = db.Column(db.String(30), nullable=False, default='general')
    id_partido = db.Column(db.Integer, db.ForeignKey('partido.id_partido'), nullable=True)
    id_comentario = db.Column(db.Integer, db.ForeignKey('comentario.id_comentario', ondelete='CASCADE'), nullable=True)
    leida = db.Column(db.Boolean, nullable=False, default=False)
    fecha_creacion = db.Column(db.DateTime, nullable=False, default=ahora)
    fecha_lectura = db.Column(db.DateTime, nullable=True)

    comentario = db.relationship('Comentario', lazy=True)

    def to_dict(self):
        return {
            'id_notificacion': self.id_notificacion,
            'titulo': self.titulo,
            'mensaje': self.mensaje,
            'tipo': self.tipo,
            'id_partido': self.id_partido,
            'id_comentario': self.id_comentario,
            'id_noticia': self.comentario.id_noticia if self.comentario else None,
            'leida': bool(self.leida),
            'fecha_creacion': iso(self.fecha_creacion),
            'fecha_lectura': iso(self.fecha_lectura),
        }
