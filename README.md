# Survey_Analysis_IMARPE

Colección de funciones de análisis de cruceros y evaluaciones. Cada análisis es un subpaquete independiente.

| Subpaquete | Qué hace |
|---|---|
| `survey_analysis_imarpe.anchoveta` | Distribución horaria de profundidad de anchoveta (ANCP/ANCG) por masa de agua (TSM/SSM) |

## Instalación

```bash
pip install git+https://github.com/danielgrados/Survey_Analysis_IMARPE.git
# versión fija (recomendado para reproducibilidad):
pip install git+https://github.com/danielgrados/Survey_Analysis_IMARPE.git@v0.1.0
```

Para actualizar a una etiqueta nueva (por ejemplo `v0.1.1`):

```bash
pip install --upgrade --force-reinstall --no-deps git+https://github.com/danielgrados/Survey_Analysis_IMARPE.git@v0.1.1
```

## Uso: anchoveta

Los parámetros se cambian desde tu propio script, sin tocar el paquete:

```python
import survey_analysis_imarpe.anchoveta as an

an.ARCHIVO = r"D:\ruta\Bitacora_completa_2026-2.xlsx"   # .xlsx o .csv
an.TSM_FRIA = 17.5          # EJEMPLO: usa tus propios cortes (obligatorios)
an.TSM_CALIDA = 19.5
an.COLORES["Fría"] = "#1f77b4"   # cambiar un solo color

a = an.ejecutar(salida=r"D:\ruta\figuras")
```

En la carpeta `ejemplos/` hay un script completo con todos los parámetros listos para editar.

### Cómo se cambian los parámetros

| Forma | Alcance |
|---|---|
| `an.TSM_FRIA = 17.5` | Queda fijo hasta que lo cambies |
| `an.configurar(TSM_FRIA=17.5, FUENTE=14)` | Igual, varios a la vez |
| `an.ejecutar(archivo, TSM_FRIA=17.5)` | Vale solo para esa llamada; la siguiente vuelve a lo fijado antes |
| Editar `survey_analysis_imarpe/anchoveta/parametros.py` | Cambia los valores por defecto (útil si instalaste con `pip install -e .`; reinicia el kernel después) |

`an.ver_parametros()` devuelve un diccionario con los valores actuales. Un nombre en mayúsculas que no sea un
parámetro (por ejemplo `an.TSM_FRIAA = 1`) da error, para detectar errores de tipeo.

### Parámetros

| Parámetro | Por defecto | Qué hace |
|---|---|---|
| `ARCHIVO` | `None` | Ruta del .xlsx / .csv (o se pasa a `ejecutar`) |
| `CLASES` | `["ANCP", "ANCG"]` | Valores de `Region_class` a analizar (exactamente 2; la primera va a la izquierda en los violines partidos) |
| `COL_PROF`, `COL_HORA` | `"Depth_mean"`, `"Time_M"` | Columnas de profundidad y hora |
| `COL_SSM`, `COL_TSM` | `"SSM"`, `"TSM"` | Columnas de salinidad y temperatura |
| `TSM_FRIA` | `None` (obligatorio) | TSM menor que este valor: masa "Fría" |
| `TSM_CALIDA` | `None` (obligatorio) | TSM mayor o igual: "Cálida"; entre ambos: "Transición" |
| `SSM_ASS` | `35.1` | Corte de salinidad que se dibuja como referencia |
| `SEPARAR_POR_SSM` | `False` | `True` crea el grupo "Cálida salina" |
| `SSM_CORTE` | `35.1` | Corte de SSM (solo si `SEPARAR_POR_SSM`) |
| `HORA_AMANECER`, `HORA_ATARDECER` | `6`, `18` | Limitan la banda de noche y el cálculo día/noche |
| `MIN_N_VIOLIN` | `5` | Mínimo de cardúmenes por hora para dibujar violín o mediana |
| `PROF_MAX_EJE` | `None` | Profundidad máxima del eje (`None` = automática) |
| `FUENTE` | `12` | Tamaño de letra base |
| `TINTA`, `TINTA_2`, `COLOR_TOTAL` | `"#111111"`, `"#6b6a66"`, `"#4c78a8"` | Colores de texto y de la figura total |
| `COLORES` | Fría, Transición, Cálida, Cálida salina | Color de cada masa de agua (basta indicar los que cambian) |
| `COLOR_CLASE` | ANCP, ANCG | Color de cada clase (basta indicar los que cambian) |
| `ORDEN` | `["Fría", "Transición", "Cálida"]` | Masas de agua que se grafican y su orden |

Columnas fijas que debe tener la bitácora además de las anteriores: `Region_class`, `Lat_M`, `Lon_M`.

### Elegir figuras

```python
an.ejecutar(salida="figuras", figuras=[1, 4, 9])                # solo 1, 4 y 9
an.ejecutar(salida="figuras", figuras=[8], tablas=False)        # solo la 8, sin CSV
```

| N.º | Figura |
|---|---|
| 1 | Violines por hora (ANCP + ANCG) |
| 2 | Diagrama T-S y mapa de posiciones |
| 3 | Violines por hora, un panel por masa de agua |
| 4 | Medianas por hora y masa de agua |
| 5 | Violines por hora, ANCP y ANCG separados |
| 6 | Medianas por hora y masa, un panel por clase |
| 7 | Violines partidos ANCP / ANCG |
| 8 | Violines partidos por masa de agua (y una figura por cada masa) |
| 9 | Respaldo de los cortes de TSM y SSM |

Por defecto (`figuras="todas"`) se generan las 9, más los CSV de resumen (`tablas=True`).

### Usar una sola función

```python
import survey_analysis_imarpe.anchoveta as an
from pathlib import Path

an.configurar(ARCHIVO="bitacora.xlsx", TSM_FRIA=17.5, TSM_CALIDA=19.5, PROF_MAX_EJE=60)
a = an.cargar()
a["masa"] = an.masa_de_agua(a)
a = a[a["masa"] != "sin dato"]
an.fig_total(a, Path("figuras"))
```

### Estructura del subpaquete

- `parametros.py`: solo los valores por defecto (columnas, cortes de TSM/SSM, ejes, colores...). No tiene funciones.
- `graficos.py`: solo las funciones; leen los valores desde `parametros.py`.
- `__init__.py`: expone todo para que puedas usar `an.TSM_FRIA = 17.5`.

## Cómo agregar un análisis nuevo

1. Crea una carpeta `survey_analysis_imarpe/<tema>/` con un `__init__.py` y tu archivo `.py` de funciones.
2. En el `__init__.py` del tema exporta las funciones públicas (`from .miarchivo import mi_funcion`).
3. Agrega una fila a la tabla de arriba y un ejemplo de uso.
4. Sube la versión en `pyproject.toml` y en `survey_analysis_imarpe/__init__.py`, haz commit y crea una etiqueta nueva.

Uso: `from survey_analysis_imarpe.<tema> import mi_funcion`

## Desarrollo local

```bash
pip install -e .
```
