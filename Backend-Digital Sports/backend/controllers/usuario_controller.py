# =============================================================================
# Controlador: Autenticación, perfil y gestión de usuarios — /api/usuarios
# =============================================================================
from flask import request, session, current_app
from sqlalchemy import func, or_
from werkzeug.security import check_password_hash, generate_password_hash

from backend.extensions import db
from backend.models.estudiante import Estudiante
from backend.models.usuario import ROLES, Usuario
from backend.services import auditoria_service, auth_service
from backend.services.equipo_service import equipos_de_estudiante
from backend.utils.auth import login_requerido, roles_requeridos, usuario_actual
from backend.utils.consultas import obtener_o_404
from backend.utils.respuestas import ApiError, paginar, respuesta_json
from backend.utils.tiempo import ahora
from backend.utils import validacion as v


def _datos_sesion(usuario):
    data = usuario.to_dict()
    perfil = usuario.perfil_estudiante
    data['foto_perfil'] = usuario.foto_perfil
    if perfil:
        data['id_estudiante'] = perfil.id_estudiante
        data['curso'] = perfil.curso
        data['equipos'] = [{'id_equipo': e.id_equipo, 'nombre': e.nombre, 'id_torneo': e.id_torneo,
                            'torneo': e.torneo.nombre} for e in equipos_de_estudiante(perfil)]
    return data


def _iniciar_sesion(usuario):
    session.clear()
    session.permanent = True
    session['id_usuario'] = usuario.id_usuario
    usuario.ultimo_acceso = ahora()


def _correo_disponible(correo, excluir_id=None):
    q = Usuario.query.filter(func.lower(Usuario.correo) == correo.lower())
    if excluir_id:
        q = q.filter(Usuario.id_usuario != excluir_id)
    if q.first():
        raise ApiError('Ya existe un usuario registrado con ese correo.', 409)


# -----------------------------------------------------------------------------
# Registro público (SIEMPRE rol estudiante), login, logout y sesión
# -----------------------------------------------------------------------------
def registrar_usuario():
    """POST /api/usuarios/registro — Registro público de estudiantes."""
    data = v.cuerpo_json()
    nombre = v.texto(data, 'nombre', minimo=3, maximo=100)
    correo = v.correo(data)
    contrasena = v.contrasena_segura(data.get('contrasena'))
    curso = v.texto(data, 'curso', requerido=False, maximo=50)
    _correo_disponible(correo)

    # El rol se fija en el servidor: cualquier "rol" enviado por el cliente se ignora.
    usuario = Usuario(nombre=nombre, correo=correo, contrasena=generate_password_hash(contrasena),
                      rol='estudiante', activo=True)
    db.session.add(usuario)
    db.session.flush()
    db.session.add(Estudiante(nombre=nombre, curso=curso, id_usuario=usuario.id_usuario))
    auditoria_service.registrar('registro', 'usuario', usuario.id_usuario, {'correo': correo}, usuario=usuario)
    _iniciar_sesion(usuario)
    db.session.commit()
    return respuesta_json({'mensaje': 'Cuenta creada correctamente.', 'usuario': _datos_sesion(usuario)}, 201)


def login_usuario():
    """POST /api/usuarios/login — Inicia sesión con correo (o nombre de usuario) y contraseña."""
    data = v.cuerpo_json()
    identificador = v.texto(data, 'correo', maximo=150, etiqueta='correo')
    contrasena = data.get('contrasena') or ''
    if not contrasena:
        raise ApiError('Correo y contraseña son obligatorios.')

    ip = request.remote_addr or 'desconocida'
    espera = auth_service.login_bloqueado(ip, identificador)
    if espera:
        raise ApiError(f'Demasiados intentos fallidos. Intenta de nuevo en {max(espera // 60, 1)} minuto(s).', 429)

    usuario = Usuario.query.filter(or_(func.lower(Usuario.correo) == identificador.lower(),
                                       Usuario.nombre == identificador)).first()
    if not usuario or not check_password_hash(usuario.contrasena, contrasena):
        auth_service.registrar_fallo(ip, identificador)
        raise ApiError('Correo o contraseña incorrectos.', 401)
    if not usuario.activo:
        raise ApiError('Tu cuenta está desactivada. Contacta al administrador.', 403)

    auth_service.limpiar_fallos(ip, identificador)
    _iniciar_sesion(usuario)
    db.session.commit()
    return respuesta_json({'mensaje': f'¡Bienvenido, {usuario.nombre}!', 'usuario': _datos_sesion(usuario)})


