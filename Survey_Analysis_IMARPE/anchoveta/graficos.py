"""
Anchoveta (Region_class = ANCP o ANCG): distribución horaria de la profundidad media de los
cardúmenes (Depth_mean vs hora de Time_M), total y separada por masa de agua (TSM / SSM).

Uso rápido:
    from survey_analysis_imarpe.anchoveta import ejecutar
    ejecutar("Bitacora_completa_2026-2.xlsx", salida="figuras", TSM_FRIA=..., TSM_CALIDA=...)

Los parámetros (columnas, cortes de TSM/SSM, ejes, colores...) están en parametros.py.

Genera (PNG 300 dpi + EPS) en la carpeta de salida:
  1_horaria_total          violines de Depth_mean por hora (ANCP + ANCG)
  2_masas_agua_TS_mapa     diagrama T-S con los umbrales y mapa de posiciones por grupo
  3_horaria_por_masa       violines por hora, un panel por masa de agua
  4_medianas_por_masa      mediana (y rango intercuartílico) por hora, todas las masas juntas
  5_horaria_por_clase      violines por hora, ANCP y ANCG en paneles separados
  6_medianas_por_clase_y_masa        mediana por hora y masa de agua, un panel por clase
  7_horaria_ANCP_ANCG_juntos         violines partidos por hora: ANCP (izq.) y ANCG (der.)
  8_horaria_ANCP_ANCG_por_masa       igual, un panel por masa de agua
  9_respaldo_cortes_TSM_SSM          histograma/densidad/mezcla de TSM con valles y cortes + corte SSM
  resumen_masas_agua.csv / resumen_por_clase_y_masa.csv
"""
import re
import unicodedata
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from . import parametros as P       # valores por defecto (archivo aparte)


def configurar(**kwargs):
    """Cambia parámetros (los de parametros.py); quedan fijos hasta que los vuelvas a cambiar.

    Ej.: configurar(TSM_FRIA=17.5, TSM_CALIDA=19.5, MIN_N_VIOLIN=10).
    COLORES y COLOR_CLASE se combinan con los actuales: basta indicar los colores que cambian.
    """
    nuevos = {}
    for k, v in kwargs.items():
        k = k.upper()
        if k not in P._PARAMETROS:
            raise ValueError(f"Parámetro desconocido: {k}. Válidos: {', '.join(P._PARAMETROS)}")
        nuevos[k] = v
    for k, v in nuevos.items():
        if k in ("COLORES", "COLOR_CLASE"):
            v = {**getattr(P, k), **v}
        setattr(P, k, v)
    if "SEPARAR_POR_SSM" in nuevos and "ORDEN" not in nuevos:
        orden = [m for m in P.ORDEN if m != "Cálida salina"]
        P.ORDEN = orden + (["Cálida salina"] if P.SEPARAR_POR_SSM else [])


def ver_parametros():
    """Devuelve un diccionario con los valores actuales de todos los parámetros."""
    return {k: getattr(P, k) for k in P._PARAMETROS}


def limpio(t):
    return re.sub(r"[^A-Z0-9]", "", unicodedata.normalize("NFKD", str(t)).upper())


# ----------------------------- datos -----------------------------
def cargar():
    ruta = Path(P.ARCHIVO)
    df = pd.read_csv(ruta, sep=None, engine="python") if ruta.suffix.lower() == ".csv" else pd.read_excel(ruta)
    df.columns = [str(c).replace("ï..", "").strip() for c in df.columns]
    ok = {limpio(c) for c in P.CLASES}
    a = df[df["Region_class"].map(limpio).isin(ok)].copy()
    a["clase"] = a["Region_class"].map(limpio)
    a[P.COL_PROF] = pd.to_numeric(a[P.COL_PROF], errors="coerce")
    for c in (P.COL_SSM, P.COL_TSM):
        a[c] = pd.to_numeric(a[c], errors="coerce")
    a["hora"] = pd.to_timedelta(a[P.COL_HORA].astype(str).str.strip(), errors="coerce").dt.components.hours
    n0 = len(a)
    a = a.dropna(subset=[P.COL_PROF, "hora"]).copy()
    a["hora"] = a["hora"].astype(int)
    print(f"Filas {'/'.join(P.CLASES)}: {n0} | con profundidad y hora válidas: {len(a)}")
    return a


def masa_de_agua(a):
    t, s = a[P.COL_TSM], a[P.COL_SSM]
    m = pd.Series("Transición", index=a.index)
    m[t < P.TSM_FRIA] = "Fría"
    m[t >= P.TSM_CALIDA] = "Cálida"
    if P.SEPARAR_POR_SSM:
        m[(t >= P.TSM_CALIDA) & (s >= P.SSM_CORTE)] = "Cálida salina"
    m[t.isna() | s.isna()] = "sin dato"
    return m


