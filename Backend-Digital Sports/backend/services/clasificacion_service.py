"""
Cálculo de la tabla de posiciones.

Estrategia: la clasificación se calcula SIEMPRE a partir de los resultados
oficiales almacenados en la tabla partido. Así:
  - refleja en todo momento el estado real de la base de datos,
  - un resultado modificado o anulado se refleja de inmediato,
  - es imposible contar dos veces un encuentro (cada partido se recorre una vez),
  - nadie puede editar puntos manualmente.

Solo cuentan los partidos con estado 'finalizado' y resultado registrado.
Programados, en juego, suspendidos y cancelados no suman.

Puntuación (configurable por torneo): victoria 3, empate 1, derrota 0.
Orden (configurable por torneo, campo criterios_desempate):
  pts  = mayor cantidad de puntos
  dg   = mayor diferencia de goles (GF - GC)
  gf   = mayor cantidad de goles a favor
  pg   = mayor cantidad de partidos ganados
  gc_menor = menor cantidad de goles en contra
Si persiste el empate se ordena alfabéticamente solo para mostrar la tabla
de forma estable (no es un criterio oficial) y los equipos comparten posición.
"""
from backend.models.equipo import Equipo
from backend.models.partido import Partido


def _fila_vacia(equipo):
    return {'id_equipo': equipo.id_equipo, 'equipo': equipo.nombre, 'curso': equipo.curso,
            'pj': 0, 'pg': 0, 'pe': 0, 'pp': 0, 'gf': 0, 'gc': 0, 'dg': 0, 'pts': 0}


def partidos_computables(id_torneo):
    return (Partido.query
            .filter(Partido.id_torneo == id_torneo,
                    Partido.estado == 'finalizado',
                    Partido.goles_local.isnot(None),
                    Partido.goles_visitante.isnot(None))
            .all())


def calcular_tabla(torneo):
    """Devuelve la lista ordenada de filas de la tabla de posiciones del torneo."""
    filas = {e.id_equipo: _fila_vacia(e) for e in Equipo.query.filter_by(id_torneo=torneo.id_torneo).all()
             if e.estado == 'activo'}

    for p in partidos_computables(torneo.id_torneo):
        for equipo in (p.equipo_local, p.equipo_visitante):
            if equipo.id_equipo not in filas:  # equipo inactivo con partidos jugados
                filas[equipo.id_equipo] = _fila_vacia(equipo)
        local, visita = filas[p.id_equipo_local], filas[p.id_equipo_visitante]
        gl, gv = p.goles_local, p.goles_visitante

        for fila, a_favor, en_contra in ((local, gl, gv), (visita, gv, gl)):
            fila['pj'] += 1
            fila['gf'] += a_favor
            fila['gc'] += en_contra
            if a_favor > en_contra:
                fila['pg'] += 1
                fila['pts'] += torneo.puntos_victoria
            elif a_favor == en_contra:
                fila['pe'] += 1
                fila['pts'] += torneo.puntos_empate
            else:
                fila['pp'] += 1
                fila['pts'] += torneo.puntos_derrota

    for fila in filas.values():
        fila['dg'] = fila['gf'] - fila['gc']

    criterios = torneo.lista_criterios()

    def clave_oficial(f):
        return tuple(f['gc'] if c == 'gc_menor' else -f[c] for c in criterios)

    ordenadas = sorted(filas.values(), key=lambda f: (clave_oficial(f), f['equipo'].lower()))

    # Posición compartida si los criterios oficiales empatan
    anterior = None
    for i, fila in enumerate(ordenadas, start=1):
        clave = clave_oficial(fila)
        fila['posicion'] = ordenadas[i - 2]['posicion'] if anterior == clave else i
        anterior = clave
    return ordenadas


def posicion_de_equipo(equipo):
    for fila in calcular_tabla(equipo.torneo):
        if fila['id_equipo'] == equipo.id_equipo:
            return fila
    return None
