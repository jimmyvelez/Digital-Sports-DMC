import json

from backend.extensions import db
from backend.utils.tiempo import ahora, iso


class Auditoria(db.Model):
    """
    Modelo AUDITORIA
    Historial de cambios importantes (quién, qué, cuándo).
    """
    __tablename__ = 'auditoria'

    id_auditoria = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_usuario = db.Column(db.Integer, db.ForeignKey('usuario.id_usuario'), nullable=True)
    accion = db.Column(db.String(50), nullable=False)
    entidad = db.Column(db.String(50), nullable=False)
    id_entidad = db.Column(db.Integer, nullable=True)
    detalle = db.Column(db.Text, nullable=True)
    fecha = db.Column(db.DateTime, nullable=False, default=ahora, index=True)

    usuario = db.relationship('Usuario', lazy=True)

    def to_dict(self):
        try:
            detalle = json.loads(self.detalle) if self.detalle else None
        except ValueError:
            detalle = self.detalle
        return {
            'id_auditoria': self.id_auditoria,
            'id_usuario': self.id_usuario,
            'usuario': self.usuario.nombre if self.usuario else 'Sistema',
            'accion': self.accion,
            'entidad': self.entidad,
            'id_entidad': self.id_entidad,
            'detalle': detalle,
            'fecha': iso(self.fecha),
        }


class SchemaVersion(db.Model):
    """Migraciones de esquema/datos aplicadas (ver backend/migraciones.py)."""
    __tablename__ = 'schema_version'

    version = db.Column(db.Integer, primary_key=True, autoincrement=False)
    descripcion = db.Column(db.String(200), nullable=False)
    fecha_aplicada = db.Column(db.DateTime, nullable=False, default=ahora)
