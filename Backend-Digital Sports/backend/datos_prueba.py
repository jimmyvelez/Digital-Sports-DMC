"""
Datos de prueba — Digital Sports DMC
=====================================
Carga un escenario completo para probar la plataforma con los tres roles:

    flask --app run.py datos-prueba

Todo se crea A TRAVÉS DE LA API (como lo harían el administrador, los docentes
y los estudiantes), así que se aplican las mismas validaciones y permisos, y
las notificaciones, la clasificación y el historial se generan con eventos
reales. Las fechas se calculan a partir del día de ejecución (partidos pasados
con resultado y partidos futuros programados).

Solo se ejecuta si la base de datos no tiene torneos, para no mezclar datos.
Las contraseñas de estas cuentas son de PRUEBA: no usar en producción.
"""
import random
from datetime import timedelta

from backend.extensions import db
from backend.utils.tiempo import ahora

CLAVE_ADMIN = 'Admin12345'
CLAVE_DOCENTE = 'Docente123'
CLAVE_ESTUDIANTE = 'Estudiante123'
DOMINIO = 'dmc.edu.co'

NOMBRES_H = ['Andrés', 'Santiago', 'Mateo', 'Samuel', 'Juan David', 'Nicolás', 'Sebastián', 'Tomás', 'Daniel',
             'Alejandro', 'Felipe', 'Julián', 'Esteban', 'Camilo', 'David', 'Miguel', 'Kevin', 'Brayan',
             'Óscar', 'Diego', 'Jhon', 'Luis', 'Martín', 'Emmanuel']
NOMBRES_M = ['Laura', 'Valentina', 'Sofía', 'Mariana', 'Isabella', 'Daniela', 'Gabriela', 'Sara', 'Paula',
             'Natalia', 'Juliana', 'Camila', 'Manuela', 'Salomé', 'Luciana', 'Antonella']
APELLIDOS = ['López', 'Gómez', 'Rodríguez', 'Martínez', 'García', 'Hernández', 'Díaz', 'Moreno', 'Rojas',
             'Castro', 'Vargas', 'Ortiz', 'Ramírez', 'Torres', 'Suárez', 'Pérez', 'Jiménez', 'Ruiz',
             'Cárdenas', 'Muñoz', 'Rincón', 'Pineda', 'Salazar', 'Quintero']

LUGARES = ['Cancha principal', 'Cancha 2', 'Coliseo cubierto']


class Cliente:
    """Cliente HTTP interno (test_client) con la sesión de un usuario concreto."""

    def __init__(self, app, id_usuario=None):
        self.c = app.test_client()
        if id_usuario:
            with self.c.session_transaction() as s:
                s['id_usuario'] = id_usuario

    def __call__(self, metodo, ruta, body=None):
        r = self.c.open('/api' + ruta, method=metodo, json=body, headers={'X-Requested-With': 'datos-prueba'})
        if r.status_code >= 400:
            raise RuntimeError(f'{metodo} {ruta} -> {r.status_code}: {r.get_json()}')
        return r.get_json()


def _correo(nombre):
    import unicodedata
    base = unicodedata.normalize('NFKD', nombre.lower()).encode('ascii', 'ignore').decode()
    partes = base.replace(' ', '.').split('.')
    return f"{partes[0]}.{partes[-1]}@{DOMINIO}"


