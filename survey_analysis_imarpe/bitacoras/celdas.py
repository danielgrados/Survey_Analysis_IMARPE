"""
descriptores_celdas: descriptores espaciales y de densidad de la bitácora de CELDAS 120 kHz, calculados por archivo.

    from survey_analysis_imarpe.bitacoras import descriptores_celdas

    tabla = descriptores_celdas(
        r"D:\\...\\Bitacora_Celdas_120_kHz_Cr2202-04.xlsx",         # un archivo, una lista, o {"Cr 2202-04": ruta, ...}
        variables=["ANC", "ANCP", "ANCG"],
    )

Devuelve un DataFrame con UNA FILA POR ARCHIVO x VARIABLE y estas columnas (más `rango_latitud`, que indica el
filtro usado con lat_rango=(-16, -3), o "todo"):

  Densidad        NASC_total, NASC_medio_todas, NASC_medio_positivas, NASC_mediano_positivas, CV_positivas,
                  NASC_maximo, indice_abundancia_m2 (= suma de NASC x área de la celda)
  Ocupación       n_celdas, celdas_positivas, pct_celdas_positivas, area_ocupada_mn2, area_prospectada_mn2
  Localización    x_cg_grados (longitud del centro de gravedad), y_cg_grados (latitud), inercia_km2
  Dispersión      eje_principal_km, eje_secundario_km, isotropia, orientacion_grados (desde el norte)
  Concentración   area_equivalente_mn2 (EA), D95_mn2, gini

Con bootstrap=N (por TRANSECTOS, porque las celdas de un transecto no son independientes) agrega, para cada
indicador, las columnas <indicador>_ic_inf y <indicador>_ic_sup (IC al 95 %).

La celda es positiva si NASC > umbral_positivo. Los ceros se incluyen en los índices espaciales (definen el área
ocupada). El área de cada celda es largo_celda_mn x espacio_transectos_mn (por defecto 1 mn x 10 mn).
Requiere pandas, numpy y openpyxl.
"""
import os
from pathlib import Path

import numpy as np
import pandas as pd

INDICADORES = ["NASC_total", "NASC_medio_todas", "NASC_medio_positivas", "NASC_mediano_positivas", "CV_positivas",
               "NASC_maximo", "indice_abundancia_m2",
               "n_celdas", "celdas_positivas", "pct_celdas_positivas", "area_ocupada_mn2", "area_prospectada_mn2",
               "x_cg_grados", "y_cg_grados", "inercia_km2", "eje_principal_km", "eje_secundario_km", "isotropia",
               "orientacion_grados", "area_equivalente_mn2", "D95_mn2", "gini"]
_R = 6371.0


# ----------------------------- cálculos -----------------------------
def _proyectar_km(lon, lat, lon0):
    """Proyección sinusoidal (equivalente en área), en km. Suficiente para 3.5 a 18 °S."""
    return _R * np.deg2rad(lon - lon0) * np.cos(np.deg2rad(lat)), _R * np.deg2rad(lat)


def _a_grados(xcg, ycg, lon0):
    lat = np.degrees(ycg / _R)
    return lon0 + np.degrees(xcg / (_R * np.cos(np.deg2rad(lat)))), lat


def _gini(z):
    z = np.sort(np.asarray(z, float))
    n = len(z)
    return np.nan if n == 0 or z.sum() == 0 else float((2 * np.sum(np.arange(1, n + 1) * z) / (n * z.sum())) - (n + 1) / n)


def _espaciales(x, y, z, lon0, area_celda):
    """Índices de Woillez et al. (2007), ponderados por z (incluye ceros). x, y en km."""
    S = z.sum()
    xcg, ycg = (z * x).sum() / S, (z * y).sum() / S
    dx, dy = x - xcg, y - ycg
    C = np.array([[(z * dx * dx).sum(), (z * dx * dy).sum()], [(z * dx * dy).sum(), (z * dy * dy).sum()]]) / S
    val, vec = np.linalg.eigh(C)
    acum = np.cumsum(np.sort(z)[::-1]) / S
    lon_cg, lat_cg = _a_grados(xcg, ycg, lon0)
    return {"x_cg_grados": lon_cg, "y_cg_grados": lat_cg, "x_cg_km": xcg, "y_cg_km": ycg,
            "inercia_km2": float((z * (dx ** 2 + dy ** 2)).sum() / S),
            "eje_principal_km": float(4 * np.sqrt(val[1])), "eje_secundario_km": float(4 * np.sqrt(max(val[0], 0))),
            "isotropia": float(np.sqrt(max(val[0], 0) / val[1])),
            "orientacion_grados": float((np.degrees(np.arctan2(vec[0, 1], vec[1, 1])) + 180) % 180),
            "area_equivalente_mn2": float(S ** 2 / (z ** 2).sum() * area_celda),
            "D95_mn2": float((np.searchsorted(acum, 0.95) + 1) * area_celda), "gini": _gini(z)}


