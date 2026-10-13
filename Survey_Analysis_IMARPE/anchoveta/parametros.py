"""
Parámetros del análisis de anchoveta (valores por defecto).

Este archivo solo contiene valores; las funciones están en graficos.py y leen estos valores.

Se pueden cambiar de dos maneras:
  1) Editando este archivo (si instalaste el paquete con `pip install -e .`; reinicia el kernel después).
  2) Desde tu propio script, sin tocar este archivo:
         import survey_analysis_imarpe.anchoveta as an
         an.TSM_FRIA = 17.5                        -> queda fijo hasta que lo cambies
         an.configurar(TSM_FRIA=17.5, FUENTE=14)   -> igual, varios a la vez
         an.ejecutar(archivo, FUENTE=14)           -> vale solo para esa llamada
"""

ARCHIVO = None                      # ruta del .xlsx / .csv (o se pasa a ejecutar)
CLASES = ["ANCP", "ANCG"]           # valores de Region_class a analizar

# nombres de columnas en la bitácora
COL_PROF = "Depth_mean"
COL_HORA = "Time_M"
COL_SSM = "SSM"                     # AJUSTAR si tu columna se llama distinto
COL_TSM = "TSM"                     # AJUSTAR si tu columna se llama distinto

# masas de agua (obligatorio fijar TSM_FRIA y TSM_CALIDA: no hay valor por defecto)
TSM_FRIA = None                     # TSM < TSM_FRIA            -> "Fría"
TSM_CALIDA = None                   # TSM >= TSM_CALIDA         -> "Cálida"; entre ambos "Transición"
SSM_ASS = 35.1                      # corte de salinidad que se dibuja como referencia
SEPARAR_POR_SSM = False             # True: crea el grupo "Cálida salina"
SSM_CORTE = 35.1                    # solo se usa si SEPARAR_POR_SSM = True

# horario
HORA_AMANECER = 6
HORA_ATARDECER = 18

# gráficos
MIN_N_VIOLIN = 5                    # mínimo de cardúmenes por hora para dibujar violín / mediana
PROF_MAX_EJE = None                 # None = automático según los datos
FUENTE = 12
TINTA = "#111111"
TINTA_2 = "#6b6a66"
COLOR_TOTAL = "#4c78a8"
COLORES = {"Fría": "#3b78b5", "Transición": "#8fb996", "Cálida": "#d9822b", "Cálida salina": "#b23a48"}
COLOR_CLASE = {"ANCP": "#4c78a8", "ANCG": "#e0a030"}
ORDEN = ["Fría", "Transición", "Cálida"]

_PARAMETROS = ["ARCHIVO", "CLASES", "COL_PROF", "COL_HORA", "COL_SSM", "COL_TSM", "TSM_FRIA", "TSM_CALIDA",
               "SSM_ASS", "SEPARAR_POR_SSM", "SSM_CORTE", "HORA_AMANECER", "HORA_ATARDECER", "MIN_N_VIOLIN",
               "PROF_MAX_EJE", "FUENTE", "TINTA", "TINTA_2", "COLOR_TOTAL", "COLORES", "COLOR_CLASE", "ORDEN"]
