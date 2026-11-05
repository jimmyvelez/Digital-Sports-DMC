"""Helpers de validación de entrada. Lanzan ApiError(400) con mensajes claros."""
import re
from datetime import date, datetime

from flask import request

from backend.utils.respuestas import ApiError

CORREO_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')


def cuerpo_json():
    """Devuelve el cuerpo JSON como dict o lanza 400."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ApiError('El cuerpo de la solicitud debe ser un objeto JSON.')
    return data


def texto(data, campo, requerido=True, minimo=0, maximo=None, etiqueta=None):
    etiqueta = etiqueta or campo
    valor = data.get(campo)
    if valor is None or (isinstance(valor, str) and not valor.strip()):
        if requerido:
            raise ApiError(f'El campo "{etiqueta}" es obligatorio.', detalles={campo: 'obligatorio'})
        return None
    if not isinstance(valor, (str, int, float)):
        raise ApiError(f'El campo "{etiqueta}" debe ser texto.', detalles={campo: 'tipo'})
    valor = str(valor).strip()
    if len(valor) < minimo:
        raise ApiError(f'El campo "{etiqueta}" debe tener al menos {minimo} caracteres.', detalles={campo: 'corto'})
    if maximo and len(valor) > maximo:
        raise ApiError(f'El campo "{etiqueta}" admite como máximo {maximo} caracteres.', detalles={campo: 'largo'})
    return valor


def entero(data, campo, requerido=True, minimo=None, maximo=None, etiqueta=None):
    etiqueta = etiqueta or campo
    valor = data.get(campo)
    if valor is None or valor == '':
        if requerido:
            raise ApiError(f'El campo "{etiqueta}" es obligatorio.', detalles={campo: 'obligatorio'})
        return None
    if isinstance(valor, bool):
        raise ApiError(f'El campo "{etiqueta}" debe ser un número entero.', detalles={campo: 'tipo'})
    try:
        valor = int(valor)
    except (TypeError, ValueError):
        raise ApiError(f'El campo "{etiqueta}" debe ser un número entero.', detalles={campo: 'tipo'})
    if minimo is not None and valor < minimo:
        raise ApiError(f'El campo "{etiqueta}" debe ser mayor o igual a {minimo}.', detalles={campo: 'rango'})
    if maximo is not None and valor > maximo:
        raise ApiError(f'El campo "{etiqueta}" debe ser menor o igual a {maximo}.', detalles={campo: 'rango'})
    return valor


def opcion(data, campo, opciones, requerido=True, defecto=None, etiqueta=None):
    etiqueta = etiqueta or campo
    valor = data.get(campo)
    if valor is None or valor == '':
        if requerido and defecto is None:
            raise ApiError(f'El campo "{etiqueta}" es obligatorio.', detalles={campo: 'obligatorio'})
        return defecto
    if valor not in opciones:
        raise ApiError(f'Valor inválido para "{etiqueta}". Opciones: {", ".join(opciones)}.',
                       detalles={campo: 'opcion'})
    return valor


def booleano(data, campo, defecto=None):
    valor = data.get(campo, defecto)
    if isinstance(valor, bool) or valor is None:
        return valor
    if isinstance(valor, (int, str)):
        return str(valor).lower() in ('1', 'true', 'si', 'sí', 'on')
    raise ApiError(f'El campo "{campo}" debe ser verdadero o falso.')


def fecha_hora(data, campo, requerido=True, etiqueta=None):
    """Acepta 'YYYY-MM-DDTHH:MM[:SS]' o 'YYYY-MM-DD HH:MM'."""
    etiqueta = etiqueta or campo
    valor = data.get(campo)
    if not valor:
        if requerido:
            raise ApiError(f'El campo "{etiqueta}" es obligatorio.', detalles={campo: 'obligatorio'})
        return None
    try:
        return datetime.fromisoformat(str(valor).replace(' ', 'T')).replace(tzinfo=None, microsecond=0)
    except ValueError:
        raise ApiError(f'El campo "{etiqueta}" debe tener formato fecha y hora (AAAA-MM-DDTHH:MM).',
                       detalles={campo: 'formato'})


def solo_fecha(data, campo, requerido=False, etiqueta=None):
    etiqueta = etiqueta or campo
    valor = data.get(campo)
    if not valor:
        if requerido:
            raise ApiError(f'El campo "{etiqueta}" es obligatorio.', detalles={campo: 'obligatorio'})
        return None
    try:
        return date.fromisoformat(str(valor)[:10])
    except ValueError:
        raise ApiError(f'El campo "{etiqueta}" debe tener formato AAAA-MM-DD.', detalles={campo: 'formato'})


def correo(data, campo='correo'):
    valor = texto(data, campo, maximo=150, etiqueta='correo').lower()
    if not CORREO_RE.match(valor):
        raise ApiError('El correo electrónico no es válido.', detalles={campo: 'formato'})
    return valor


def contrasena_segura(valor, campo='contrasena'):
    """Mínimo 8 caracteres, con al menos una letra y un número."""
    if not isinstance(valor, str) or len(valor) < 8:
        raise ApiError('La contraseña debe tener al menos 8 caracteres.', detalles={campo: 'corta'})
    if len(valor) > 128:
        raise ApiError('La contraseña es demasiado larga.', detalles={campo: 'larga'})
    if not re.search(r'[A-Za-z]', valor) or not re.search(r'\d', valor):
        raise ApiError('La contraseña debe incluir letras y números.', detalles={campo: 'debil'})
    return valor


def arg_entero(nombre):
    """Lee un entero opcional de la query string (?nombre=)."""
    valor = request.args.get(nombre)
    if valor in (None, ''):
        return None
    try:
        return int(valor)
    except ValueError:
        raise ApiError(f'El parámetro "{nombre}" debe ser un número entero.')


def arg_fecha(nombre):
    valor = request.args.get(nombre)
    if not valor:
        return None
    try:
        return date.fromisoformat(valor[:10])
    except ValueError:
        raise ApiError(f'El parámetro "{nombre}" debe tener formato AAAA-MM-DD.')
