from backend.extensions import db
from backend.utils.tiempo import ahora, iso


ESTADOS_NOTICIA = ('borrador', 'publicada', 'retirada')


class Noticia(db.Model):
    """
    Modelo NOTICIA
    Noticia deportiva publicada en el portal. La columna 'descripcion' guarda
    el contenido completo (nombre heredado del diseño original).
    Solo las noticias 'publicada' son visibles para estudiantes y visitantes.
    """
    __tablename__ = 'noticia'

    id_noticia = db.Column(db.Integer, primary_key=True, autoincrement=True)
    titulo = db.Column(db.String(200), nullable=False)
    descripcion = db.Column(db.Text, nullable=False)
    imagen = db.Column(db.String(500), nullable=True)
    id_autor = db.Column(db.Integer, db.ForeignKey('usuario.id_usuario'), nullable=True)
    estado = db.Column(db.String(20), nullable=False, default='borrador')
    fecha_creacion = db.Column(db.DateTime, nullable=True, default=ahora)
    fecha_publicacion = db.Column(db.DateTime, nullable=True)
    fecha_actualizacion = db.Column(db.DateTime, nullable=True, default=ahora, onupdate=ahora)

    autor = db.relationship('Usuario', lazy=True)
    comentarios = db.relationship('Comentario', backref='noticia', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Noticia {self.id_noticia}: {self.titulo}>'

    def to_dict(self, resumen=False):
        contenido = self.descripcion or ''
        data = {
            'id_noticia': self.id_noticia,
            'titulo': self.titulo,
            'resumen': contenido if len(contenido) <= 160 else contenido[:157].rstrip() + '...',
            'imagen': self.imagen,
            'id_autor': self.id_autor,
            'autor': self.autor.nombre if self.autor else None,
            'estado': self.estado,
            'fecha_creacion': iso(self.fecha_creacion),
            'fecha_publicacion': iso(self.fecha_publicacion),
            'total_comentarios': sum(1 for c in self.comentarios if c.estado == 'visible'),
        }
        if not resumen:
            data['contenido'] = contenido
            data['descripcion'] = contenido  # compatibilidad
        return data