# ----------------------------- gráficos -----------------------------
def violines_por_hora(ax, d, color, titulo=None, n_arriba=True):
    """Un violín por hora (0-23) con mediana; eje Y invertido (profundidad)."""
    ax.axvspan(-0.5, P.HORA_AMANECER - 0.5, color="#000000", alpha=0.06, lw=0, zorder=0)
    ax.axvspan(P.HORA_ATARDECER - 0.5, 23.5, color="#000000", alpha=0.06, lw=0, zorder=0)
    meds, hs = [], []
    for h in range(24):
        v = d.loc[d["hora"] == h, P.COL_PROF].to_numpy(float)
        if len(v) == 0:
            continue
        if len(v) >= P.MIN_N_VIOLIN and np.ptp(v) > 0:
            p = ax.violinplot(v, positions=[h], widths=0.85, showextrema=False)
            for b in p["bodies"]:
                b.set_facecolor(color); b.set_edgecolor("#2b2b2b"); b.set_linewidth(0.5); b.set_alpha(1.0)
        ax.plot([h - 0.3, h + 0.3], [np.median(v)] * 2, color="#111111", lw=1.6, zorder=4,
                solid_capstyle="butt")
        meds.append(np.median(v)); hs.append(h)
        if n_arriba:
            ax.text(h, 1.008, f"{len(v)}", transform=ax.get_xaxis_transform(), ha="center", va="bottom",
                    fontsize=P.FUENTE - 5, color=P.TINTA_2)
    ax.set_ylim(P.PROF_MAX_EJE, 0)
    ax.set_xlim(-0.7, 23.7)
    ax.set_xticks(range(0, 24, 1))
    ax.set_xticklabels([f"{h:02d}" for h in range(24)], fontsize=P.FUENTE - 2)
    ax.grid(axis="y", color="#cfcdc6", lw=0.6, alpha=0.7, zorder=0)
    ax.set_axisbelow(True)
    if titulo:
        ax.set_title(titulo, loc="left", pad=20)


def guardar(fig, nombre, salida):
    for ext, kw in (("png", {"dpi": 300}), ("eps", {})):
        fig.savefig(salida / f"{nombre}.{ext}", facecolor="white", **kw)
    plt.close(fig)
    print("Gráfico:", salida / f"{nombre}.png")


def fig_total(a, salida):
    fig, ax = plt.subplots(figsize=(13, 6.5))
    violines_por_hora(ax, a, P.COLOR_TOTAL)
    ax.set_ylabel("Profundidad media del cardumen (m)")
    ax.set_title(f"Anchoveta ({' + '.join(P.CLASES)}): profundidad por hora del día   "
                 f"n = {len(a):,}".replace(",", " "), loc="left", pad=20)
    ax.set_xlabel("Hora local (Time_M)    ·    banda gris = noche · línea negra = mediana · "
                  "número sobre cada hora = n de cardúmenes")
    fig.tight_layout(); guardar(fig, "1_horaria_total", salida)


def fig_ts_mapa(a, salida):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6.2), gridspec_kw={"width_ratios": [1.15, 1]})
    for g in P.ORDEN:
        d = a[a["masa"] == g]
        if len(d):
            ax1.scatter(d[P.COL_SSM], d[P.COL_TSM], s=5, color=P.COLORES[g], linewidths=0, rasterized=True,
                        label=f"{g} (n={len(d):,})".replace(",", " "))
            ax2.scatter(d["Lon_M"], d["Lat_M"], s=5, color=P.COLORES[g], linewidths=0, rasterized=True)
    ymin, ymax = a[P.COL_TSM].min() - 0.4, a[P.COL_TSM].max() + 0.6
    ax1.set_ylim(ymin, ymax)
    for y in (P.TSM_FRIA, P.TSM_CALIDA):
        ax1.axhline(y, color="#6b6a66", ls="--", lw=0.9)
    if P.SEPARAR_POR_SSM:
        ax1.plot([P.SSM_CORTE] * 2, [P.TSM_CALIDA, ymax], color="#6b6a66", ls="--", lw=0.9)
    ax1.axvline(P.SSM_ASS, color="#111111", lw=1.2)
    ax1.text(P.SSM_ASS + 0.002, ymax - 0.1, f"SSM = {P.SSM_ASS}", fontsize=P.FUENTE - 3, va="top")
    ax1.set_xlabel("SSM (salinidad superficial)"); ax1.set_ylabel("TSM (°C)")
    ax1.set_title("Diagrama T-S de los cardúmenes de anchoveta", loc="left")
    ax1.legend(markerscale=3, frameon=False, loc="upper left", fontsize=P.FUENTE - 1)
    ax2.set_xlabel("Longitud"); ax2.set_ylabel("Latitud"); ax2.set_aspect("equal")
    ax2.set_title("Posición de los cardúmenes por grupo", loc="left")
    ax1.grid(color="#cfcdc6", lw=0.5, alpha=0.6); ax2.grid(color="#cfcdc6", lw=0.5, alpha=0.6)
    fig.tight_layout(); guardar(fig, "2_masas_agua_TS_mapa", salida)