def _indicadores(x, y, z, lon0, umbral, area_celda):
    pos = z > umbral
    zp = z[pos]
    out = {"NASC_total": z.sum(), "NASC_medio_todas": z.mean(),
           "NASC_medio_positivas": zp.mean() if len(zp) else np.nan,
           "NASC_mediano_positivas": float(np.median(zp)) if len(zp) else np.nan,
           "CV_positivas": float(zp.std(ddof=1) / zp.mean()) if len(zp) > 1 else np.nan,
           "NASC_maximo": z.max(), "indice_abundancia_m2": float((z * area_celda).sum()),
           "n_celdas": len(z), "celdas_positivas": int(pos.sum()), "pct_celdas_positivas": 100 * pos.mean(),
           "area_ocupada_mn2": float(pos.sum() * area_celda), "area_prospectada_mn2": float(len(z) * area_celda)}
    if z.sum() > 0:
        out.update(_espaciales(x, y, z, lon0, area_celda))
    else:
        out.update({k: np.nan for k in ("x_cg_grados", "y_cg_grados", "x_cg_km", "y_cg_km", "inercia_km2",
                                        "eje_principal_km", "eje_secundario_km", "isotropia", "orientacion_grados",
                                        "area_equivalente_mn2", "D95_mn2", "gini")})
    return out


def _leer(ruta, hoja, cols):
    ruta = Path(ruta)
    if ruta.suffix.lower() == ".csv":
        df = pd.read_csv(ruta, sep=None, engine="python", encoding_errors="replace")
        df.columns = [str(c).strip().strip('"') for c in df.columns]
    else:
        df = pd.read_excel(ruta, sheet_name=hoja)
        df.columns = [str(c).strip() for c in df.columns]
    return df


