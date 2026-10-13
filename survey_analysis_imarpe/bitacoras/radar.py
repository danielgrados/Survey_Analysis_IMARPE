"""radar_climatologia: gráfico de araña (radar) de la climatología vs. uno o varios cruceros.

    from survey_analysis_imarpe.bitacoras import radar_climatologia

    fig, tabla = radar_climatologia(
        climatologia=r"C:\\...\\climatologia_bitacoras_120.xlsx",      # hoja "promedios"
        bitacoras=[r"C:\\...\\Bitacora_1202-04.csv", r"C:\\...\\Bitacora_2609-10.xlsx"],
        periodo="dia",            # "todo" | "dia" | "noche"  (o una lista: ["todo", "dia", "noche"])
        grupo="ANC",              # "ANC" | "ANCP" | "ANCG"
    )

Cada eje es una variable; 100 = promedio climatológico (círculo punteado). Cada crucero se dibuja como
índice = 100 * (promedio del crucero / promedio climatológico). Para Sv_mean (dB) el índice se calcula en escala
lineal: 100 * 10^((Sv_crucero - Sv_clim)/10).

`bitacoras` acepta una ruta, una lista de rutas, un diccionario {"etiqueta": ruta} o la base compilada
"bitacoras_compiladas.csv.gz" junto con cruceros=["Cr 1202-04", ...].
IMPORTANTE: hora_dia y desfase_horas deben ser los mismos que usaste al generar la climatología.
"""
import os
import textwrap

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .lectura import CLASES_ANC, VARIABLES, _cargar_cruceros

ETIQUETAS_EJES = {"Corrected_length": "Largo\ncorregido", "Corrected_thickness": "Espesor\ncorregido",
                  "Corrected_area": "Área\ncorregida", "Sv_mean": "Sv medio\n(dB)",
                  "Depth_mean": "Profundidad\nmedia", "Height_mean": "Altura\nmedia",
                  "3D_school_volume": "Volumen 3D\ndel cardumen"}
COLORES = ["#eb6834", "#1baf7a", "#6250d6", "#eda100", "#e87ba4", "#008300", "#e34948"]  # cruceros, en orden
COLOR_CLIM = "#2a78d6"
TINTA, TINTA_2, GRIS = "#111111", "#6b6a66", "#d6d5cf"
PERIODOS = {"todo": ("general", "Todo"), "total": ("general", "Todo"), "general": ("general", "Todo"),
            "dia": ("dia", "Día"), "día": ("dia", "Día"), "noche": ("noche", "Noche")}



def _promedios(tabla, grupo, periodo, hora_dia):
    t = tabla[tabla["clase"].isin(CLASES_ANC)] if grupo == "ANC" else tabla[tabla["clase"] == grupo]
    h = t["hora"]
    if periodo == "dia":
        t = t[(h >= hora_dia[0]) & (h < hora_dia[1])]
    elif periodo == "noche":
        t = t[h.notna() & ~((h >= hora_dia[0]) & (h < hora_dia[1]))]
    return t[VARIABLES].mean(), len(t)


def _indice(valor, clim, var):
    if pd.isna(valor) or pd.isna(clim):
        return np.nan
    return 100 * 10 ** ((valor - clim) / 10) if var == "Sv_mean" else 100 * valor / clim


