# Survey\_Analysis\_IMARPE

Colección de funciones de análisis de cruceros y evaluaciones. Cada análisis es un subpaquete independiente.

|Subpaquete|Qué hace|
|-|-|
|`survey\_analysis\_imarpe.anchoveta`|Distribución horaria de profundidad de anchoveta (ANCP/ANCG) por masa de agua (TSM/SSM)|

## Instalación

```bash
pip install git+https://github.com/danielgrados/Survey\_Analysis\_IMARPE.git
# versión fija (recomendado para reproducibilidad):
pip install git+https://github.com/danielgrados/Survey\_Analysis\_IMARPE.git@v0.1.0
```

## Uso: anchoveta

```python
from survey\_analysis\_imarpe.anchoveta import ejecutar

a = ejecutar(
    "Bitacora\_completa\_2026-2.xlsx",   # .xlsx o .csv
    salida="figuras",                  # PNG 300 dpi + EPS + CSV
    TSM\_FRIA=17.5,                     # obligatorio: TSM < este valor -> "Fría"
    TSM\_CALIDA=19.5,                   # obligatorio: TSM >= este valor -> "Cálida"
)
```

Parámetros opcionales (en mayúsculas): `CLASES`, `COL\_PROF`, `COL\_HORA`, `COL\_SSM`, `COL\_TSM`, `SSM\_ASS`,
`SEPARAR\_POR\_SSM`, `SSM\_CORTE`, `HORA\_AMANECER`, `HORA\_ATARDECER`, `MIN\_N\_VIOLIN`, `PROF\_MAX\_EJE`, `FUENTE`,
`COLORES`, `COLOR\_CLASE`.

Columnas requeridas: `Region\_class`, `Depth\_mean`, `Time\_M`, `SSM`, `TSM`, `Lat\_M`, `Lon\_M`.

Una sola función:

```python
import survey\_analysis\_imarpe.anchoveta as an
from pathlib import Path

an.configurar(ARCHIVO="bitacora.xlsx", TSM\_FRIA=17.5, TSM\_CALIDA=19.5, PROF\_MAX\_EJE=60)
a = an.cargar()
a\["masa"] = an.masa\_de\_agua(a)
a = a\[a\["masa"] != "sin dato"]
an.fig\_total(a, Path("figuras"))
```

## Cómo agregar un análisis nuevo

1. Crea una carpeta `survey\_analysis\_imarpe/<tema>/` con un `\_\_init\_\_.py` y tu archivo `.py` de funciones.
2. En el `\_\_init\_\_.py` del tema exporta las funciones públicas (`from .miarchivo import mi\_funcion`).
3. Agrega una fila a la tabla de arriba y un ejemplo de uso.
4. Sube la versión en `pyproject.toml` y en `survey\_analysis\_imarpe/\_\_init\_\_.py`, haz commit y crea una etiqueta (`v0.3.0`).

Uso: `from survey\_analysis\_imarpe.<tema> import mi\_funcion`

## Desarrollo local

```bash
pip install -e .
```

