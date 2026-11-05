from backend.extensions import db


class Docente(db.Model):
    """
    Modelo DOCENTE
    Representa un docente que arbitra partidos.
    Relaciones:
      - Un docente ARBITRA muchos partidos.
    """
    __tablename__ = 'docente'

    id_docente = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nombre = db.Column(db.String(100), nullable=False)

    # Relaciones
    partidos = db.relationship('Partido', backref='docente', lazy=True)

    def __repr__(self):
        return f'<Docente {self.id_docente}: {self.nombre}>'

    def to_dict(self):
        return {
            'id_docente': self.id_docente,
            'nombre': self.nombre
        }
