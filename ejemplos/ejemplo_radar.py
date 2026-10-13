"""Ejemplo: radar de la climatología vs. uno o varios cruceros (bitácoras 120 kHz).

Antes de ejecutar, cambia las rutas. La climatología es el Excel que genera el script de climatología
(hoja "promedios").
"""
from survey_analysis_imarpe.bitacoras import radar_climatologia

fig, tabla = radar_climatologia(
    climatologia=r"d:\OneDrive - imarpe.gob.pe\DanielTrabajo\DanielGeneral\CodigosGenerales\CodigosPython\DatosVarios_Crucero\Climatologia_Regiones_2004-2026.xlsx",
    # Una ruta, una lista de rutas, o un diccionario {"etiqueta": ruta}:
    bitacoras={"Verano 202026": r"d:\OneDrive - imarpe.gob.pe\Data_AFH - Documentos\BitacorasVarias\pelagicos\2026\Cr2602-04\Bitacora Regiones 120 kHz Cr 2602-04_total.csv",
               "Verano 2023": r"d:\OneDrive - imarpe.gob.pe\Data_AFH - Documentos\BitacorasVarias\pelagicos\2023\Cr 2302-03\Bitacora Regiones 120 kHz Cr2302-03 final.csv"},
    # Con la base compilada:  bitacoras=r"D:\ruta\bitacoras_compiladas.csv.gz", cruceros=["Cr 1202-04", "Cr 2609-10"],
    periodo="todo",              # "todo" | "dia" | "noche"   o una lista: ["todo", "dia", "noche"]
    grupo="ANC",               # "ANC" | "ANCP" | "ANCG"
    estacion="verano",          # estación de la climatología: "todas" | "verano" | "primavera"
    # ---- tamaños y estilo (todos opcionales) ----
    figsize=None,               # (ancho, alto) en pulgadas; None = automático
    fuente=15, fuente_titulo=15, fuente_panel=13, fuente_ejes=8.5, fuente_radial=7.5,
    fuente_leyenda=14, fuente_nota=9,
    grosor_linea=2.2, tam_marcador=6, alfa_relleno=0.14,
    valores_en_ejes="no",       # "no" | "clim" | "todos" | "auto"
    mostrar_ticks_radiales=False,   # False oculta los números 50/100/150
    mostrar_n=False,
    # ---- salida ----
    salida=r"c:\Users\dgihsa\Downloads\Resultados", formatos=("png", "pdf"), dpi=300,
    mostrar=True,
)
print(tabla)