# ----------------------------- función principal -----------------------------
def radar_climatologia(
        climatologia, bitacoras, periodo="todo", grupo="ANC", estacion="todas", cruceros=None,
        variables=None, etiquetas_ejes=None, desfase_horas=0, hora_dia=(6, 18),
        # ---- salida ----
        salida="salida_radar", nombre=None, formatos=("png", "pdf"), dpi=300, guardar=True, mostrar=True,
        # ---- textos ----
        titulo=None, nota=None, mostrar_nota=True, valores_en_ejes="auto", mostrar_n=True,
        # ---- tamaños (todos modificables) ----
        figsize=None, fuente=10, fuente_titulo=15, fuente_panel=13, fuente_ejes=8.5, fuente_radial=7.5,
        fuente_leyenda=11, fuente_nota=9, pad_ejes=14, pad_panel=34,
        # ---- líneas y colores ----
        grosor_linea=2.2, grosor_clim=2.0, tam_marcador=6, alfa_relleno=0.14, alfa_clim=0.10,
        color_clim=COLOR_CLIM, colores=None, rmax=None, ticks_radiales=None, mostrar_ticks_radiales=True,
        # ---- leyenda ----
        leyenda_loc="lower center", leyenda_bbox=(0.5, 0.045), leyenda_ncol=None, leyenda=True,
        margen=(0, 0.14, 1, 0.96)):
    """
    Dibuja el radar de la climatología vs. uno o más cruceros. Devuelve (figura, tabla con los valores e índices).

    Qué dibujar
      climatologia   ruta del Excel generado por el script de climatología (hoja "promedios").
      bitacoras      ruta | lista de rutas | {"etiqueta": ruta} | base compilada .csv.gz (ver arriba).
      cruceros       con la base compilada: lista de cruceros a comparar (None = todos).
      periodo        "todo", "dia" o "noche"; o una lista ["todo", "dia", "noche"] para varios paneles.
      grupo          "ANC", "ANCP" o "ANCG".     estacion  "todas", "verano" o "primavera" (de la climatología).
      variables      subconjunto/orden de las 7 variables.  etiquetas_ejes  {"Depth_mean": "Prof."} para renombrar.
      desfase_horas, hora_dia   iguales a los de la climatología.

    Tamaños y estilo
      figsize, fuente (base), fuente_titulo, fuente_panel, fuente_ejes (nombres de variables), fuente_radial
      (números 50/100/150), fuente_leyenda, fuente_nota, pad_ejes (separación de las etiquetas), pad_panel.
      grosor_linea, grosor_clim, tam_marcador, alfa_relleno, alfa_clim, color_clim, colores (lista, uno por crucero).
      rmax (radio máximo; por defecto automático y común a todos los paneles), ticks_radiales (p. ej. [50, 100, 150]).
      leyenda_loc, leyenda_bbox, leyenda_ncol, leyenda=False para ocultarla; margen=(izq, abajo, der, arriba) en 0-1.
      valores_en_ejes: "auto", "todos", "clim" o "no" (valores reales bajo el nombre de cada variable).
    """
    variables = list(variables) if variables else list(VARIABLES)
    malas = [v for v in variables if v not in VARIABLES]
    if malas:
        raise ValueError(f"Variables desconocidas: {malas}. Opciones: {VARIABLES}")
    grupo = str(grupo).upper()
    if grupo not in {"ANC", "ANCP", "ANCG"}:
        raise ValueError("grupo debe ser 'ANC', 'ANCP' o 'ANCG'")
    lista = [periodo] if isinstance(periodo, str) else list(periodo)
    if len(lista) == 1 and str(lista[0]).lower() in ("los3", "todos", "3", "tres"):
        lista = ["todo", "dia", "noche"]
    try:
        pers = [PERIODOS[str(p).lower()] for p in lista]
    except KeyError as e:
        raise ValueError(f"periodo desconocido: {e}. Usa 'todo', 'dia' o 'noche'.")
    etq = {**ETIQUETAS_EJES, **(etiquetas_ejes or {})}

    clim = pd.read_excel(climatologia, sheet_name="promedios")
    clim = clim[(clim["grupo"] == grupo) & (clim["estacion"] == estacion)].set_index("periodo")
    if clim.empty:
        raise ValueError(f"La climatología no tiene filas para grupo={grupo}, estacion={estacion}.")

    datos = _cargar_cruceros(bitacoras, cruceros, desfase_horas)
    nombres = list(datos)
    cols = list(colores) if colores else COLORES
    if len(nombres) > len(cols):
        raise ValueError(f"Hay {len(nombres)} cruceros y solo {len(cols)} colores; pasa más en 'colores'.")

    # ---- cálculo ----
    filas, idx, valores, ns = [], {}, {}, {}
    for per, _ in pers:
        for nom in nombres:
            prom, n = _promedios(datos[nom], grupo, per, hora_dia)
            ns[(per, nom)] = n
            valores[(per, nom)] = prom
            idx[(per, nom)] = [_indice(prom[v], clim.loc[per, v], v) for v in variables]
            if n == 0:
                print(f"  ! {nom}: sin cardúmenes {grupo} en el periodo '{per}'; no se dibuja.")
            for v, i in zip(variables, idx[(per, nom)]):
                filas.append({"periodo": per, "crucero": nom, "variable": v, "climatologia": clim.loc[per, v],
                              "crucero_valor": prom[v], "indice(clim=100)": i, "n": n})
    tabla = pd.DataFrame(filas)

    todos = np.array([i for lst in idx.values() for i in lst], dtype=float)
    r_max = rmax if rmax else max(150.0, (np.nanmax(todos) if np.isfinite(todos).any() else 150) * 1.12)
    ang = np.linspace(0, 2 * np.pi, len(variables), endpoint=False)
    cierre = lambda a: np.concatenate([a, a[:1]])
    if valores_en_ejes == "auto":
        valores_en_ejes = "todos" if len(nombres) == 1 else "clim"
    if ticks_radiales is None:
        ticks_radiales = [t for t in (50, 100, 150, 200, 300, 400, 500) if t < r_max]

    # ---- dibujo ----
    np_ = len(pers)
    if figsize is None:
        figsize = (8.2, 7.6) if np_ == 1 else (5.4 * np_ - 0.2, 7.0)
    with plt.rc_context({"font.size": fuente, "font.family": "DejaVu Sans"}):
        fig, axs = plt.subplots(1, np_, figsize=figsize, subplot_kw={"projection": "polar"}, squeeze=False)
        for ax, (per, tit) in zip(axs[0], pers):
            ax.set_theta_offset(np.pi / 2)
            ax.set_theta_direction(-1)
            ax.set_ylim(0, r_max)
            ax.set_yticks(ticks_radiales)
            ax.set_yticklabels([])
            ax.grid(color=GRIS, lw=0.8)
            ax.spines["polar"].set_color(GRIS)
            ax.plot(cierre(ang), np.full(len(ang) + 1, 100), color=color_clim, lw=grosor_clim, ls="--", zorder=2,
                    label="Climatología (=100)")
            ax.fill(cierre(ang), np.full(len(ang) + 1, 100), color=color_clim, alpha=alfa_clim, zorder=1)
            for k, nom in enumerate(nombres):
                if ns[(per, nom)] == 0:
                    continue
                y = cierre(np.array(idx[(per, nom)], dtype=float))
                lab = nom + (f" (n={ns[(per, nom)]:,})" if (mostrar_n and np_ == 1) else "")
                ax.plot(ang_c := cierre(ang), y, color=cols[k], lw=grosor_linea, marker="o", ms=tam_marcador,
                        mfc=cols[k], mec="white", mew=1.5, zorder=3 + k, label=lab)
                ax.fill(ang_c, np.nan_to_num(y), color=cols[k], alpha=alfa_relleno, zorder=1)
            etiquetas = []
            for j, v in enumerate(variables):
                txt = etq[v]
                if valores_en_ejes == "todos":
                    vals = "  ".join(f"{valores[(per, nom)][v]:,.1f}" for nom in nombres)
                    txt += f"\n{vals} ({clim.loc[per, v]:,.1f})"
                elif valores_en_ejes == "clim":
                    txt += f"\nclim: {clim.loc[per, v]:,.1f}"
                etiquetas.append(txt)
            ax.set_xticks(ang)
            ax.set_xticklabels(etiquetas, color=TINTA, fontsize=fuente_ejes)
            ax.tick_params(axis="x", pad=pad_ejes)
            n_txt = f"  (n = {ns[(per, nombres[0])]:,})" if (mostrar_n and len(nombres) == 1 and np_ > 1) else ""
            ax.set_title(tit + n_txt, color=TINTA, fontsize=fuente_panel, pad=pad_panel, fontweight="bold")
            if mostrar_ticks_radiales:
                for r in ticks_radiales:
                    ax.text(np.deg2rad(8), r, f"{r:g}", color=TINTA_2, fontsize=fuente_radial, ha="left", va="bottom")
        if leyenda:
            h, l = axs[0][0].get_legend_handles_labels()
            fig.legend(h, l, loc=leyenda_loc, bbox_to_anchor=leyenda_bbox, ncol=leyenda_ncol or min(len(l), 4),
                       frameon=False, fontsize=fuente_leyenda)
        fig.suptitle(titulo or f"{grupo} · comparación con la climatología ({estacion})", color=TINTA,
                     fontsize=fuente_titulo, y=0.99)
        if mostrar_nota:
            texto_nota = nota or ("Índice: 100 = promedio climatológico. Sv: índice en escala lineal."
                                  + (" Bajo cada variable: valores reales de cada crucero (climatología)."
                                     if valores_en_ejes == "todos" else
                                     " Bajo cada variable: valor climatológico." if valores_en_ejes == "clim" else ""))
            texto_nota = textwrap.fill(texto_nota, width=max(30, int(figsize[0] * 72 / fuente_nota * 1.7)))
            fig.text(0.5, 0.012, texto_nota, ha="center", va="bottom", color=TINTA_2, fontsize=fuente_nota)
        fig.tight_layout(rect=margen)

        if guardar:
            os.makedirs(salida, exist_ok=True)
            base = nombre or f"radar_{grupo}_{'-'.join(p for p, _ in pers)}_{estacion}"
            for ext in formatos:
                ruta = os.path.join(salida, f"{base}.{ext}")
                fig.savefig(ruta, dpi=dpi, facecolor="white")
            tabla.to_csv(os.path.join(salida, f"{base}.csv"), index=False, sep=";", encoding="utf-8-sig")
            print(f"Guardado en: {os.path.abspath(salida)}  ({base}.*)")
        if mostrar:
            plt.show()
    return fig, tabla


if __name__ == "__main__":
    # Ejemplo: cambia las rutas y ejecuta
    radar_climatologia(
        climatologia=r"C:\ruta\climatologia_bitacoras_120.xlsx",
        bitacoras=[r"C:\ruta\Bitacora_Regiones_120_kHz_1202-04.csv"],
        periodo="todo", grupo="ANC")
