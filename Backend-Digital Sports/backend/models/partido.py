from backend.extensions import db
from backend.utils.tiempo import ahora, iso


ESTADOS_PARTIDO = ('programado', 'en_juego', 'finalizado', 'suspendido', 'cancelado')

# Transiciones de estado permitidas. Un resultado finalizado puede corregirse
# sin cambiar de estado; anularlo (-> cancelado) solo lo puede hacer un admin.
TRANSICIONES_PARTIDO = {
    'programado': {'en_juego', 'finalizado', 'suspendido', 'cancelado'},
    'en_juego': {'finalizado', 'suspendido'},
    'suspendido': {'programado', 'cancelado'},
    'finalizado': {'cancelado'},
    'cancelado': set(),
}


class Partido(db.Model):
    """
    Modelo PARTIDO
    Representa un partido entre dos equipos dentro de un torneo.
    Relaciones:
      - Un partido pertenece a un torneo (FK id_torneo).
      - Un partido tiene un equipo local y uno visitante.
      - Un partido tiene un docente responsable (FK id_usuario -> usuario).
      - Un partido REGISTRA muchos goles y faltas.
    El resultado oficial está en goles_local / goles_visitante. La columna
    marcador (texto "L-V") se mantiene sincronizada por compatibilidad.
    """
    __tablename__ = 'partido'

    id_partido = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_torneo = db.Column(db.Integer, db.ForeignKey('torneo.id_torneo'), nullable=False)
    id_equipo_local = db.Column(db.Integer, db.ForeignKey('equipo.id_equipo'), nullable=False)
    id_equipo_visitante = db.Column(db.Integer, db.ForeignKey('equipo.id_equipo'), nullable=False)
    id_usuario = db.Column(db.Integer, db.ForeignKey('usuario.id_usuario'), nullable=True)
    id_docente = db.Column(db.Integer, db.ForeignKey('docente.id_docente'), nullable=True)  # heredado
    fecha = db.Column(db.DateTime, nullable=False)
    lugar = db.Column(db.String(150), nullable=True)
    estado = db.Column(db.String(30), nullable=False, default='programado')
    marcador = db.Column(db.String(20), nullable=True)
    goles_local = db.Column(db.Integer, nullable=True)
    goles_visitante = db.Column(db.Integer, nullable=True)
    observaciones = db.Column(db.Text, nullable=True)
    fecha_creacion = db.Column(db.DateTime, nullable=True, default=ahora)
    fecha_actualizacion = db.Column(db.DateTime, nullable=True, default=ahora, onupdate=ahora)

    # Relaciones
    goles = db.relationship('Gol', backref='partido', lazy=True)
    responsable = db.relationship('Usuario', foreign_keys=[id_usuario], lazy=True)

    def __repr__(self):
        return f'<Partido {self.id_partido}: Local {self.id_equipo_local} vs Visitante {self.id_equipo_visitante}>'

    @property
    def tiene_resultado(self):
        return self.goles_local is not None and self.goles_visitante is not None

    def sincronizar_marcador(self):
        self.marcador = f'{self.goles_local}-{self.goles_visitante}' if self.tiene_resultado else None

    def to_dict(self):
        return {
            'id_partido': self.id_partido,
            'id_torneo': self.id_torneo,
            'torneo': self.torneo.nombre if self.torneo else None,
            'categoria': self.torneo.categoria if self.torneo else None,
            'id_equipo_local': self.id_equipo_local,
            'equipo_local': self.equipo_local.nombre if self.equipo_local else None,
            'id_equipo_visitante': self.id_equipo_visitante,
            'equipo_visitante': self.equipo_visitante.nombre if self.equipo_visitante else None,
            'id_usuario': self.id_usuario,
            'responsable': self.responsable.nombre if self.responsable else None,
            'fecha': iso(self.fecha),
            'lugar': self.lugar,
            'estado': self.estado,
            'goles_local': self.goles_local,
            'goles_visitante': self.goles_visitante,
            'marcador': self.marcador,
            'observaciones': self.observaciones,
            'fecha_actualizacion': iso(self.fecha_actualizacion),
        }