def rejilla(n):
    """Paneles apilados (1 columna) si hay <= 3 grupos; 2x2 si hay 4. Devuelve (fig, axs 2D)."""
    if n <= 3:
        fig, axs = plt.subplots(n, 1, figsize=(15, 5.4 * n), sharey=True)
        return fig, np.atleast_1d(axs).reshape(n, 1)
    return plt.subplots(2, 2, figsize=(16, 10.5), sharey=True)


def fig_por_masa(a, salida, tag="", etiqueta=""):
    grupos = [g for g in P.ORDEN if (a["masa"] == g).any()]
    n = len(grupos)
    fig, axs = plt.subplots(n, 1, figsize=(14, 5.6 * n), sharey=True)
    axs = np.atleast_1d(axs)
    for ax, g in zip(axs, grupos):
        d = a[a["masa"] == g]
        violines_por_hora(ax, d, P.COLORES[g], f"{g}  (n = {len(d):,})".replace(",", " "))
        ax.set_ylabel("Profundidad media del cardumen (m)")
    axs[-1].set_xlabel("Hora local (Time_M)    ·    banda gris = noche · línea negra = mediana · número sobre cada hora = n")
    fig.suptitle(f"Anchoveta{etiqueta}: profundidad por hora según masa de agua (definida por TSM)", x=0.01, ha="left",
                 fontsize=P.FUENTE + 3, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.975)); guardar(fig, f"3_horaria_por_masa{tag}", salida)


def fig_medianas(a, salida):
    fig, ax = plt.subplots(figsize=(13, 6.5))
    ax.axvspan(-0.5, P.HORA_AMANECER - 0.5, color="#000000", alpha=0.06, lw=0)
    ax.axvspan(P.HORA_ATARDECER - 0.5, 23.5, color="#000000", alpha=0.06, lw=0)
    for g in P.ORDEN:
        d = a[a["masa"] == g]
        if d.empty:
            continue
        r = d.groupby("hora")[P.COL_PROF].agg(n="size", med="median",
                                            q1=lambda x: x.quantile(.25), q3=lambda x: x.quantile(.75))
        r = r.reindex(range(24))                       # horas sin datos -> huecos (no se unen con línea)
        r.loc[r["n"].fillna(0) < P.MIN_N_VIOLIN, ["med", "q1", "q3"]] = np.nan
        ax.fill_between(r.index, r.q1, r.q3, color=P.COLORES[g], alpha=0.15, lw=0)
        ax.plot(r.index, r.med, color=P.COLORES[g], lw=2.2, marker="o", ms=5, mec="white", mew=1.2,
                label=f"{g} (n={len(d):,})".replace(",", " "))
    ax.set_ylim(P.PROF_MAX_EJE, 0); ax.set_xlim(-0.7, 23.7)
    ax.set_xticks(range(24)); ax.set_xticklabels([f"{h:02d}" for h in range(24)], fontsize=P.FUENTE - 2)
    ax.set_xlabel(f"Hora local (Time_M)    ·    solo horas con n ≥ {P.MIN_N_VIOLIN} por grupo; las horas sin datos suficientes quedan en blanco")
    ax.set_ylabel("Profundidad media del cardumen (m)")
    ax.grid(axis="y", color="#cfcdc6", lw=0.6, alpha=0.7)
    ax.set_title("Anchoveta: mediana (línea) y rango intercuartílico (sombra) por hora y masa de agua", loc="left")
    ax.legend(frameon=False, loc="lower center", ncol=4, fontsize=P.FUENTE - 1, bbox_to_anchor=(0.5, 0.0))
    fig.tight_layout(); guardar(fig, "4_medianas_por_masa", salida)


