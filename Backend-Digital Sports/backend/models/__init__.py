# =============================================================================
# backend/models/__init__.py
# Importa todos los modelos para que SQLAlchemy los registre al iniciar.
# =============================================================================

from backend.models.usuario import Usuario
from backend.models.torneo import Torneo
from backend.models.equipo import Equipo
from backend.models.estudiante import Estudiante, IntegranteEquipo
from backend.models.partido import Partido
from backend.models.gol import Gol
from backend.models.posicion import Posicion
from backend.models.noticia import Noticia
from backend.models.docente import Docente
from backend.models.comentario import Comentario, ReporteComentario
from backend.models.notificacion import Notificacion
from backend.models.falta import Falta
from backend.models.auditoria import Auditoria, SchemaVersion


__all__ = [
    "Usuario",
    "Torneo",
    "Equipo",
    "Estudiante",
    "IntegranteEquipo",
    "Partido",
    "Gol",
    "Posicion",
    "Noticia",
    "Docente",
    "Comentario",
    "ReporteComentario",
    "Notificacion",
    "Falta",
    "Auditoria",
    "SchemaVersion",
]