def _round_robin(ids):
    """Fixture todos contra todos (método del círculo), ida y vuelta."""
    equipos = list(ids) + ([None] if len(ids) % 2 else [])
    n = len(equipos)
    jornadas = []
    for r in range(n - 1):
        jornada = []
        for i in range(n // 2):
            a, b = equipos[i], equipos[n - 1 - i]
            if a is not None and b is not None:
                jornada.append((a, b) if r % 2 == 0 else (b, a))
        jornadas.append(jornada)
        equipos = [equipos[0]] + [equipos[-1]] + equipos[1:-1]
    return jornadas + [[(b, a) for a, b in j] for j in jornadas]


def sembrar(app, log=print):
    from backend.models import Torneo, Usuario

    if Torneo.query.count():
        raise RuntimeError('La base de datos ya tiene torneos. Los datos de prueba solo se cargan en una base vacía.')

    rnd = random.Random(2026)
    hoy = ahora().replace(minute=0, second=0)
    resumen = {'cuentas': []}

    # ------------------------------------------------------------ Administrador
    admin = Usuario.query.filter_by(rol='admin', activo=True).first()
    if not admin:
        from backend import _crear_admin
        admin, _ = _crear_admin('Administrador DMC', f'admin@{DOMINIO}', CLAVE_ADMIN)
        resumen['cuentas'].append(('admin', admin.correo, CLAVE_ADMIN))
    else:
        resumen['cuentas'].append(('admin', admin.correo, '(contraseña actual, no se modifica)'))
    A = Cliente(app, admin.id_usuario)

    # ------------------------------------------------------------ Docentes
    docentes = {}
    for clave, nombre in (('carlos', 'Carlos Rodríguez'), ('julio', 'Julio Herrera'), ('viviana', 'Viviana Martínez')):
        u = A('POST', '/usuarios', {'nombre': nombre, 'correo': _correo(nombre), 'contrasena': CLAVE_DOCENTE,
                                    'rol': 'docente'})
        docentes[clave] = (u, Cliente(app, u['id_usuario']))
        resumen['cuentas'].append(('docente', u['correo'], CLAVE_DOCENTE))
    log('  Docentes creados: 3')

    # ------------------------------------------------------------ Torneos
    inicio = (hoy - timedelta(days=35)).date()
    fin = (hoy + timedelta(days=75)).date()
    def_torneos = [
        ('Masculino Sección A', 'Masculino A', 'Cursos de sexto, séptimo y octavo. Liga todos contra todos a dos vueltas.', 'activo'),
        ('Masculino Sección B', 'Masculino B', 'Cursos de noveno, décimo, undécimo y el equipo de profesores.', 'activo'),
        ('Femenino', 'Femenino', 'Torneo femenino interclases con equipos representativos de cada grado.', 'activo'),
        ('Interroscas', 'Roscas', 'Torneo entre grupos de amigos. Formato libre enfocado en la integración.', 'planificacion'),
    ]
    torneos = []
    for nombre, cat, desc, estado in def_torneos:
        torneos.append(A('POST', '/torneos', {
            'nombre': nombre, 'categoria': cat, 'descripcion': desc, 'estado': estado,
            'fecha_inicio': inicio.isoformat(), 'fecha_fin': fin.isoformat(), 'sistema_competicion': 'liga'}))
    log('  Torneos creados: 4')

    # ------------------------------------------------------------ Equipos (los crea cada docente)
    def_equipos = {
        0: [('601', 'Sexto', 'carlos'), ('602', 'Sexto', 'carlos'), ('701', 'Séptimo', 'carlos'),
            ('702', 'Séptimo', 'julio'), ('801', 'Octavo', 'julio'), ('802', 'Octavo', 'julio')],
        1: [('901', 'Noveno', 'julio'), ('1001', 'Décimo', 'julio'), ('1101', 'Undécimo', 'carlos'),
            ('Profesores', 'Profesores', 'carlos')],
        2: [('601 Femenino', 'Sexto', 'viviana'), ('702 Femenino', 'Séptimo', 'viviana'),
            ('902 Femenino', 'Noveno', 'viviana'), ('1102 Femenino', 'Undécimo', 'viviana')],
        3: [('Tormenta FC', 'Mixto', 'carlos'), ('Invictus', 'Mixto', 'julio'), ('Imperio', 'Mixto', 'viviana'),
            ('Fénix', 'Mixto', 'julio')],
    }
    equipos = {}  # id_equipo -> dict con datos, docente y jugadores
    por_torneo = {}
    for t_idx, lista in def_equipos.items():
        torneo = torneos[t_idx]
        por_torneo[t_idx] = []
        for nombre, curso, doc in lista:
            e = docentes[doc][1]('POST', '/equipos', {'id_torneo': torneo['id_torneo'], 'nombre': nombre, 'curso': curso,
                                                      'descripcion': f'Equipo {nombre} del torneo {torneo["nombre"]}.'})
            equipos[e['id_equipo']] = {'datos': e, 'doc': doc, 'jugadores': []}
            por_torneo[t_idx].append(e['id_equipo'])
    log(f'  Equipos creados: {len(equipos)}')

    # ------------------------------------------------------------ Estudiantes y plantillas
    usados = set()

    def nombre_unico(femenino):
        while True:
            n = f"{rnd.choice(NOMBRES_M if femenino else NOMBRES_H)} {rnd.choice(APELLIDOS)}"
            if n not in usados and _correo(n) not in {_correo(x) for x in usados}:
                usados.add(n)
                return n

    estudiantes_con_cuenta = []  # (usuario, cliente, id_equipo)
    for t_idx, ids in por_torneo.items():
        if t_idx == 3:
            continue  # Interroscas: se arma con estudiantes que ya juegan en otros torneos
        for id_eq in ids:
            eq = equipos[id_eq]
            femenino = t_idx == 2
            cuentas = 2 if t_idx in (0, 2) else 1
            for i in range(6):
                if eq['datos']['nombre'] == 'Profesores':
                    nombre = nombre_unico(False)
                    est = docentes[eq['doc']][1]('POST', '/estudiantes', {'nombre': nombre, 'curso': 'Docentes'})
                elif i < cuentas:
                    nombre = nombre_unico(femenino)
                    cli = Cliente(app)
                    reg = cli('POST', '/usuarios/registro', {'nombre': nombre, 'correo': _correo(nombre),
                                                             'contrasena': CLAVE_ESTUDIANTE, 'curso': eq['datos']['curso']})
                    est = {'id_estudiante': reg['usuario']['id_estudiante'], 'nombre': nombre}
                    estudiantes_con_cuenta.append((reg['usuario'], cli, id_eq))
                else:
                    nombre = nombre_unico(femenino)
                    est = docentes[eq['doc']][1]('POST', '/estudiantes', {'nombre': nombre, 'curso': eq['datos']['curso']})
                docentes[eq['doc']][1]('POST', f'/equipos/{id_eq}/integrantes',
                                       {'id_estudiante': est['id_estudiante'], 'dorsal': i + 1 if i else 10})
                eq['jugadores'].append(est['id_estudiante'])
    # Interroscas: jugadores de otros torneos (regla: un equipo por torneo, varios torneos permitidos)
    libres = [e for e, _, _ in estudiantes_con_cuenta]
    for k, id_eq in enumerate(por_torneo[3]):
        for u in libres[k * 3:(k + 1) * 3]:
            docentes[equipos[id_eq]['doc']][1]('POST', f'/equipos/{id_eq}/integrantes', {'id_estudiante': u['id_estudiante']})
            equipos[id_eq]['jugadores'].append(u['id_estudiante'])
    log(f'  Estudiantes: {len(estudiantes_con_cuenta)} con cuenta + perfiles sin cuenta en las plantillas')

    # Cuenta desactivada (para probar la gestión de usuarios)
    inactivo = A('POST', '/usuarios', {'nombre': 'Cuenta Desactivada', 'correo': f'inactivo@{DOMINIO}',
                                       'contrasena': CLAVE_ESTUDIANTE, 'rol': 'estudiante'})
    A('PUT', f"/usuarios/{inactivo['id_usuario']}", {'activo': False})

    # ------------------------------------------------------------ Partidos, resultados y goles
    total = {'partidos': 0, 'finalizados': 0, 'goles': 0}
    futuros = []
    for t_idx in (0, 1, 2):
        torneo = torneos[t_idx]
        for j, jornada in enumerate(_round_robin(por_torneo[t_idx])):
            dia = hoy.replace(hour=7) - timedelta(days=32) + timedelta(days=7 * j + t_idx)
            for m, (local, visitante) in enumerate(jornada):
                fecha = dia + timedelta(hours=2 * m)
                doc = docentes[equipos[local]['doc']][1]
                p = doc('POST', '/partidos', {
                    'id_torneo': torneo['id_torneo'], 'id_equipo_local': local, 'id_equipo_visitante': visitante,
                    'fecha': fecha.isoformat(timespec='minutes'), 'lugar': LUGARES[(m + t_idx) % 2]})
                total['partidos'] += 1
                if fecha < hoy - timedelta(hours=2):
                    gl, gv = rnd.choice([0, 1, 1, 2, 2, 3, 4]), rnd.choice([0, 0, 1, 1, 2, 3])
                    doc('PUT', f"/partidos/{p['id_partido']}/resultado", {'goles_local': gl, 'goles_visitante': gv})
                    total['finalizados'] += 1
                    for id_eq, goles in ((local, gl), (visitante, gv)):
                        for _ in range(goles):
                            doc('POST', '/goles', {'id_partido': p['id_partido'],
                                                   'id_estudiante': rnd.choice(equipos[id_eq]['jugadores']),
                                                   'minuto': rnd.randint(1, 60)})
                            total['goles'] += 1
                    # Faltas en algunos partidos
                    if rnd.random() < 0.35:
                        id_eq = rnd.choice((local, visitante))
                        doc('POST', '/faltas', {'id_partido': p['id_partido'], 'id_equipo': id_eq,
                                                'id_estudiante': rnd.choice(equipos[id_eq]['jugadores']),
                                                'tipo': rnd.choice(['tarjeta_amarilla', 'tarjeta_amarilla', 'tarjeta_roja',
                                                                    'conducta_antideportiva']),
                                                'minuto': rnd.randint(5, 58),
                                                'descripcion': 'Registro de prueba generado para la demostración.'})
                else:
                    futuros.append((p, doc))
    # Estados especiales en partidos próximos
    if len(futuros) >= 4:
        p, doc = futuros[0]
        doc('PUT', f"/partidos/{p['id_partido']}", {'lugar': 'Coliseo cubierto'})           # cambio de lugar
        p, doc = futuros[1]
        doc('PATCH', f"/partidos/{p['id_partido']}/estado", {'estado': 'suspendido', 'motivo': 'Lluvia fuerte'})
        p, doc = futuros[2]
        doc('PATCH', f"/partidos/{p['id_partido']}/estado", {'estado': 'cancelado', 'motivo': 'Actividad institucional'})
    # Un partido en juego hoy (Masculino B)
    ids_b = por_torneo[1]
    doc = docentes[equipos[ids_b[0]]['doc']][1]
    p = doc('POST', '/partidos', {'id_torneo': torneos[1]['id_torneo'], 'id_equipo_local': ids_b[0],
                                  'id_equipo_visitante': ids_b[2],
                                  'fecha': (ahora() - timedelta(minutes=30)).isoformat(timespec='minutes'),
                                  'lugar': 'Coliseo cubierto', 'observaciones': 'Partido amistoso de exhibición.'})
    doc('PATCH', f"/partidos/{p['id_partido']}/estado", {'estado': 'en_juego'})
    doc('PUT', f"/partidos/{p['id_partido']}/resultado", {'goles_local': 1, 'goles_visitante': 0, 'finalizar': False})
    total['partidos'] += 1
    log(f"  Partidos: {total['partidos']} ({total['finalizados']} finalizados), goles registrados: {total['goles']}")

    # ------------------------------------------------------------ Noticias y comentarios
    carlos, julio, viviana = (docentes[k][1] for k in ('carlos', 'julio', 'viviana'))
    textos = [
        (carlos, 'Arrancó la liga Masculina Sección A', '../assets/img/noticia1.jpg',
         'Con seis equipos de sexto a octavo grado comenzó la liga masculina sección A. Los partidos se juegan '
         'en la cancha principal y en la cancha 2 durante los descansos. Consulta el calendario en la sección '
         'de partidos y sigue la tabla de posiciones, que se actualiza con cada resultado.', 'publicada'),
        (viviana, 'El torneo femenino supera todas las expectativas', '../assets/img/noticia2.avif',
         'Cuatro equipos representativos disputan el torneo femenino interclases. La participación ha sido '
         'masiva y las graderías se llenan en cada encuentro. ¡Gracias a toda la comunidad por el apoyo!', 'publicada'),
        (julio, 'Recomendaciones para los partidos en días de lluvia', '../assets/img/noticia3.png',
         'Cuando llueva con fuerza los partidos podrán suspenderse y reprogramarse. Revisa tus notificaciones: '
         'la plataforma te avisará de cualquier cambio de fecha, hora o lugar de los partidos de tu equipo.', 'publicada'),
        (A, 'Abiertas las inscripciones para Interroscas', '../assets/img/noticia4.avif',
         'Los grupos de amigos ya pueden inscribirse al torneo Interroscas. Habla con tu docente de educación '
         'física para registrar tu equipo. El torneo está en planificación y pronto se publicará el calendario.', 'publicada'),
        (carlos, 'Borrador: premiación de fin de año', '../assets/img/carrusel1.jpg',
         'Este borrador describe la ceremonia de premiación de los campeones. Aún no está visible para los estudiantes.', 'borrador'),
    ]
    noticias = []
    for cli, titulo, img, contenido, estado in textos:
        noticias.append(cli('POST', '/noticias', {'titulo': titulo, 'contenido': contenido, 'imagen': img, 'estado': estado}))
    retirada = julio('POST', '/noticias', {'titulo': 'Cambio de horario del descanso (retirada)', 'estado': 'publicada',
                                           'contenido': 'Esta noticia fue publicada con información errónea y luego se retiró.',
                                           'imagen': '../assets/img/carrusel2.jpg'})
    julio('PATCH', f"/noticias/{retirada['id_noticia']}/estado", {'estado': 'retirada'})
    comentarios_txt = ['¡Qué buen torneo! Vamos con toda 💪', 'Excelente organización, felicitaciones a los profes.',
                       '¿Cuándo sale el calendario de la segunda vuelta?', 'Mi equipo va a ser campeón este año.',
                       'Gracias por mantenernos informados.', 'Ojalá hagan un partido de estudiantes contra profesores.']
    comentarios = []
    for k, (u, cli, _) in enumerate(estudiantes_con_cuenta[:len(comentarios_txt)]):
        comentarios.append(cli('POST', f"/noticias/{noticias[k % 3]['id_noticia']}/comentarios",
                               {'contenido': comentarios_txt[k]}))
    # Comentario reportado para la moderación del admin
    malo = estudiantes_con_cuenta[7][1]('POST', f"/noticias/{noticias[0]['id_noticia']}/comentarios",
                                          {'contenido': 'Comentario ofensivo de prueba para la bandeja de moderación.'})
    estudiantes_con_cuenta[8][1]('POST', f"/comentarios/{malo['id_comentario']}/reportar")
    log(f'  Noticias: {len(noticias) + 1}, comentarios: {len(comentarios) + 1}')

    # Un estudiante ya leyó sus notificaciones (para ver ambos estados)
    estudiantes_con_cuenta[1][1]('PATCH', '/notificaciones/leer-todas')

    for u, _, id_eq in estudiantes_con_cuenta:
        resumen['cuentas'].append(('estudiante', u['correo'], CLAVE_ESTUDIANTE, equipos[id_eq]['datos']['nombre']))
    resumen['cuentas'].append(('estudiante (desactivado)', inactivo['correo'], CLAVE_ESTUDIANTE))
    db.session.remove()
    return resumen