def resumen(a, salida):
    dia = a["hora"].between(P.HORA_AMANECER, P.HORA_ATARDECER - 1)
    filas = []
    for g in ["Total"] + P.ORDEN:
        d = a if g == "Total" else a[a["masa"] == g]
        if d.empty:
            continue
        dd = dia.loc[d.index]
        filas.append({"grupo": g, "n": len(d), "TSM_media": d[P.COL_TSM].mean(), "SSM_media": d[P.COL_SSM].mean(),
                      "lat_media": d["Lat_M"].mean(), "lon_media": d["Lon_M"].mean(),
                      "n_dia": int(dd.sum()), "prof_mediana_dia": d.loc[dd, P.COL_PROF].median(),
                      "n_noche": int((~dd).sum()), "prof_mediana_noche": d.loc[~dd, P.COL_PROF].median()})
    r = pd.DataFrame(filas).round(2)
    r.to_csv(salida / "resumen_masas_agua.csv", index=False, sep=";", encoding="utf-8-sig")
    print(r.to_string(index=False))


def fig_clases(a, salida):
    """ANCP y ANCG en paneles separados: violines de profundidad por hora."""
    cl = [c for c in P.CLASES if (a["clase"] == limpio(c)).any()]
    fig, axs = plt.subplots(len(cl), 1, figsize=(13, 5.8 * len(cl)), sharey=True)
    axs = np.atleast_1d(axs)
    for ax, c in zip(axs, cl):
        d = a[a["clase"] == limpio(c)]
        violines_por_hora(ax, d, P.COLOR_CLASE.get(c, P.COLOR_TOTAL), f"{c}  (n = {len(d):,})".replace(",", " "))
        ax.set_ylabel("Profundidad media del cardumen (m)")
    axs[-1].set_xlabel("Hora local (Time_M)    ·    banda gris = noche · línea negra = mediana · "
                       "número sobre cada hora = n de cardúmenes")
    fig.tight_layout(); guardar(fig, "5_horaria_por_clase", salida)


def fig_medianas_clase(a, salida):
    """Mediana por hora y masa de agua, un panel por clase (ANCP / ANCG)."""
    cl = [c for c in P.CLASES if (a["clase"] == limpio(c)).any()]
    fig, axs = plt.subplots(1, len(cl), figsize=(8.5 * len(cl), 6.5), sharey=True)
    axs = np.atleast_1d(axs)
    for ax, c in zip(axs, cl):
        dc = a[a["clase"] == limpio(c)]
        ax.axvspan(-0.5, P.HORA_AMANECER - 0.5, color="#000000", alpha=0.06, lw=0)
        ax.axvspan(P.HORA_ATARDECER - 0.5, 23.5, color="#000000", alpha=0.06, lw=0)
        for g in P.ORDEN:
            d = dc[dc["masa"] == g]
            if d.empty:
                continue
            r = d.groupby("hora")[P.COL_PROF].agg(n="size", med="median")
            r = r.reindex(range(24))
            r.loc[r["n"].fillna(0) < P.MIN_N_VIOLIN, "med"] = np.nan
            ax.plot(r.index, r.med, color=P.COLORES[g], lw=2.2, marker="o", ms=5, mec="white", mew=1.2,
                    label=f"{g} (n={len(d):,})".replace(",", " "))
        ax.set_ylim(P.PROF_MAX_EJE, 0); ax.set_xlim(-0.7, 23.7)
        ax.set_xticks(range(0, 24, 2)); ax.set_xticklabels([f"{h:02d}" for h in range(0, 24, 2)])
        ax.set_xlabel("Hora local (Time_M)"); ax.grid(axis="y", color="#cfcdc6", lw=0.6, alpha=0.7)
        ax.set_title(f"{c}  (n = {len(dc):,})".replace(",", " "), loc="left")
        ax.legend(frameon=False, loc="lower center", fontsize=P.FUENTE - 2, ncol=2)
    axs[0].set_ylabel("Profundidad media del cardumen (m)")
    fig.suptitle(f"Mediana de profundidad por hora y masa de agua (solo horas con n ≥ {P.MIN_N_VIOLIN})",
                 x=0.01, ha="left", fontsize=P.FUENTE + 2, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.95)); guardar(fig, "6_medianas_por_clase_y_masa", salida)


