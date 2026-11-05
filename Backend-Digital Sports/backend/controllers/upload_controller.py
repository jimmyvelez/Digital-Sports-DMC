# =============================================================================
# Controlador: Subida de imágenes (noticias y escudos) — /api/uploads (docente/admin)
# Las URLs se declaran en backend/routes/upload_routes.py
# =============================================================================
import os
import uuid

from flask import current_app, request

from backend.utils.auth import roles_requeridos
from backend.utils.respuestas import ApiError, respuesta_json


# Firmas (magic bytes) de los formatos de imagen aceptados
FIRMAS = {
    'png': [b'\x89PNG\r\n\x1a\n'],
    'jpg': [b'\xff\xd8\xff'],
    'jpeg': [b'\xff\xd8\xff'],
    'gif': [b'GIF87a', b'GIF89a'],
}


def _es_imagen_valida(extension, cabecera):
    if extension == 'avif':
        return cabecera[4:8] == b'ftyp' and b'avi' in cabecera[8:16]
    if extension == 'webp':
        return cabecera.startswith(b'RIFF') and cabecera[8:12] == b'WEBP'
    return any(cabecera.startswith(f) for f in FIRMAS.get(extension, []))


@roles_requeridos('admin', 'docente')
def subir_imagen():
    """POST /api/uploads — multipart/form-data con el campo 'archivo'. Devuelve {url}."""
    archivo = request.files.get('archivo')
    if not archivo or not archivo.filename:
        raise ApiError('Selecciona una imagen para subir.')
    extension = archivo.filename.rsplit('.', 1)[-1].lower() if '.' in archivo.filename else ''
    if extension not in current_app.config['EXTENSIONES_IMAGEN']:
        raise ApiError('Formato no permitido. Usa PNG, JPG, WEBP, GIF o AVIF.')
    cabecera = archivo.stream.read(32)
    archivo.stream.seek(0)
    if not _es_imagen_valida(extension, cabecera):
        raise ApiError('El archivo no es una imagen válida.')

    carpeta = current_app.config['UPLOAD_DIR']
    os.makedirs(carpeta, exist_ok=True)
    nombre = f'{uuid.uuid4().hex}.{extension}'  # nombre generado: nunca se usa el del cliente
    archivo.save(os.path.join(carpeta, nombre))
    return respuesta_json({'url': f'/uploads/{nombre}'}, 201)