def configuracion_auth():
    """GET /api/usuarios/auth-config — Configuración pública de autenticación (ej. Google Client ID)."""
    client_id = current_app.config.get('GOOGLE_CLIENT_ID')
    return respuesta_json({
        'google_client_id': client_id if client_id and client_id != 'TU_GOOGLE_CLIENT_ID' else None
    })


def google_login():
    """POST /api/usuarios/google-login — Inicia sesión o registra con Google OAuth."""
    import logging
    from google.oauth2 import id_token
    from google.auth.transport import requests as google_requests
    from google.auth.exceptions import GoogleAuthError

    data = v.cuerpo_json()
    token = data.get('credential')
    if not token:
        raise ApiError('No se recibió credencial de Google.', 400)

    client_id = current_app.config.get('GOOGLE_CLIENT_ID')
    if not client_id or client_id == 'TU_GOOGLE_CLIENT_ID':
        raise ApiError('El login con Google no está configurado en el servidor.', 500)

    try:
        idinfo = id_token.verify_oauth2_token(
            token,
            google_requests.Request(),
            client_id,
            clock_skew_in_seconds=300
        )

        correo = idinfo.get('email')
        nombre = idinfo.get('name', 'Usuario de Google')
        foto_perfil = idinfo.get('picture')
        google_id = idinfo.get('sub') or idinfo.get('user_id')

        if not correo:
            raise ApiError('No se pudo obtener el correo de Google.', 400)

        es_nuevo = False

        # Buscar primero por google_id (más preciso), luego por correo
        usuario = None
        if google_id:
            usuario = Usuario.query.filter(Usuario.google_id == google_id).first()
        if not usuario:
            usuario = Usuario.query.filter(func.lower(Usuario.correo) == correo.lower()).first()

        if usuario:
            # ── Usuario existente ──────────────────────────────────────────────
            if not usuario.activo:
                raise ApiError('Tu cuenta está desactivada. Contacta al administrador.', 403)
            # Vincular google_id si viene y aún no está vinculado
            if google_id and not usuario.google_id:
                usuario.google_id = google_id

            # Actualizar foto de perfil si viene de Google y es nueva
            if foto_perfil and usuario.foto_perfil != foto_perfil:
                usuario.foto_perfil = foto_perfil
            # Si es estudiante sin perfil deportivo, crearlo
            if usuario.rol == 'estudiante' and not usuario.perfil_estudiante:
                if not Estudiante.query.filter_by(id_usuario=usuario.id_usuario).first():
                    db.session.add(Estudiante(nombre=usuario.nombre, id_usuario=usuario.id_usuario))
            auditoria_service.registrar('login_google', 'usuario', usuario.id_usuario,
                                        {'correo': correo}, usuario=usuario)
            logging.info('[Google Login] Login de usuario existente: %s (id=%s)', correo, usuario.id_usuario)
        else:
            # ── Usuario nuevo: crear cuenta de estudiante ──────────────────────
            es_nuevo = True
            contrasena_hash = generate_password_hash('GOOGLE_OAUTH_NO_PASSWORD')
            usuario = Usuario(nombre=nombre, correo=correo, contrasena=contrasena_hash,
                              rol='estudiante', foto_perfil=foto_perfil,
                              google_id=google_id, activo=True)
            db.session.add(usuario)
            db.session.flush()  # Genera id_usuario antes de crear el perfil
            db.session.add(Estudiante(nombre=nombre, id_usuario=usuario.id_usuario))
            auditoria_service.registrar('registro_google', 'usuario', usuario.id_usuario,
                                        {'correo': correo}, usuario=usuario)
            logging.info('[Google Login] Nuevo usuario registrado: %s (id=%s)', correo, usuario.id_usuario)

        # ── Confirmar cambios en BD ANTES de iniciar la sesión ────────────────
        # (evita que la cookie quede con un id_usuario de una transacción revertida)
        usuario.ultimo_acceso = ahora()
        db.session.commit()

        # Iniciar sesión solo después del commit exitoso
        session.clear()
        session.permanent = True
        session['id_usuario'] = usuario.id_usuario

        mensaje = (f'¡Cuenta creada con Google! Bienvenido, {usuario.nombre}.' if es_nuevo
                   else f'¡Bienvenido de nuevo, {usuario.nombre}!')
        return respuesta_json({
            'mensaje': mensaje,
            'es_nuevo': es_nuevo,
            'usuario': _datos_sesion(usuario)
        })

    except ValueError as e:
        logging.warning('[Google Login] Token inválido: %s', str(e))
        raise ApiError(f'El token de Google es inválido o ha expirado. Detalle: {str(e)}', 401)
    except GoogleAuthError as e:
        logging.error('[Google Login] Error de autenticación Google: %s', str(e))
        raise ApiError('Error al validar la autenticación con Google. Verifica tu conexión.', 502)


