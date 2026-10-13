"""Lectura y limpieza de las bitácoras de regiones 120 kHz (Echoview).

Reconoce .csv / .xls / .xlsx, separador coma, punto y coma, tabulador o espacios, codificación UTF-8 o cp1252,
títulos antes del encabezado, columnas con espacios o con "X" delante (R: X3D_school_volume), decimales con coma
y centinelas (-9999, -999, 999, 9999 -> vacío). Funciones de uso interno del subpaquete.
"""
import csv
import re
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd

VARIABLES = ["Corrected_length", "Corrected_thickness", "Corrected_area", "Sv_mean",
             "Depth_mean", "Height_mean", "3D_school_volume"]
CLASES_ANC = {"ANC", "ANCP", "ANCG"}
SENTINELAS = {-9999.0, -999.0, 999.0, 9999.0}
COL_HORA = "Time_M"
CLAVES_ENCABEZADO = {"region_class", "rengion_class", "region_id", "region_name", "sv_mean", "nasc", "depth_mean"}
ALIAS_CLASE = ("region_class", "rengion_class")


def _norm_col(nombre):
    t = unicodedata.normalize("NFKD", str(nombre)).encode("ascii", "ignore").decode().lower()
    t = re.sub(r"[^a-z0-9]+", "_", t).strip("_")
    return re.sub(r"^x(?=\d)", "", t)                  # R agrega una "X" a nombres que empiezan con número


_NECESARIAS = {_norm_col(v) for v in VARIABLES} | {_norm_col(COL_HORA)} | set(ALIAS_CLASE)


def _limpiar_clase(x):
    if pd.isna(x):
        return ""
    t = unicodedata.normalize("NFKD", str(x)).encode("ascii", "ignore").decode().upper()
    return re.sub(r"[^A-Z0-9]", "", t)


def _detectar_sep(linea):
    cuentas = {s: linea.count(s) for s in (";", ",", "\t")}
    mejor = max(cuentas, key=cuentas.get)
    return mejor if cuentas[mejor] >= 3 else None


def _celdas(linea, sep):
    if sep is None:
        return [c.strip().strip('"').strip() for c in linea.split()]
    try:
        fila = next(csv.reader([linea], delimiter=sep, skipinitialspace=True))
    except (csv.Error, StopIteration):
        fila = linea.split(sep)
    return [c.strip().strip('"').strip() for c in fila]


def _encabezado_csv(ruta):
    with open(ruta, "r", encoding="cp1252", errors="replace", newline="") as fh:
        lineas = [fh.readline().rstrip("\r\n") for _ in range(25)]
    lineas = [ln.lstrip("\ufeff").lstrip("ï»¿") for ln in lineas]
    candidatas = [(i, ln) for i, ln in enumerate(lineas) if ln.strip()]
    if not candidatas:
        raise ValueError("el archivo está vacío")
    for i, ln in candidatas:
        sep = _detectar_sep(ln)
        if {_norm_col(c) for c in _celdas(ln, sep)} & CLAVES_ENCABEZADO:
            return {"separador": sep, "fila_encabezado": i,
                    "linea_datos": lineas[i + 1] if i + 1 < len(lineas) else ""}
    raise ValueError("no se reconoció la fila de encabezado")


def _encabezado_excel(ruta):
    with pd.ExcelFile(ruta) as xl:
        for hoja in xl.sheet_names:
            previa = xl.parse(hoja, header=None, nrows=25)
            for i in range(len(previa)):
                fila = [str(c).strip() for c in previa.iloc[i].tolist() if pd.notna(c) and str(c).strip() != ""]
                if {_norm_col(c) for c in fila} & CLAVES_ENCABEZADO:
                    return {"hoja": hoja, "fila_encabezado": i}
    raise ValueError("no se reconoció la fila de encabezado en ninguna hoja")