def resumen_clase(a, salida):
    dia = a["hora"].between(P.HORA_AMANECER, P.HORA_ATARDECER - 1)
    filas = []
    for c in P.CLASES:
        for g in ["Total"] + P.ORDEN:
            d = a[a["clase"] == limpio(c)]
            d = d if g == "Total" else d[d["masa"] == g]
            if d.empty:
                continue
            dd = dia.loc[d.index]
            filas.append({"clase": c, "grupo": g, "n": len(d), "n_dia": int(dd.sum()),
                          "prof_mediana_dia": d.loc[dd, P.COL_PROF].median(), "n_noche": int((~dd).sum()),
                          "prof_mediana_noche": d.loc[~dd, P.COL_PROF].median(),
                          "TSM_media": d[P.COL_TSM].mean(), "SSM_media": d[P.COL_SSM].mean()})
    r = pd.DataFrame(filas).round(2)
    r.to_csv(salida / "resumen_por_clase_y_masa.csv", index=False, sep=";", encoding="utf-8-sig")
    print(r.to_string(index=False))


def violines_partidos(ax, d, titulo=None):
    """Por hora: ANCP (mitad izquierda) y ANCG (mitad derecha) en el mismo violín, con su mediana."""
    ax.axvspan(-0.5, P.HORA_AMANECER - 0.5, color="#000000", alpha=0.06, lw=0, zorder=0)
    ax.axvspan(P.HORA_ATARDECER - 0.5, 23.5, color="#000000", alpha=0.06, lw=0, zorder=0)
    lados = {limpio(P.CLASES[0]): -1, limpio(P.CLASES[1]): +1}          # ANCP = izquierda, ANCG = derecha
    for h in range(24):
        dh = d[d["hora"] == h]
        txt = []
        for c in P.CLASES:
            lado = lados[limpio(c)]
            v = dh.loc[dh["clase"] == limpio(c), P.COL_PROF].to_numpy(float)
            txt.append(str(len(v)))
            if len(v) == 0:
                continue
            col = P.COLOR_CLASE.get(c, P.COLOR_TOTAL)
            if len(v) >= P.MIN_N_VIOLIN and np.ptp(v) > 0:
                p = ax.violinplot(v, positions=[h], widths=0.9, showextrema=False)
                for b in p["bodies"]:
                    xy = b.get_paths()[0].vertices
                    xy[:, 0] = np.clip(xy[:, 0], -np.inf, h) if lado < 0 else np.clip(xy[:, 0], h, np.inf)
                    b.set_facecolor(col); b.set_edgecolor("#2b2b2b"); b.set_linewidth(0.5); b.set_alpha(1.0)
            x0, x1 = (h - 0.4, h) if lado < 0 else (h, h + 0.4)
            ax.plot([x0, x1], [np.median(v)] * 2, color="#111111", lw=1.8, zorder=4, solid_capstyle="butt")
        ax.text(h, 1.008, txt[0], transform=ax.get_xaxis_transform(), ha="center", va="bottom",
                fontsize=P.FUENTE - 5, color=P.TINTA_2)
        ax.text(h, 1.045, txt[1], transform=ax.get_xaxis_transform(), ha="center", va="bottom",
                fontsize=P.FUENTE - 5, color=P.TINTA_2)
    ax.set_ylim(P.PROF_MAX_EJE, 0); ax.set_xlim(-0.7, 23.7)
    ax.set_xticks(range(24)); ax.set_xticklabels([f"{h:02d}" for h in range(24)], fontsize=P.FUENTE - 2)
    ax.grid(axis="y", color="#cfcdc6", lw=0.6, alpha=0.7); ax.set_axisbelow(True)
    if titulo:
        ax.set_title(titulo, loc="left", pad=34)


def leyenda_clases(ax, **kw):
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(facecolor=P.COLOR_CLASE.get(c, P.COLOR_TOTAL), edgecolor="#2b2b2b", lw=0.5,
                             label=f"{c} (mitad {'izquierda' if i == 0 else 'derecha'})") for i, c in enumerate(P.CLASES)],
              frameon=False, fontsize=P.FUENTE - 1, **kw)


def fig_clases_juntas(a, salida):
    fig, ax = plt.subplots(figsize=(14, 7))
    violines_partidos(ax, a, f"Anchoveta: profundidad por hora, {P.CLASES[0]} y {P.CLASES[1]} en el mismo gráfico")
    ax.set_ylabel("Profundidad media del cardumen (m)")
    ax.set_xlabel(f"Hora local (Time_M)    ·    banda gris = noche · línea negra = mediana · "
                  f"n sobre cada hora: fila inferior = {P.CLASES[0]}, fila superior = {P.CLASES[1]}")
    leyenda_clases(ax, loc="lower center", ncol=2, bbox_to_anchor=(0.5, 0.0))
    fig.tight_layout(); guardar(fig, "7_horaria_ANCP_ANCG_juntos", salida)


