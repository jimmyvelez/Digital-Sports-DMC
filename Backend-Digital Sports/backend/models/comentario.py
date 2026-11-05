from backend.extensions import db
from backend.utils.tiempo import ahora, iso


ESTADOS_COMENTARIO = ('visible', 'oculto')

MOTIVOS_REPORTE = {
    'ofensivo': 'Lenguaje ofensivo o inapropiado',
    'spam': 'Spam o publicidad no deseada',
    'acoso': 'Acoso, intimidación o amenazas',
    'falso': 'Información falsa o engañosa',
    'otro': 'Otro motivo',
}


class Comentario(db.Model):
    """
    Modelo COMENTARIO
    Comentario de un usuario sobre una noticia publicada.
    'reportes' cuenta los reportes activos; el admin puede moderarlo.
    """
    __tablename__ = 'comentario'

    id_comentario = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_noticia = db.Column(db.Integer, db.ForeignKey('noticia.id_noticia'), nullable=False, index=True)
    id_usuario = db.Column(db.Integer, db.ForeignKey('usuario.id_usuario'), nullable=False)
    contenido = db.Column(db.Text, nullable=False)
    estado = db.Column(db.String(20), nullable=False, default='visible')
    reportes = db.Column(db.Integer, nullable=False, default=0)
    fecha_creacion = db.Column(db.DateTime, nullable=False, default=ahora)
    fecha_edicion = db.Column(db.DateTime, nullable=True)

    usuario = db.relationship('Usuario', lazy=True)
    registros_reporte = db.relationship('ReporteComentario', backref='comentario', lazy=True,
                                        cascade='all, delete-orphan',
                                        order_by='ReporteComentario.fecha.desc()')

    def to_dict(self, con_reportes=False):
        ultimo_rep = self.registros_reporte[0] if self.registros_reporte else None
        data = {
            'id_comentario': self.id_comentario,
            'id_noticia': self.id_noticia,
            'noticia': self.noticia.titulo if self.noticia else None,
            'id_usuario': self.id_usuario,
            'autor': self.usuario.nombre if self.usuario else None,
            'correo_autor': self.usuario.correo if self.usuario else None,
            'rol_autor': self.usuario.rol if self.usuario else None,
            'contenido': self.contenido,
            'estado': self.estado,
            'reportes': self.reportes,
            'ultimo_motivo': ultimo_rep.motivo_texto if ultimo_rep else None,
            'fecha_ultimo_reporte': iso(ultimo_rep.fecha) if ultimo_rep else None,
            'fecha_creacion': iso(self.fecha_creacion),
            'fecha_edicion': iso(self.fecha_edicion),
        }
        if con_reportes:
            data['historial_reportes'] = [r.to_dict() for r in self.registros_reporte]
        return data


class ReporteComentario(db.Model):
    """Registro histórico de qué usuario reportó un comentario, motivo y fecha."""
    __tablename__ = 'reporte_comentario'
    __table_args__ = (db.UniqueConstraint('id_comentario', 'id_usuario', name='uq_reporte_comentario_usuario'),)

    id_reporte = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_comentario = db.Column(db.Integer, db.ForeignKey('comentario.id_comentario'), nullable=False)
    id_usuario = db.Column(db.Integer, db.ForeignKey('usuario.id_usuario'), nullable=False)
    motivo = db.Column(db.String(50), nullable=False, default='ofensivo')
    detalles = db.Column(db.String(500), nullable=True)
    fecha = db.Column(db.DateTime, nullable=False, default=ahora)

    usuario = db.relationship('Usuario', lazy=True)

    @property
    def motivo_texto(self):
        return MOTIVOS_REPORTE.get(self.motivo, self.motivo or 'Inapropiado')

    def to_dict(self):
        return {
            'id_reporte': self.id_reporte,
            'id_comentario': self.id_comentario,
            'id_usuario': self.id_usuario,
            'reportante': self.usuario.nombre if self.usuario else 'Usuario',
            'correo_reportante': self.usuario.correo if self.usuario else None,
            'motivo': self.motivo,
            'motivo_texto': self.motivo_texto,
            'detalles': self.detalles,
            'fecha': iso(self.fecha),
        }