def _leer_archivo(ruta):
    if ruta.suffix.lower() == ".csv":
        info = _encabezado_csv(ruta)
        sep = info["separador"]
        decimal_coma = sep in (";", "\t") and bool(re.search(r"\d,\d", info["linea_datos"]))
        ultimo = None
        for enc in ("utf-8-sig", "cp1252"):
            try:
                df = pd.read_csv(ruta, sep=sep if sep else r"\s+", engine="c" if sep else "python", encoding=enc,
                                 skiprows=info["fila_encabezado"], dtype=str, skipinitialspace=True,
                                 usecols=lambda c: _norm_col(c) in _NECESARIAS, on_bad_lines="skip")
                break
            except UnicodeDecodeError as e:
                ultimo = e
        else:
            raise ultimo
    else:
        info = _encabezado_excel(ruta)
        df = pd.read_excel(ruta, sheet_name=info["hoja"], header=info["fila_encabezado"], dtype=object,
                           usecols=lambda c: _norm_col(c) in _NECESARIAS)
        decimal_coma = False
    df.columns = [_norm_col(c) for c in df.columns]
    df = df.loc[:, ~df.columns.duplicated()]
    for alias in ALIAS_CLASE:
        if alias in df.columns and alias != "region_class":
            df = df.rename(columns={alias: "region_class"})
    return df, decimal_coma


def _a_numero(serie, decimal_coma):
    s = serie.astype(str).str.strip().str.strip('"')
    if decimal_coma:
        s = s.str.replace(",", ".", regex=False)
    v = pd.to_numeric(s, errors="coerce")
    return v.mask(v.isin(SENTINELAS) | (v <= -900))


_RE_HORA = re.compile(r"(\d{1,2}):(\d{2})")


def _hora_de(serie):
    def una(x):
        if x is None or (isinstance(x, float) and np.isnan(x)):
            return np.nan
        if isinstance(x, (int, float, np.integer, np.floating)) and 0 <= x < 1:
            return int(x * 24)
        t = str(x).strip().strip('"')
        m = _RE_HORA.search(t)
        if m:
            h = int(m.group(1))
            return h if 0 <= h <= 23 else np.nan
        try:
            f = float(t.replace(",", "."))
            return int(f * 24) if 0 <= f < 1 else np.nan
        except ValueError:
            return np.nan
    return serie.map(una)


def _etiqueta_de_ruta(ruta):
    for p in [ruta.parent] + list(ruta.parents):
        if re.match(r"^cr[\s_\-]*\d{4}[\s_\-]*\d{2}", p.name, re.IGNORECASE):
            return p.name
    return ruta.stem


def _tabla_de_archivo(ruta, desfase_horas):
    """DataFrame con clase, hora y las 7 variables, de una bitácora."""
    df, dec = _leer_archivo(Path(ruta))
    if "region_class" not in df.columns:
        raise ValueError("no tiene columna Region_class")
    out = pd.DataFrame({"clase": df["region_class"].map(_limpiar_clase)})
    for v in VARIABLES:
        nv = _norm_col(v)
        out[v] = _a_numero(df[nv], dec) if nv in df.columns else np.nan
    nh = _norm_col(COL_HORA)
    h = _hora_de(df[nh]) if nh in df.columns else pd.Series(np.nan, index=df.index)
    out["hora"] = (h + desfase_horas) % 24
    return out


def _cargar_cruceros(bitacoras, cruceros, desfase_horas):
    """Devuelve {etiqueta: DataFrame(clase, hora, variables)}."""
    if isinstance(bitacoras, dict):
        return {k: _tabla_de_archivo(v, desfase_horas) for k, v in bitacoras.items()}
    if isinstance(bitacoras, (str, Path)):
        bitacoras = [bitacoras]
    res = {}
    for b in bitacoras:
        b = Path(b)
        if b.name.lower().endswith((".csv.gz", ".gz")):                # base compilada
            comp = pd.read_csv(b, sep=";", encoding="utf-8-sig")
            elegidos = cruceros if cruceros else sorted(comp["crucero"].unique())
            for c in elegidos:
                sub = comp[comp["crucero"] == c]
                if sub.empty:
                    raise ValueError(f"el crucero '{c}' no está en {b.name}")
                res[c] = sub[["clase"] + VARIABLES + ["hora"]].reset_index(drop=True)   # la hora ya trae el desfase
        else:
            et = _etiqueta_de_ruta(b)
            while et in res:
                et += "'"
            res[et] = _tabla_de_archivo(b, desfase_horas)
    return res
