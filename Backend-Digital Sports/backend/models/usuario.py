from backend.extensions import db
from backend.utils.tiempo import ahora, iso


ROLES = ('admin', 'docente', 'estudiante')


class Usuario(db.Model):
    """
    Modelo USUARIO
    Cuenta de acceso al sistema. El rol define los permisos:
      - admin: acceso global.
      - docente: gestiona equipos, partidos, noticias y faltas.
      - estudiante: consulta, comenta y recibe notificaciones.
    Un usuario con rol estudiante tiene un perfil deportivo en la tabla estudiante.
    """
    __tablename__ = 'usuario'

    id_usuario = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nombre = db.Column(db.String(100), nullable=False)
    correo = db.Column(db.String(150), unique=True, nullable=False)
    contrasena = db.Column(db.String(255), nullable=False)
    rol = db.Column(db.String(100), nullable=False, default='estudiante')
    foto_perfil = db.Column(db.String(500), nullable=True)
    google_id = db.Column(db.String(128), unique=True, nullable=True)  # sub de Google OAuth
    activo = db.Column(db.Boolean, nullable=False, default=True)
    fecha_creacion = db.Column(db.DateTime, nullable=True, default=ahora)
    ultimo_acceso = db.Column(db.DateTime, nullable=True)

    @property
    def es_cuenta_google(self):
        """True si esta cuenta fue creada o vinculada con Google OAuth."""
        return self.google_id is not None

    def __repr__(self):
        return f'<Usuario {self.id_usuario}: {self.nombre}>'

    def to_dict(self):
        return {
            'id_usuario': self.id_usuario,
            'nombre': self.nombre,
            'correo': self.correo,
            'foto_perfil': self.foto_perfil,
            'rol': self.rol,
            'activo': bool(self.activo),
            'es_cuenta_google': self.es_cuenta_google,
            'fecha_creacion': iso(self.fecha_creacion),
            'ultimo_acceso': iso(self.ultimo_acceso),
            # Nunca se incluye la contraseña
        }