def fig_clases_juntas_por_masa(a, salida):
    """Violines partidos ANCP / ANCG por hora, un panel por masa de agua (apilados). Guarda también cada masa sola."""
    grupos = [g for g in P.ORDEN if (a["masa"] == g).any()]
    fig, axs = plt.subplots(len(grupos), 1, figsize=(15, 6.2 * len(grupos)), sharey=True)
    axs = np.atleast_1d(axs)
    for ax, g in zip(axs, grupos):
        d = a[a["masa"] == g]
        violines_partidos(ax, d, f"{g}  (n = {len(d):,};  TSM {'< ' + str(P.TSM_FRIA) if g == 'Fría' else ('≥ ' + str(P.TSM_CALIDA) if g.startswith('Cálida') else str(P.TSM_FRIA) + '-' + str(P.TSM_CALIDA))} °C)".replace(",", " "))
        ax.set_ylabel("Profundidad media del cardumen (m)")
    axs[-1].set_xlabel("Hora local (Time_M)    ·    banda gris = noche · línea negra = mediana · "
                       f"n sobre cada hora: fila inferior = {P.CLASES[0]}, fila superior = {P.CLASES[1]} · n < {P.MIN_N_VIOLIN}: solo mediana")
    leyenda_clases(axs[0], loc="lower left", ncol=1)
    fig.tight_layout(); guardar(fig, "8_horaria_ANCP_ANCG_por_masa", salida)
    for g in grupos:                                       # una figura por masa de agua
        f2, ax = plt.subplots(figsize=(15, 6.8))
        d = a[a["masa"] == g]
        violines_partidos(ax, d, f"{g}  (n = {len(d):,})".replace(",", " "))
        ax.set_ylabel("Profundidad media del cardumen (m)"); ax.set_xlabel("Hora local (Time_M)")
        leyenda_clases(ax, loc="lower left", ncol=1)
        f2.tight_layout(); guardar(f2, f"8_{P.ORDEN.index(g) + 1}_{g.replace(' ', '_')}_ANCP_ANCG", salida)