def logout_usuario():
    """POST /api/usuarios/logout — Cierra sesión."""
    session.clear()
    return respuesta_json({'mensaje': 'Sesión cerrada correctamente.'})


def sesion_actual():
    """GET /api/usuarios/sesion — Devuelve la sesión actual."""
    usuario = usuario_actual()
    if not usuario:
        return respuesta_json({'autenticado': False})
    return respuesta_json({'autenticado': True, 'usuario': _datos_sesion(usuario)})


# -----------------------------------------------------------------------------
# Recuperación de contraseña
# -----------------------------------------------------------------------------
def solicitar_recuperacion():
    """POST /api/usuarios/recuperar — Envía un enlace de restablecimiento (respuesta siempre genérica)."""
    data = v.cuerpo_json()
    correo = v.correo(data)
    usuario = Usuario.query.filter(func.lower(Usuario.correo) == correo).first()
    if usuario and usuario.activo:
        auth_service.enviar_correo_reset(usuario, auth_service.generar_token_reset(usuario))
    return respuesta_json({'mensaje': 'Si el correo está registrado, recibirás un enlace para restablecer '
                                      'tu contraseña.'})


def restablecer_contrasena():
    """POST /api/usuarios/restablecer — Cambia la contraseña con un token válido."""
    data = v.cuerpo_json()
    token = v.texto(data, 'token', maximo=500)
    contrasena = v.contrasena_segura(data.get('contrasena'))
    usuario = auth_service.validar_token_reset(token)
    if not usuario:
        raise ApiError('El enlace no es válido o ya expiró. Solicita uno nuevo.', 400)
    usuario.contrasena = generate_password_hash(contrasena)
    auditoria_service.registrar('restablecer_contrasena', 'usuario', usuario.id_usuario, usuario=usuario)
    db.session.commit()
    return respuesta_json({'mensaje': 'Contraseña actualizada. Ya puedes iniciar sesión.'})


# -----------------------------------------------------------------------------
# Perfil propio
# -----------------------------------------------------------------------------
@login_requerido
def ver_perfil():
    return respuesta_json(_datos_sesion(usuario_actual()))


@login_requerido
def actualizar_perfil():
    """PUT /api/usuarios/perfil — Actualiza nombre, curso y/o contraseña propios."""
    usuario = usuario_actual()
    data = v.cuerpo_json()
    if 'nombre' in data:
        usuario.nombre = v.texto(data, 'nombre', minimo=3, maximo=100)
        if usuario.perfil_estudiante:
            usuario.perfil_estudiante.nombre = usuario.nombre
    if 'curso' in data and usuario.perfil_estudiante:
        usuario.perfil_estudiante.curso = v.texto(data, 'curso', requerido=False, maximo=50)
    if data.get('contrasena_nueva'):
        if not check_password_hash(usuario.contrasena, data.get('contrasena_actual') or ''):
            raise ApiError('La contraseña actual no es correcta.', 400, {'contrasena_actual': 'incorrecta'})
        usuario.contrasena = generate_password_hash(v.contrasena_segura(data['contrasena_nueva'],
                                                                          'contrasena_nueva'))
        auditoria_service.registrar('cambiar_contrasena', 'usuario', usuario.id_usuario)
    db.session.commit()
    return respuesta_json({'mensaje': 'Perfil actualizado.', 'usuario': _datos_sesion(usuario)})


# -----------------------------------------------------------------------------
# Administración de usuarios (solo admin)
# -----------------------------------------------------------------------------
@roles_requeridos('admin')
def listar_usuarios():
    """GET /api/usuarios — Filtros: ?rol=&activo=&q="""
    query = Usuario.query
    rol = request.args.get('rol')
    if rol:
        query = query.filter(Usuario.rol == rol)
    activo = request.args.get('activo')
    if activo in ('0', '1'):
        query = query.filter(Usuario.activo.is_(activo == '1'))
    q = (request.args.get('q') or '').strip()
    if q:
        like = f'%{q}%'
        query = query.filter(or_(Usuario.nombre.ilike(like), Usuario.correo.ilike(like)))
    return respuesta_json(paginar(query.order_by(Usuario.nombre), lambda u: u.to_dict()))


