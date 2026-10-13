"""Anchoveta (ANCP / ANCG): distribución horaria de la profundidad por masa de agua (TSM / SSM).

    parametros.py   solo los valores por defecto (columnas, cortes de TSM/SSM, ejes, colores...)
    graficos.py     solo las funciones; leen los valores desde parametros.py

Los parámetros se pueden leer y cambiar directamente desde el paquete:

    import survey_analysis_imarpe.anchoveta as an
    an.TSM_FRIA = 17.5
    an.TSM_CALIDA = 19.5
    an.ejecutar("bitacora.xlsx", salida="figuras", figuras=[1, 4, 9])

Lo que asignas así queda fijo hasta que lo cambies. Lo que pasas a ejecutar(...) vale solo para esa llamada.
"""
import re as _re
import sys as _sys
import types as _types

from . import parametros as _P
from . import graficos as _g
from .graficos import (  # noqa: F401
    configurar, ver_parametros, ejecutar, FIGURAS, cargar, masa_de_agua, limpio,
    violines_por_hora, violines_partidos,
    fig_total, fig_ts_mapa, fig_por_masa, fig_medianas, fig_clases, fig_medianas_clase,
    fig_clases_juntas, fig_clases_juntas_por_masa, fig_justificacion,
    resumen, resumen_clase,
)

_PARAMS = frozenset(_P._PARAMETROS)


class _PaqueteAnchoveta(_types.ModuleType):
    """Deja leer y asignar los parámetros como atributos del paquete: an.TSM_FRIA = 17.5"""

    def __getattr__(self, nombre):                 # solo se llama si el paquete no tiene ese nombre
        if nombre in _PARAMS:
            return getattr(_P, nombre)
        raise AttributeError(f"module {self.__name__!r} has no attribute {nombre!r}")

    def __setattr__(self, nombre, valor):
        if nombre in _PARAMS:
            _g.configurar(**{nombre: valor})
        elif _re.fullmatch(r"[A-Z][A-Z0-9_]*", nombre):    # MAYÚSCULAS que no son parámetro: error de tipeo
            raise AttributeError(f"Parámetro desconocido: {nombre}. Válidos: {', '.join(_P._PARAMETROS)}")
        else:
            super().__setattr__(nombre, valor)

    def __dir__(self):
        return sorted(set(super().__dir__()) | _PARAMS)


_sys.modules[__name__].__class__ = _PaqueteAnchoveta