def fig_justificacion(a, salida):
    """Figura 9: respaldo de los cortes de TSM (histograma, densidad, valles, mezcla gaussiana) y de SSM (35.1)."""
    from scipy.signal import argrelextrema
    from scipy.stats import gaussian_kde, norm
    try:
        from sklearn.mixture import GaussianMixture
    except Exception:
        GaussianMixture = None
    t, sa = a[P.COL_TSM].to_numpy(float), a[P.COL_SSM].to_numpy(float)
    u = a.drop_duplicates(subset=[P.COL_TSM, P.COL_SSM])                      # posiciones únicas (sin filas repetidas)
    tu = u[P.COL_TSM].to_numpy(float)
    xs = np.linspace(t.min() - 0.3, t.max() + 0.3, 700)
    kde = gaussian_kde(tu, bw_method=0.15)(xs)
    idx = argrelextrema(kde, np.less)[0]
    valles = xs[idx][(kde[idx] / kde.max()) < 0.1]                        # solo valles realmente profundos

    fig = plt.figure(figsize=(16, 10.5))
    gs = fig.add_gridspec(2, 2, height_ratios=[1.15, 1], hspace=0.32, wspace=0.18)
    ax = fig.add_subplot(gs[0, :])
    bins = np.arange(np.floor(t.min() * 4) / 4, t.max() + 0.25, 0.25)
    h, _ = np.histogram(t, bins=bins, density=True)
    for lo, hi, g in ((-99, P.TSM_FRIA, "Fría"), (P.TSM_FRIA, P.TSM_CALIDA, "Transición"), (P.TSM_CALIDA, 99, "Cálida")):
        m = (bins[:-1] >= lo) & (bins[:-1] < hi)
        ax.bar(bins[:-1][m], h[m], width=0.25, align="edge", color=P.COLORES[g], edgecolor="white", lw=0.6,
               label=f"{g}: n = {int(((t >= lo) & (t < hi)).sum()):,}".replace(",", " "))
    ax.plot(xs, kde, color=P.TINTA, lw=1.8, label="Densidad (kernel)")
    ax.set_ylim(0, 0.80)
    if GaussianMixture is not None:
        g2 = GaussianMixture(2, n_init=5, random_state=0).fit(tu.reshape(-1, 1))
        o = np.argsort(g2.means_.ravel())
        for k, ls in zip(o, ("--", ":")):
            mu, sd, w = g2.means_.ravel()[k], np.sqrt(g2.covariances_.ravel()[k]), g2.weights_[k]
            ax.plot(xs, w * norm.pdf(xs, mu, sd), color="#6b6a66", lw=1.6, ls=ls,
                    label=f"Mezcla de 2 gaussianas: media {mu:.1f} °C")
        ent = (xs > g2.means_.min()) & (xs < g2.means_.max())
        p = g2.predict_proba(xs[ent].reshape(-1, 1))[:, o[0]]
        c50 = xs[ent][np.argmin(abs(p - 0.5))]
        ax.axvline(c50, color="#6b6a66", lw=1.0, ls="-.")
        ax.text(c50 + 0.04, 0.30, f"{c50:.1f} °C: igual probabilidad\nde pertenecer a cada grupo",
                fontsize=P.FUENTE - 3, va="top", color=P.TINTA_2)
    for v in valles:
        ax.plot([v], [0], marker="^", ms=10, color="#111111", clip_on=False, zorder=5)
    for x0, txt in ((P.TSM_FRIA, f"corte Fría / Transición\n{P.TSM_FRIA:.1f} °C"),
                    (P.TSM_CALIDA, f"corte Transición / Cálida\n{P.TSM_CALIDA:.1f} °C")):
        ax.axvline(x0, color="#111111", lw=1.6)
        ax.text(x0 - 0.04, 0.47, txt, fontsize=P.FUENTE - 2, fontweight="bold", va="top", ha="right")
    ax.set_xlabel("TSM (°C)    ·    ▲ = valles de la densidad (" + ", ".join(f"{v:.2f}" for v in valles) + " °C)")
    ax.set_ylabel("Densidad de cardúmenes")
    ax.set_title("Separación por temperatura: dos poblaciones con un valle entre ellas", loc="left")
    ax.legend(frameon=False, loc="upper left", fontsize=P.FUENTE - 2, ncol=1)

    sbins = np.arange(34.95, 35.5, 0.01)
    ax2 = fig.add_subplot(gs[1, 0])
    ax2.axvspan(34.95, P.SSM_ASS, color="#000000", alpha=0.07, lw=0)
    ax2.hist(sa, bins=sbins, color=P.COLOR_TOTAL, edgecolor="white", lw=0.4)
    ax2.axvline(P.SSM_ASS, color="#111111", lw=1.6)
    ax2.set_ylim(0, 4300)
    n_bajo = int((sa < P.SSM_ASS).sum())
    ax2.text(P.SSM_ASS + 0.005, 4300 * 0.95, f"SSM ≥ {P.SSM_ASS}: {len(sa) - n_bajo:,} cardúmenes ({100 * (len(sa) - n_bajo) / len(sa):.0f} %)".replace(",", " "),
             fontsize=P.FUENTE - 2, fontweight="bold", va="top")
    ax2.text(34.955, 4300 * 0.95, f"SSM < {P.SSM_ASS}:\n{n_bajo} cardúmenes", fontsize=P.FUENTE - 2, va="top", color=P.TINTA_2)
    ax2.set_xlim(34.95, 35.5); ax2.set_xlabel("SSM (salinidad superficial)"); ax2.set_ylabel("Número de cardúmenes")
    ax2.set_title(f"Corte de salinidad en {P.SSM_ASS}: todos quedan de un mismo lado (mín. {sa.min():.2f})", loc="left")

    ax3 = fig.add_subplot(gs[1, 1])
    ax3.axvspan(34.95, P.SSM_ASS, color="#000000", alpha=0.07, lw=0)
    for lo, hi, g in ((-99, P.TSM_FRIA, "Fría"), (P.TSM_FRIA, P.TSM_CALIDA, "Transición"), (P.TSM_CALIDA, 99, "Cálida")):
        m = (t >= lo) & (t < hi)
        ax3.scatter(sa[m], t[m], s=5, color=P.COLORES[g], linewidths=0, rasterized=True)
    ax3.axvline(P.SSM_ASS, color="#111111", lw=1.6)
    for y in (P.TSM_FRIA, P.TSM_CALIDA):
        ax3.axhline(y, color="#111111", lw=1.0, ls="--")
    ax3.set_xlim(34.95, 35.5); ax3.set_ylim(t.min() - 0.4, t.max() + 0.5)
    ax3.set_xlabel("SSM (salinidad superficial)"); ax3.set_ylabel("TSM (°C)")
    ax3.set_title("Diagrama T-S con los cortes de TSM y SSM", loc="left")
    ax3.grid(color="#cfcdc6", lw=0.5, alpha=0.6); ax2.grid(axis="y", color="#cfcdc6", lw=0.5, alpha=0.6)
    fig.text(0.01, 0.005, "Densidad, valles y mezcla gaussiana calculados con posiciones únicas (pares TSM-SSM distintos) para no contar varias veces el mismo punto. "
             "TSM y SSM provienen de grillas de ~16 km.", fontsize=P.FUENTE - 3, color=P.TINTA_2)
    guardar(fig, "9_respaldo_cortes_TSM_SSM", salida)