@roles_requeridos('admin', 'docente')
def listar_docentes():
    """GET /api/usuarios/docentes — Docentes activos (para asignar responsables)."""
    docentes = Usuario.query.filter(Usuario.rol == 'docente', Usuario.activo.is_(True)).order_by(Usuario.nombre).all()
    return respuesta_json([{'id_usuario': d.id_usuario, 'nombre': d.nombre} for d in docentes])


def _admins_activos(excluir_id=None):
    q = Usuario.query.filter(Usuario.rol == 'admin', Usuario.activo.is_(True))
    if excluir_id:
        q = q.filter(Usuario.id_usuario != excluir_id)
    return q.count()


@roles_requeridos('admin')
def crear_usuario():
    """POST /api/usuarios — El admin crea cuentas de docentes, administradores o estudiantes."""
    data = v.cuerpo_json()
    nombre = v.texto(data, 'nombre', minimo=3, maximo=100)
    correo = v.correo(data)
    contrasena = v.contrasena_segura(data.get('contrasena'))
    rol = v.opcion(data, 'rol', ROLES)
    _correo_disponible(correo)
    usuario = Usuario(nombre=nombre, correo=correo, contrasena=generate_password_hash(contrasena), rol=rol)
    db.session.add(usuario)
    db.session.flush()
    if rol == 'estudiante':
        db.session.add(Estudiante(nombre=nombre, curso=v.texto(data, 'curso', requerido=False, maximo=50),
                                  id_usuario=usuario.id_usuario))
    auditoria_service.registrar('crear', 'usuario', usuario.id_usuario, {'correo': correo, 'rol': rol})
    db.session.commit()
    return respuesta_json(usuario.to_dict(), 201)


@roles_requeridos('admin')
def detalle_usuario(id_usuario):
    usuario = obtener_o_404(Usuario, id_usuario, 'Usuario no encontrado.')
    return respuesta_json(_datos_sesion(usuario))


@roles_requeridos('admin')
def editar_usuario(id_usuario):
    """PUT /api/usuarios/<id> — Nombre, correo, rol, estado (activo) y contraseña."""
    admin = usuario_actual()
    usuario = obtener_o_404(Usuario, id_usuario, 'Usuario no encontrado.')
    data = v.cuerpo_json()
    cambios = {}

    if 'nombre' in data:
        usuario.nombre = v.texto(data, 'nombre', minimo=3, maximo=100)
        if usuario.perfil_estudiante:
            usuario.perfil_estudiante.nombre = usuario.nombre
    if 'correo' in data:
        correo = v.correo(data)
        _correo_disponible(correo, excluir_id=usuario.id_usuario)
        usuario.correo = correo
    if 'rol' in data:
        rol = v.opcion(data, 'rol', ROLES)
        if rol != usuario.rol:
            if usuario.id_usuario == admin.id_usuario:
                raise ApiError('No puedes cambiar tu propio rol.', 409)
            if usuario.rol == 'admin' and _admins_activos(excluir_id=usuario.id_usuario) == 0:
                raise ApiError('Debe existir al menos un administrador activo.', 409)
            cambios['rol'] = [usuario.rol, rol]
            usuario.rol = rol
            if rol == 'estudiante' and not usuario.perfil_estudiante:
                db.session.add(Estudiante(nombre=usuario.nombre, id_usuario=usuario.id_usuario))
    if 'activo' in data:
        activo = v.booleano(data, 'activo')
        if activo is False and usuario.id_usuario == admin.id_usuario:
            raise ApiError('No puedes desactivar tu propia cuenta.', 409)
        if activo is False and usuario.rol == 'admin' and _admins_activos(excluir_id=usuario.id_usuario) == 0:
            raise ApiError('Debe existir al menos un administrador activo.', 409)
        if activo != usuario.activo:
            cambios['activo'] = [usuario.activo, activo]
        usuario.activo = activo
    if data.get('contrasena'):
        usuario.contrasena = generate_password_hash(v.contrasena_segura(data['contrasena']))
        cambios['contrasena'] = 'restablecida por admin'

    auditoria_service.registrar('editar', 'usuario', usuario.id_usuario, cambios or None)
    db.session.commit()
    return respuesta_json(usuario.to_dict())