# ----------------------------- función principal -----------------------------
def descriptores_celdas(archivos, variables=("ANC", "ANCP", "ANCG"), hoja=0, etiquetas=None,
                        col_lon="Lon_M", col_lat="Lat_M", col_transecto="Transect",
                        lat_rango=None, umbral_positivo=0.0, largo_celda_mn=1.0, espacio_transectos_mn=10.0,
                        bootstrap=0, semilla=12345, incluir_cg_km=False,
                        guardar=None, verbose=True):
    """
    Calcula los descriptores por archivo (un archivo = un crucero) y variable.

    archivos       ruta | lista de rutas | {"etiqueta": ruta}.  Acepta .xlsx / .xls / .csv (primera hoja por defecto).
    variables      columnas de NASC por especie (por defecto ANC, ANCP, ANCG).
    etiquetas      lista con el nombre de cada archivo (si no, se usa el nombre del archivo).
    lat_rango      (lat_a, lat_b) para usar solo las celdas entre esas latitudes, p. ej. (-16, -3) o (-3, -16)
                   (el orden no importa; incluye los extremos). None = todas las celdas. Todo se calcula solo con
                   las celdas del rango, incluidas el área prospectada, el centro de gravedad y el Gini.
    bootstrap      N.º de remuestreos de transectos para el IC95 (0 = sin intervalos de confianza).
    incluir_cg_km  True agrega x_cg_km y y_cg_km (centro de gravedad en km proyectados).
    guardar        ruta de un .xlsx o .csv donde guardar la tabla (None = no guardar).
    Devuelve un DataFrame (una fila por archivo x variable).
    """
    if isinstance(archivos, dict):
        rutas, nombres = list(archivos.values()), list(archivos.keys())
    else:
        rutas = [archivos] if isinstance(archivos, (str, Path)) else list(archivos)
        nombres = list(etiquetas) if etiquetas else [Path(r).stem for r in rutas]
    if len(nombres) != len(rutas):
        raise ValueError("'etiquetas' debe tener un nombre por cada archivo.")
    variables = list(variables)
    area_celda = largo_celda_mn * espacio_transectos_mn
    rng = np.random.default_rng(semilla)
    filas = []

    for nombre, ruta in zip(nombres, rutas):
        if verbose:
            print(f"\n=== {nombre} ===")
        try:
            df = _leer(ruta, hoja, None)
        except Exception as e:
            print(f"  ! No se pudo leer {ruta}: {e}")
            continue
        faltan = [c for c in (col_lon, col_lat) if c not in df.columns]
        if faltan:
            print(f"  ! Faltan columnas {faltan}; se omite el archivo.")
            continue
        df = df.dropna(subset=[col_lon, col_lat]).reset_index(drop=True)
        if lat_rango is not None:
            lat_min, lat_max = sorted(float(v) for v in lat_rango)
            df = df[(df[col_lat] >= lat_min) & (df[col_lat] <= lat_max)].reset_index(drop=True)
            if verbose:
                print(f"  Rango de latitud {lat_min:g} a {lat_max:g}: {len(df):,} celdas")
            if df.empty:
                print("  ! No hay celdas en ese rango de latitud; se omite el archivo.")
                continue
        lon0 = df[col_lon].mean()
        x, y = _proyectar_km(df[col_lon].values, df[col_lat].values, lon0)
        trans = df[col_transecto].astype(str).values if col_transecto in df.columns else None
        if bootstrap and trans is None:
            print(f"  ! No hay columna '{col_transecto}': no se calculan intervalos de confianza.")
        for var in variables:
            if var not in df.columns:
                print(f"  ! {var}: no está en el archivo; se omite.")
                continue
            z = pd.to_numeric(df[var], errors="coerce").fillna(0).clip(lower=0).values
            fila = {"archivo": nombre, "variable": var,
                    "rango_latitud": "todo" if lat_rango is None else f"{lat_min:g} a {lat_max:g}",
                    **_indicadores(x, y, z, lon0, umbral_positivo, area_celda)}
            if z.sum() == 0:
                print(f"  ! {var}: no hay celdas positivas; los índices espaciales quedan vacíos.")
            elif bootstrap and trans is not None:
                ids = np.unique(trans)
                por_t = {t: np.where(trans == t)[0] for t in ids}
                muestras = []
                for _ in range(bootstrap):
                    idx = np.concatenate([por_t[t] for t in rng.choice(ids, len(ids), replace=True)])
                    if z[idx].sum() > 0:
                        muestras.append(_indicadores(x[idx], y[idx], z[idx], lon0, umbral_positivo, area_celda))
                m = pd.DataFrame(muestras)
                for k in INDICADORES:
                    if k in ("n_celdas", "area_prospectada_mn2"):
                        continue
                    fila[f"{k}_ic_inf"], fila[f"{k}_ic_sup"] = np.nanpercentile(m[k], [2.5, 97.5])
            if verbose and z.sum() > 0:
                print(f"  {var}: positivas {fila['celdas_positivas']:,} ({fila['pct_celdas_positivas']:.1f} %) | "
                      f"NASC medio {fila['NASC_medio_todas']:,.1f} | CG ({fila['x_cg_grados']:.2f}, {fila['y_cg_grados']:.2f}) | "
                      f"EA {fila['area_equivalente_mn2']:,.0f} mn2 | Gini {fila['gini']:.2f}")
            filas.append(fila)

    tabla = pd.DataFrame(filas)
    if tabla.empty:
        return tabla
    orden = ["archivo", "variable", "rango_latitud"] + INDICADORES + (["x_cg_km", "y_cg_km"] if incluir_cg_km else [])
    orden += [c for c in tabla.columns if c.endswith(("_ic_inf", "_ic_sup"))]
    tabla = tabla[orden]
    if guardar:
        if str(guardar).lower().endswith(".csv"):
            tabla.to_csv(guardar, index=False, sep=";", encoding="utf-8-sig")
        else:
            tabla.to_excel(guardar, index=False)
        if verbose:
            print(f"\nTabla guardada en: {os.path.abspath(guardar)}")
    return tabla