# ----------------------------- orquestador -----------------------------
FIGURAS = {
    1: fig_total,                  # violines por hora (ANCP + ANCG)
    2: fig_ts_mapa,                # diagrama T-S y mapa
    3: fig_por_masa,               # violines por hora, un panel por masa de agua
    4: fig_medianas,               # medianas por hora y masa de agua
    5: fig_clases,                 # violines por hora, ANCP y ANCG separados
    6: fig_medianas_clase,         # medianas por hora y masa, un panel por clase
    7: fig_clases_juntas,          # violines partidos ANCP | ANCG
    8: fig_clases_juntas_por_masa, # violines partidos por masa de agua (+ una figura por masa)
    9: fig_justificacion,          # respaldo de los cortes de TSM y SSM
}


def ejecutar(archivo=None, salida="salida_anchoveta", figuras="todas", tablas=True, **config):
    """Corre el análisis y guarda figuras y tablas en `salida`.

    archivo : ruta al .xlsx o .csv de la bitácora (déjalo vacío si ya fijaste ARCHIVO).
    salida  : carpeta donde se guardan los gráficos (se crea si no existe).
    figuras : "todas" (por defecto) o una lista con los números de las figuras que quieres, p. ej. [1, 4, 9].
              1 total · 2 T-S y mapa · 3 por masa · 4 medianas · 5 por clase · 6 medianas por clase
              7 ANCP|ANCG juntos · 8 ANCP|ANCG por masa · 9 respaldo de cortes TSM/SSM
    tablas  : True (por defecto) guarda los CSV de resumen; False no los genera.
    config  : parámetros SOLO para esta llamada, p. ej. TSM_FRIA=17.5, MIN_N_VIOLIN=10. Los que fijaste antes
              (an.X = valor, configurar(...) o editando parametros.py) se usan como base y no se modifican.
    Devuelve el DataFrame procesado (con columnas 'clase', 'hora' y 'masa').
    """
    if isinstance(figuras, str):
        if figuras.lower() != "todas":
            raise ValueError('figuras debe ser "todas" o una lista de números, p. ej. [1, 4, 9]')
        elegidas = sorted(FIGURAS)
    else:
        elegidas = sorted({int(f) for f in (figuras if hasattr(figuras, "__iter__") else [figuras])})
        malas = [f for f in elegidas if f not in FIGURAS]
        if malas:
            raise ValueError(f"Figuras inexistentes: {malas}. Válidas: {sorted(FIGURAS)}")
    if archivo is not None:
        config = {**config, "ARCHIVO": archivo}
    previos = {k: getattr(P, k) for k in P._PARAMETROS}    # lo de esta llamada no se arrastra a las siguientes
    try:
        configurar(**config)
        if P.ARCHIVO is None:
            raise ValueError("Indica el archivo: ejecutar('bitacora.xlsx') o an.ARCHIVO = 'bitacora.xlsx'")
        if P.TSM_FRIA is None or P.TSM_CALIDA is None:
            raise ValueError("Debes fijar TSM_FRIA y TSM_CALIDA, p. ej. an.TSM_FRIA = 17.5 y an.TSM_CALIDA = 19.5")
        if len(P.CLASES) != 2:
            raise ValueError("CLASES debe tener exactamente 2 valores (los violines partidos comparan dos clases).")
        if P.SEPARAR_POR_SSM and "Cálida salina" not in P.ORDEN:
            configurar(ORDEN=list(P.ORDEN) + ["Cálida salina"])
        salida = Path(salida)
        salida.mkdir(parents=True, exist_ok=True)

        a = cargar()
        a["masa"] = masa_de_agua(a)
        a = a[a["masa"] != "sin dato"].copy()      # sin TSM o SSM no se puede clasificar
        print(f"Con TSM y SSM válidos: {len(a)}")
        if a.empty:
            raise ValueError("No quedaron filas con TSM y SSM válidos; revisa COL_TSM / COL_SSM.")
        if P.PROF_MAX_EJE is None:
            configurar(PROF_MAX_EJE=float(np.ceil(a[P.COL_PROF].max() / 10) * 10))
        with plt.rc_context({"font.size": P.FUENTE}):
            for n in elegidas:
                FIGURAS[n](a, salida)
        if tablas:
            resumen(a, salida)
            resumen_clase(a, salida)
        return a
    finally:
        for k, v in previos.items():
            setattr(P, k, v)
