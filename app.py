"""
Perfil productivo y competitivo de los principales cultivos del Perú
Streamlit + Folium + Plotly  ·  Fuentes: SISAGRI, SISAP, SISCOMEX, VBP (MIDAGRI)
"""
import io, json, math, sys
from pathlib import Path

import folium
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots
from streamlit_folium import st_folium

BASE = Path(__file__).parent
sys.path.insert(0, str(BASE))
from common import norm  # noqa: E402
import mapas  # noqa: E402

st.set_page_config(page_title="Perfil productivo de cultivos · Perú", page_icon="🌾",
                   layout="wide", initial_sidebar_state="expanded")

# ───────────────────────────── Estilo ─────────────────────────────
VERDE, VERDE2, HOJA, ORO, TERRA, GRIS = "#0E3B2E", "#1F6F4A", "#3FA66B", "#E0A526", "#B5523B", "#6B7A72"
CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,600;9..144,700&family=Source+Sans+3:wght@400;500;600;700&display=swap');
html, body, [class*="css"], .stMarkdown, .stSelectbox, .stRadio {{ font-family: 'Source Sans 3', sans-serif; }}
.block-container {{ padding-top: 1.2rem; max-width: 1500px; }}
.hero {{ background: linear-gradient(105deg,{VERDE} 0%,{VERDE2} 62%,#2a8a57 100%); border-radius: 16px;
        padding: 22px 28px 18px; color: #fff; position: relative; overflow: hidden; margin-bottom: 14px; }}
.hero:after {{ content:""; position:absolute; left:0; right:0; bottom:0; height:6px;
        background: linear-gradient(90deg,{ORO} 0 33%, {TERRA} 33% 66%, {HOJA} 66% 100%); }}
.hero h1 {{ font-family:'Fraunces',serif; font-weight:700; font-size:1.75rem; margin:0 0 4px; letter-spacing:-.01em; color:#fff; }}
.hero p {{ margin:0; opacity:.88; font-size:.98rem; }}
.hero .pill {{ display:inline-block; background:rgba(255,255,255,.16); border-radius:99px; padding:2px 12px;
        margin:8px 6px 0 0; font-size:.84rem; font-weight:600; }}
.kpi {{ background:#fff; border:1px solid #e3e9e4; border-radius:14px; padding:14px 16px 12px; height:100%;
        box-shadow:0 1px 2px rgba(14,59,46,.05); border-top:4px solid {HOJA}; }}
.kpi.oro {{ border-top-color:{ORO}; }} .kpi.terra {{ border-top-color:{TERRA}; }} .kpi.verde {{ border-top-color:{VERDE2}; }}
.kpi .lb {{ font-size:.82rem; color:{GRIS}; font-weight:600; }}
.kpi .vl {{ font-family:'Fraunces',serif; font-size:1.65rem; color:{VERDE}; font-weight:700; line-height:1.15; margin-top:2px; }}
.kpi .vl small {{ font-size:.8rem; color:{GRIS}; font-family:'Source Sans 3'; font-weight:600; }}
.kpi .dl {{ font-size:.82rem; margin-top:4px; font-weight:600; }}
.up {{ color:#1b8a4b; }} .down {{ color:#c0392b; }} .nd {{ color:#9aa5a0; font-weight:500; }}
.sec {{ font-family:'Fraunces',serif; color:{VERDE}; font-size:1.15rem; margin:6px 0 2px; font-weight:700; }}
.note {{ font-size:.8rem; color:{GRIS}; }}
.insight {{ background:#f3f8f4; border-left:4px solid {HOJA}; border-radius:8px; padding:10px 14px; font-size:.95rem; color:#26372f; }}
div[data-testid="stSidebar"] {{ background:#f4f7f4; border-right:1px solid #e0e8e2; }}
button[data-baseweb="tab"] {{ font-weight:600; }}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

MESES_ABR = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
MESES_NOM = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
PRETTY = {"CAFE": "Café", "ARANDANO": "Arándano", "ESPARRAGO": "Espárrago", "MAIZ": "Maíz", "LIMON": "Limón", "PLATANO": "Plátano",
          "MANI": "Maní", "AJI": "Ají", "AZUCAR": "Azúcar", "LUCUMA": "Lúcuma", "BROCOLI": "Brócoli", "MARACUYA": "Maracuyá",
          "MELOCOTON": "Melocotón", "OREGANO": "Orégano", "GUANABANA": "Guanábana", "BETARRAGA": "Betarraga", "PIÑA": "Piña",
          "ARANDANO)": "Arándano)", "MARAÑON": "Marañón", "TE": "Té", "ALGODON": "Algodón", "CAÑIHUA": "Cañihua", "COL": "Col",
          "AJONJOLI": "Ajonjolí", "ROCOTO": "Rocoto", "CAMU-CAMU": "Camu-camu", "ACHIOTE": "Achiote", "PIMIENTO": "Pimiento"}
PALETA_VERDE = ["#f2f7ee", "#cfe6bf", "#8fcb92", "#3fa66b", "#1f6f4a", "#0b3d2c"]
PALETA_ORO = ["#fff8e6", "#fde7a8", "#f6c85f", "#e0a526", "#b5702c", "#7a3b1d"]


def pretty(s: str) -> str:
    return " ".join(PRETTY.get(w, w.capitalize()) for w in str(s).split(" ")).replace("De Azucar", "de Azúcar").replace(" De ", " de ")


def fmt(x, d=0, suf=""):
    if x is None or (isinstance(x, float) and (math.isnan(x) or math.isinf(x))):
        return "N/D"
    return f"{x:,.{d}f}{suf}"


def fmt_big(x, unidad=""):
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "N/D"
    a = abs(x)
    if a >= 1e9: return f"{x/1e9:,.2f} mil M{unidad}"
    if a >= 1e6: return f"{x/1e6:,.2f} M{unidad}"
    if a >= 1e3: return f"{x/1e3:,.1f} mil{unidad}"
    return f"{x:,.1f}{unidad}"


def pc(fig, **kw):
    try:
        st.plotly_chart(fig, width="stretch", **kw)
    except TypeError:
        st.plotly_chart(fig, use_container_width=True, **kw)


def mostrar_mapa(m, height, key):
    """Muestra un mapa folium. Si streamlit-folium falla (o se activa el modo compatible), lo dibuja como HTML puro."""
    import streamlit.components.v1 as components
    if not st.session_state.get("modo_compat", False):
        try:
            try:
                return st_folium(m, height=height, use_container_width=True, returned_objects=[], key=key)
            except TypeError:
                return st_folium(m, height=height, returned_objects=[], key=key)
        except Exception as e:  # noqa: BLE001
            st.warning(f"El componente de mapas falló ({type(e).__name__}); se usa el modo compatible.")
    components.html(m.get_root().render(), height=height + 10, scrolling=False)


def tabla(df, **kw):
    try:
        st.dataframe(df, width="stretch", **kw)
    except TypeError:
        st.dataframe(df, use_container_width=True, **kw)


def style(fig, h=340, legend=True):
    fig.update_layout(height=h, margin=dict(l=8, r=8, t=36, b=8), template="plotly_white",
                      font=dict(family="Source Sans 3, sans-serif", size=13, color="#26372f"),
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", showlegend=legend,
                      legend=dict(orientation="h", yanchor="bottom", y=1.0, x=0, bgcolor="rgba(0,0,0,0)"),
                      hoverlabel=dict(font_family="Source Sans 3"))
    fig.update_xaxes(showgrid=False, linecolor="#d5ddd7")
    fig.update_yaxes(gridcolor="#eaf0ec", zeroline=False)
    return fig


def titulo_graf(txt):
    st.markdown(f'<div class="sec">{txt}</div>', unsafe_allow_html=True)


# ───────────────────────────── Carga de datos ─────────────────────────────
@st.cache_data(show_spinner=False)
def cargar_catalogo():
    c = pd.read_parquet(BASE / "data/catalogo.parquet")
    c["etiqueta"] = c.cultivo.map(pretty)
    return c


@st.cache_data(show_spinner=False)
def cargar_ub():
    return pd.read_parquet(BASE / "data/ubigeo.parquet")


@st.cache_data(show_spinner="Cargando cultivo…")
def cargar_cultivo(slug: str, nivel: str):
    df = pd.read_parquet(BASE / f"data/agri/{slug}.parquet")
    if nivel == "distrito":
        df = df.merge(cargar_ub(), on="UBIGEO", how="left")
    else:
        df["UBIGEO"], df["PROVINCIA"], df["DISTRITO"] = None, None, None
    df["MES"] = df.MES.astype(int)
    df["ANIO"] = df.ANIO.astype(int)
    return df


@st.cache_data(show_spinner=False)
def cargar_vbp():
    return pd.read_parquet(BASE / "data/vbp.parquet")


@st.cache_data(show_spinner=False)
def cargar_sisap():
    return pd.read_parquet(BASE / "data/sisap.parquet")


@st.cache_data(show_spinner=False)
def cargar_comercio():
    return pd.read_parquet(BASE / "data/comercio.parquet")


@st.cache_resource(show_spinner=False)
def cargar_geo(nombre):
    with open(BASE / f"geo/{nombre}.geojson", encoding="utf-8") as f:
        return json.load(f)


@st.cache_resource(show_spinner=False)
def cargar_paises_xy():
    with open(BASE / "geo/paises_xy.json", encoding="utf-8") as f:
        return json.load(f)


CAT = cargar_catalogo()

# ───────────────────────────── Sidebar ─────────────────────────────
with st.sidebar:
    st.markdown("### 🌾 Filtros")
    tipo = st.radio("Tipo de cultivo", ["Todos", "Permanentes", "Transitorios"], horizontal=True)
    cat_f = CAT if tipo == "Todos" else CAT[CAT.permanente == (tipo == "Permanentes")]
    lista = cat_f.cultivo.tolist()
    idx = lista.index("CACAO") if "CACAO" in lista else 0
    cultivo = st.selectbox("Cultivo (ordenado por VBP 2025)", lista, index=idx,
                           format_func=lambda c: pretty(c), help="Escribe para buscar. Los cultivos agrupan todas sus variedades.")
    info = CAT[CAT.cultivo == cultivo].iloc[0]
    DF = cargar_cultivo(info.slug, info.nivel)
    es_dist = info.nivel == "distrito"

    anios = sorted(DF.ANIO.unique())
    anios_sel = st.multiselect("Años (uno o varios)", anios[::-1], default=[anios[-1]],
                               help="Con varios años, los indicadores y mapas acumulan todos los años elegidos y se comparan con el bloque anterior de igual duración.")
    if not anios_sel: anios_sel = [anios[-1]]
    anios_sel = sorted(anios_sel)
    anio = anios_sel[-1]            # año de referencia (el más reciente)
    meses_disp = sorted(DF[DF.ANIO == anio].MES.unique())
    corte = st.select_slider("Acumulado hasta el mes", options=meses_disp, value=meses_disp[-1],
                             format_func=lambda m: MESES_ABR[m - 1])

    st.markdown("---")
    st.markdown("**📍 Ubicación**")
    deps = ["Todos"] + sorted(DF.DEPARTAMENTO.dropna().unique())
    dep = st.selectbox("Departamento", deps)
    prov = dist = "Todos"
    if es_dist:
        d1 = DF if dep == "Todos" else DF[DF.DEPARTAMENTO == dep]
        prov = st.selectbox("Provincia", ["Todos"] + sorted(d1.PROVINCIA.dropna().unique()), disabled=dep == "Todos")
        if dep != "Todos" and prov != "Todos":
            d2 = d1[d1.PROVINCIA == prov]
            dist = st.selectbox("Distrito", ["Todos"] + sorted(d2.DISTRITO.dropna().unique()))
        else:
            st.selectbox("Distrito", ["Todos"], disabled=True)
    else:
        st.caption("ℹ️ Este cultivo solo tiene detalle **departamental** en la fuente.")

    st.markdown("---")
    nivel_map = st.selectbox("Nivel del mapa", ["Automático", "Departamento", "Provincia", "Distrito"], disabled=not es_dist)
    metrica = st.radio("Métrica del mapa", ["Producción (t)", "Valor de la producción (millones S/)", "Rendimiento (t/ha)", "Precio chacra (S/kg)", "Variación % vs año anterior", "Cosecha (ha)"])
    st.checkbox("Modo compatible de mapas", key="modo_compat", help="Actívalo si no ves los mapas: los dibuja como HTML puro, sin depender de streamlit-folium.")
    st.markdown("---")
    st.caption("Fuentes: SISAGRI, SISAP, SISCOMEX y VBP – MIDAGRI. Elaboración propia.")

# ───────────────────────────── Cálculos base ─────────────────────────────
ult_anio = int(DF.ANIO.max())
ult_mes = int(DF[DF.ANIO == ult_anio].MES.max())


def txt_anios(ys):
    ys = sorted(ys)
    return str(ys[0]) if len(ys) == 1 else (f"{ys[0]}–{ys[-1]}" if ys[-1] - ys[0] + 1 == len(ys) else ", ".join(map(str, ys)))


anios_txt = txt_anios(anios_sel)
span = anio - anios_sel[0] + 1
prev_anios = [y - span for y in anios_sel]                # bloque anterior equivalente
prev_txt = txt_anios(prev_anios)
prev = anio - 1                                            # para gráficos año contra año
prev_ok = min(prev_anios) >= 2016                          # 2015 inicia en febrero -> no comparable en acumulados desde enero
anios_comp = [y for y in anios_sel if not (y == ult_anio and ult_mes < 12)]   # cosecha/rendimiento solo con años cerrados
anio_incompleto = len(anios_comp) == 0


def filtrar_geo(df):
    if dep != "Todos": df = df[df.DEPARTAMENTO == dep]
    if prov != "Todos": df = df[df.PROVINCIA == prov]
    if dist != "Todos": df = df[df.DISTRITO == dist]
    return df


DG = filtrar_geo(DF)  # cultivo en la geografía elegida (todas las fechas)
nac = DF              # cultivo nacional


def resumen(d, dc=None):
    """dc = subconjunto de años cerrados, usado para cosecha y rendimiento."""
    dc = d if dc is None else dc
    prod, sie = d.PRODUCCION.sum(), d.SIEMBRA.sum()
    pxp, prp = d.PXP.sum(), d.PRODP.sum()
    cos = dc.COSECHA.sum()
    return dict(prod=float(prod), cos=float(cos), sie=float(sie), precio=(pxp / prp if prp > 0 else np.nan),
                rend=(dc.PRODUCCION.sum() / cos if cos > 0 else np.nan))


def per(d, ys):
    ys = [int(ys)] if np.isscalar(ys) else [int(y) for y in ys]
    return d[d.ANIO.isin(ys) & (d.MES <= corte)]


cur = resumen(per(DG, anios_sel), per(DG, anios_comp))
ant = resumen(per(DG, prev_anios), per(DG, [y - span for y in anios_comp])) if prev_ok else None
cur_nac = resumen(per(nac, anios_sel))


def delta(a, b):
    if b is None or b is np.nan or (isinstance(b, float) and (math.isnan(b) or b == 0)) or a is None or (isinstance(a, float) and math.isnan(a)):
        return None
    return (a / b - 1) * 100


def chip(dv, pts=False):
    if dv is None: return '<span class="nd">vs año anterior: N/D</span>'
    cls, ar = ("up", "▲") if dv >= 0 else ("down", "▼")
    return f'<span class="{cls}">{ar} {abs(dv):,.1f}% <span class="nd">vs {prev_txt}</span></span>'


def kpi(col, label, value, unit="", sub="", cls=""):
    col.markdown(f'<div class="kpi {cls}"><div class="lb">{label}</div><div class="vl">{value} <small>{unit}</small></div>'
                 f'<div class="dl">{sub}</div></div>', unsafe_allow_html=True)


# verde actual (superficie instalada) al mes de corte
def verde(d, y):
    m = d[(d.ANIO == y) & (d.MES <= corte)]
    if m.empty: return np.nan
    mm = m.MES.max()
    return float(m[m.MES == mm].VERDE_ACTUAL.sum())


# ───────────────────────────── Encabezado ─────────────────────────────
geo_txt = " · ".join([x for x in [dep if dep != "Todos" else "Perú", prov if prov != "Todos" else None, dist if dist != "Todos" else None] if x])
st.markdown(f"""
<div class="hero">
  <h1>Perfil productivo y competitivo · {pretty(cultivo)}</h1>
  <p>Producción, precios, valor bruto y comercio exterior de los principales cultivos del sector agrario peruano</p>
  <span class="pill">📅 Enero – {MESES_NOM[corte-1].capitalize()} · {anios_txt}</span>
  <span class="pill">📍 {geo_txt}</span>
  <span class="pill">🌱 {'Permanente' if info.permanente else 'Transitorio'}</span>
  <span class="pill">🗂️ Detalle {info.nivel}</span>
</div>""", unsafe_allow_html=True)

if ult_anio == anio and meses_disp[-1] < 12:
    st.caption(f"Datos de este cultivo disponibles hasta **{MESES_NOM[ult_mes-1]} de {ult_anio}**.")

# KPIs
c1, c2, c3, c4 = st.columns(4)
dv_prod = delta(cur["prod"], ant["prod"] if ant else None)
kpi(c1, "Producción acumulada", fmt(cur["prod"], 0), "t", chip(dv_prod))
if anio_incompleto:
    kpi(c2, "Cosecha*", "N/D", "ha", '<span class="nd">* se consolida al final del año</span>', "oro")
    kpi(c3, "Rendimiento*", "N/D", "t/ha", '<span class="nd">* se consolida al final del año</span>', "oro")
else:
    nota_c = "" if len(anios_comp) == len(anios_sel) else f' <span class="nd">(solo años cerrados: {txt_anios(anios_comp)})</span>'
    kpi(c2, "Superficie cosechada", fmt(cur["cos"], 0), "ha", chip(delta(cur["cos"], ant["cos"] if ant else None)) + nota_c, "oro")
    kpi(c3, "Rendimiento", fmt(cur["rend"], 2), "t/ha", chip(delta(cur["rend"], ant["rend"] if ant else None)) + nota_c, "oro")
kpi(c4, "Precio en chacra", fmt(cur["precio"], 2), "S/ por kg", chip(delta(cur["precio"], ant["precio"] if ant else None)), "terra")

c5, c6, c7, c8 = st.columns(4)
v_cur, v_prev = verde(DG, anio), verde(DG, anio - span) if prev_ok else np.nan
kpi(c5, "Superficie instalada (verde)", fmt(v_cur, 0), "ha", chip(delta(v_cur, v_prev)), "verde")
kpi(c6, "Siembras del período", fmt(cur["sie"], 0), "ha", chip(delta(cur["sie"], ant["sie"] if ant else None)), "verde")
nd = per(DG, anios_sel).groupby("UBIGEO").PRODUCCION.sum() if es_dist else None
if es_dist:
    kpi(c7, "Distritos productores", fmt(int((nd > 0).sum()), 0), "distritos", f'<span class="nd">de {nd.shape[0]:,} con registro</span>', "verde")
else:
    kpi(c7, "Departamentos productores", fmt(int((per(DG, anios_sel).groupby("DEPARTAMENTO").PRODUCCION.sum() > 0).sum()), 0), "dptos.", "", "verde")
part = cur["prod"] / cur_nac["prod"] * 100 if cur_nac["prod"] > 0 else np.nan
kpi(c8, "Participación nacional", fmt(part, 1), "%", f'<span class="nd">del total nacional de {pretty(cultivo)}</span>', "verde")
st.write("")

# ───────────────────────────── Funciones de mapa ─────────────────────────────
PAL_REND = ["#d7191c", "#fdae61", "#f2e98f", "#a6d96a", "#1a9641"]


@st.cache_resource(show_spinner=False)
def cargar_cent():
    with open(BASE / "geo/centroides.json", encoding="utf-8") as f:
        return json.load(f)


@st.cache_resource(show_spinner=False)
def nombres_dist():
    ub = cargar_ub()
    return {r.UBIGEO: (r.DISTRITO, r.PROVINCIA, r.DEPARTAMENTO) for r in ub.itertuples()}


@st.cache_data(show_spinner="Cargando todos los cultivos del año…")
def todos_anio(anios_t):
    """Producción/valor por distrito y cultivo (todos los cultivos con detalle distrital) para un año."""
    partes = []
    for r in CAT[CAT.nivel == "distrito"].itertuples():
        d = pd.read_parquet(BASE / f"data/agri/{r.slug}.parquet", filters=[("ANIO", "in", list(anios_t))], columns=["MES", "UBIGEO", "PRODUCCION", "PXP", "COSECHA"])
        if len(d):
            d["CULTIVO"] = r.cultivo
            partes.append(d)
    out = pd.concat(partes, ignore_index=True)
    out["MES"] = out.MES.astype(int)
    return out


def codigos_area():
    dep_code = None
    if dep != "Todos":
        dep_code = next((f["properties"]["FIRST_IDDP"] for f in cargar_geo("dep")["features"] if f["properties"]["NOMBDEP"] == dep), None)
    prov_code = dist_sel = None
    if es_dist and prov != "Todos":
        sub = DF[(DF.DEPARTAMENTO == dep) & (DF.PROVINCIA == prov)]
        prov_code = sub.UBIGEO.iloc[0][:4] if len(sub) else None
    if dist != "Todos":
        sub = DF[(DF.DEPARTAMENTO == dep) & (DF.PROVINCIA == prov) & (DF.DISTRITO == dist)]
        dist_sel = sub.UBIGEO.iloc[0] if len(sub) else None
    return dep_code, prov_code, dist_sel


def tabla_territorio(nivel):
    """Agrega por territorio el período actual y el anterior."""
    d_cur, d_ant = per(DG, anios_sel).copy(), (per(DG, prev_anios).copy() if prev_ok else DG.iloc[0:0].copy())
    d_comp = per(DG, anios_comp).copy() if anios_comp else DG.iloc[0:0].copy()
    keyf = {"dep": lambda d: d.DEPARTAMENTO, "prov": lambda d: d.UBIGEO.str[:4], "dist": lambda d: d.UBIGEO}[nivel] if (es_dist or nivel == "dep") else (lambda d: d.DEPARTAMENTO)
    out = []
    for d in (d_cur, d_ant):
        d["K"] = keyf(d) if len(d) else []
        g = d.groupby("K").agg(PRODUCCION=("PRODUCCION", "sum"), COSECHA=("COSECHA", "sum"), PXP=("PXP", "sum"),
                               PRODP=("PRODP", "sum"), SIEMBRA=("SIEMBRA", "sum"))
        out.append(g)
    g, ga = out
    d_comp["K"] = keyf(d_comp) if len(d_comp) else []
    gc = d_comp.groupby("K").agg(PC=("PRODUCCION", "sum"), CC=("COSECHA", "sum"))
    g["COSECHA"] = gc.CC.reindex(g.index)
    g["rend"] = np.where(g.COSECHA > 0, gc.PC.reindex(g.index) / g.COSECHA, np.nan)
    g["precio"] = np.where(g.PRODP > 0, g.PXP / g.PRODP, np.nan)
    g["valor"] = g.PXP / 1000.0     # miles de S/ -> millones de S/
    g["var"] = np.nan
    if len(ga):
        j = g.join(ga[["PRODUCCION"]].rename(columns={"PRODUCCION": "prod_ant"}), how="left")
        g["var"] = np.where(j.prod_ant > 0, (j.PRODUCCION / j.prod_ant - 1) * 100, np.nan)
    if anio_incompleto:
        g["COSECHA"], g["rend"] = np.nan, np.nan
    g["part"] = g.PRODUCCION / max(g.PRODUCCION.sum(), 1e-9) * 100
    return g.reset_index()


def nivel_efectivo():
    if not es_dist: return "dep"
    if nivel_map != "Automático":
        return {"Departamento": "dep", "Provincia": "prov", "Distrito": "dist"}[nivel_map]
    if prov != "Todos" or dist != "Todos": return "dist"
    return "prov" if dep != "Todos" else "dep"


MET_COL = {"Producción (t)": "PRODUCCION", "Valor de la producción (millones S/)": "valor", "Rendimiento (t/ha)": "rend",
           "Precio chacra (S/kg)": "precio", "Variación % vs año anterior": "var", "Cosecha (ha)": "COSECHA"}
MET_FMT = {"PRODUCCION": lambda v: f"{v:,.0f}", "valor": lambda v: f"{v:,.1f}", "rend": lambda v: f"{v:,.1f}",
           "precio": lambda v: f"{v:,.2f}", "var": lambda v: f"{v:+,.0f}%", "COSECHA": lambda v: f"{v:,.0f}"}


def mapa_peru(nivel, g, etiq=True, circ=False):
    geo = cargar_geo({"dep": "dep", "prov": "prov", "dist": "dist"}[nivel])
    cent = cargar_cent()
    prop_key = {"dep": "NOMBDEP", "prov": "FIRST_IDPR", "dist": "IDDIST"}[nivel]
    ub = cargar_ub()
    nombres = {}
    if nivel == "prov":
        nombres = ub.assign(k=ub.UBIGEO.str[:4]).drop_duplicates("k").set_index("k")[["PROVINCIA", "DEPARTAMENTO"]].to_dict("index")
    if nivel == "dist":
        nombres = ub.set_index("UBIGEO")[["DISTRITO", "PROVINCIA", "DEPARTAMENTO"]].to_dict("index")
    mcol = MET_COL[metrica]
    gi = g.set_index("K")
    dep_code, prov_code, dist_sel = codigos_area()

    feats = []
    for f in geo["features"]:
        p = f["properties"]
        if not f.get("geometry"): continue
        if nivel == "prov":
            if dep_code and p["FIRST_IDPR"][:2] != dep_code: continue
        elif nivel == "dist":
            if dep_code and p["IDDPTO"] != dep_code: continue
            if prov_code and p["IDPROV"] != prov_code: continue
        k = p[prop_key]
        row = gi.loc[k] if k in gi.index else None
        nm = k if nivel == "dep" else (nombres.get(k, {}).get("PROVINCIA") if nivel == "prov" else nombres.get(k, {}).get("DISTRITO")) or p.get("NOMBDIST", p.get("NOMBPROV", k))
        ctx = "" if nivel == "dep" else (nombres.get(k, {}).get("DEPARTAMENTO", p.get("NOMBDEP", p.get("FIRST_NOMB", ""))))
        v = None if row is None else row[mcol]
        v = None if (v is None or (isinstance(v, float) and np.isnan(v))) else float(v)
        sel = (nivel == "dep" and dep != "Todos" and k == dep) or (nivel == "dist" and dist_sel == k) or (nivel == "prov" and prov_code == k)
        pr = 0.0 if row is None or np.isnan(row["PRODUCCION"]) else float(row["PRODUCCION"])
        feats.append({"type": "Feature", "geometry": f["geometry"], "properties": {
            "k": k, "n": str(nm).title(), "ctx": str(ctx).title(), "v": v, "sel": sel, "pr": pr,
            "prod": fmt(None if row is None else row["PRODUCCION"], 1, " t"),
            "valor": fmt(None if row is None else row["valor"], 2, " M S/"),
            "rend": fmt(None if row is None else row["rend"], 2, " t/ha"),
            "prec": fmt(None if row is None else row["precio"], 2, " S/kg"),
            "var": fmt(None if row is None else row["var"], 1, "%"),
            "part": fmt(None if row is None else row["part"], 1, "%")}})
    vals = [x["properties"]["v"] for x in feats]
    if mcol == "var":
        arr = np.abs([x for x in vals if x is not None]) if any(x is not None for x in vals) else np.array([10.0])
        esc = mapas.EscalaDiv(float(min(max(np.percentile(arr, 90), 5), 100)))
    else:
        esc = mapas.Escala(vals, PAL_REND if mcol in ("rend", "precio") else PALETA_VERDE)
    nivel_txt = {"dep": "departamento", "prov": "provincia", "dist": "distrito"}[nivel]
    m_ = mapas.base_map(f"{metrica.split(' (')[0]} · {pretty(cultivo)}", f"por {nivel_txt} · ene–{MESES_ABR[corte-1].lower()} · {anios_txt}")
    fields = ["n", "ctx", "prod", "valor", "rend", "prec", "var", "part"]
    aliases = ["Territorio", "Ubicación", "Producción", "Valor de producción", "Rendimiento", "Precio chacra", "Var. vs año ant.", "% del área"]
    if nivel == "dep": fields, aliases = fields[:1] + fields[2:], aliases[:1] + aliases[2:]
    gj = folium.GeoJson({"type": "FeatureCollection", "features": feats}, name=metrica,
                        style_function=lambda f: {"fillColor": esc.color(f["properties"]["v"]), "color": "#c0392b" if f["properties"]["sel"] else "#ffffff",
                                                  "weight": 3 if f["properties"]["sel"] else (0.4 if nivel == "dist" else 0.9), "fillOpacity": 0.9},
                        highlight_function=lambda f: {"weight": 2.5, "color": "#0E3B2E", "fillOpacity": 0.97},
                        tooltip=folium.GeoJsonTooltip(fields=fields, aliases=aliases, sticky=True, localize=True,
                                                      style="font-family:Source Sans 3,sans-serif;font-size:13px;padding:6px 8px;"))
    gj.add_to(m_)
    if nivel != "dep":
        mapas.contorno(m_, [f for f in cargar_geo("dep")["features"] if f.get("geometry") and (not dep_code or f["properties"]["FIRST_IDDP"] == dep_code)])
    if circ:
        fg = folium.FeatureGroup(name="Círculos: producción (t)")
        mx = max([x["properties"]["pr"] for x in feats] + [1e-9])
        for x in feats:
            pr_, k = x["properties"]["pr"], x["properties"]["k"]
            if pr_ > 0 and k in cent[nivel]:
                folium.CircleMarker(cent[nivel][k], radius=3 + 19 * math.sqrt(pr_ / mx), color="#222", weight=1, fill=True,
                                    fill_color=esc.color(x["properties"]["v"]), fill_opacity=.6,
                                    tooltip=f"{x['properties']['n']}: {pr_:,.0f} t").add_to(fg)
        fg.add_to(m_)
    if etiq and (nivel != "dist" or len(feats) <= 70):
        fm = MET_FMT[mcol]
        mapas.etiquetas(m_, [(*cent[nivel][x["properties"]["k"]], x["properties"]["n"], fm(x["properties"]["v"]) if x["properties"]["v"] is not None else None)
                             for x in feats if x["properties"]["k"] in cent[nivel]], "Nombres y valores")
    mapas.agregar_buscador(m_, gj, "n", "Buscar territorio…")
    mapas.agregar_leyenda(m_, esc.legend(metrica, MET_FMT[mcol]))
    mapas.agregar_selector_dpto(m_, cent["dep_bounds"], actual=dep if dep != "Todos" else None)
    folium.LayerControl(collapsed=True, position="topright").add_to(m_)
    m_.fit_bounds(mapas.bbox(feats if feats else geo["features"]), padding=(10, 10))
    return m_, len(feats)


def mapa_multi(tipo):
    """Mapas que muestran todos los cultivos con detalle distrital (cultivo principal, burbujas, clusters, calor)."""
    cent = cargar_cent()
    t = todos_anio(tuple(anios_sel))
    t = t[t.MES <= corte].merge(cargar_ub()[["UBIGEO", "DEPARTAMENTO", "PROVINCIA", "DISTRITO"]], on="UBIGEO", how="left")
    if dep != "Todos": t = t[t.DEPARTAMENTO == dep]
    if prov != "Todos": t = t[t.PROVINCIA == prov]
    if dist != "Todos": t = t[t.DISTRITO == dist]
    M = t.groupby(["CULTIVO", "UBIGEO"], as_index=False)[["PRODUCCION", "PXP", "COSECHA"]].sum()
    if M.empty: return None
    dep_code, prov_code, _ = codigos_area()
    feats = [f for f in cargar_geo("dist")["features"] if f.get("geometry") and (not dep_code or f["properties"]["IDDPTO"] == dep_code)
             and (not prov_code or f["properties"]["IDPROV"] == prov_code)]
    cont = [f for f in cargar_geo("dep")["features"] if f.get("geometry") and (not dep_code or f["properties"]["FIRST_IDDP"] == dep_code)]
    names = nombres_dist()
    ncult = {c: pretty(c) for c in M.CULTIVO.unique()}
    per_txt = f"ene–{MESES_ABR[corte-1].lower()} · {anios_txt}"
    bd = cent["dep_bounds"]
    if tipo == "Cultivo principal":
        return mapas.mapa_cultivo_principal(M, feats, names, "Cultivo principal por distrito", f"el de mayor valor de producción (S/) · {per_txt}", bd, cont, ncult)
    if tipo == "Burbujas por cultivo":
        return mapas.mapa_burbujas(M, feats, names, cent, f"Producción por cultivo y distrito ({per_txt})", "clic en una burbuja para ver su ficha · activa/oculta cultivos en el control de capas", bd, cont, ncult)
    if tipo == "Clusters de registros":
        return mapas.mapa_clusters(M, feats, names, cent, "Registros distrito-cultivo", "los círculos numerados agrupan registros · haz clic o zoom para abrirlos", bd, cont, ncult)
    ub = cargar_ub().assign(k=lambda x: x.UBIGEO.str[:4]).drop_duplicates("k")
    if dep_code:
        pl = [(*cent["prov"][r.k], r.PROVINCIA.title(), None) for r in ub.itertuples() if r.k[:2] == dep_code and r.k in cent["prov"]]
    else:
        pl = [(*cent["dep"][d], d.title(), None) for d in cent["dep"]]
    return mapas.mapa_calor(M, feats, cent, names, f"Polos agroproductivos ({per_txt})", "mapa de calor · producción normalizada por cultivo", bd, pl)


# ───────────────────────────── Pestañas ─────────────────────────────
tabs = st.tabs(["📍 Perfil productivo", "🌎 Comercio exterior", "💰 Precios y VBP", "⚖️ Comparador", "📥 Datos"])

# ═════════ TAB 1 ═════════
with tabs[0]:
    nv = nivel_efectivo()
    G = tabla_territorio(nv)
    ml, mr = st.columns([1.35, 1])
    with ml:
        TIPOS = ["Coroplético", "Cultivo principal", "Burbujas por cultivo", "Clusters de registros", "Mapa de calor"]
        tipo_mapa = st.radio("Tipo de mapa", TIPOS, horizontal=True, key="tipo_mapa", label_visibility="collapsed")
        if tipo_mapa == "Coroplético":
            o1, o2 = st.columns(2)
            etiq = o1.checkbox("Etiquetas con nombre y valor", value=True)
            circ = o2.checkbox("Círculos proporcionales a la producción", value=False)
            titulo_graf(f"{metrica} · {'por departamento' if nv=='dep' else 'por provincia' if nv=='prov' else 'por distrito'}")
            if metrica in ("Cosecha (ha)", "Rendimiento (t/ha)") and anio_incompleto:
                st.info("La cosecha y el rendimiento se consolidan al cierre del año; elige un año completo para visualizarlos en el mapa.")
            elif G.empty:
                st.warning("Sin datos para la selección.")
            mp, nfe = mapa_peru(nv, G, etiq, circ)
            clave = f"{etiq}_{circ}_{nv}_{metrica}_{cultivo}"
        else:
            titulo_graf(f"{tipo_mapa} · todos los cultivos con detalle distrital")
            mp = mapa_multi(tipo_mapa)
            clave = tipo_mapa
            if mp is None:
                st.warning("Sin datos para la selección.")
            else:
                st.caption("Este mapa usa **todos** los cultivos con detalle distrital (no depende del cultivo elegido); sí respeta año, mes de corte y ubicación. Valor = producción × precio en chacra.")
        if mp is not None:
            mostrar_mapa(mp, 580, f"mp_{anios_txt}_{corte}_{dep}_{prov}_{dist}_{clave}")
        if es_dist and nv == "dist" and tipo_mapa == "Coroplético":
            st.caption("Algunos distritos creados recientemente no tienen polígono en la cartografía y no se dibujan, pero sí cuentan en los totales.")
    with mr:
        titulo_graf("Ranking de territorios")
        if nv == "dep": nombre_col = G.K
        elif nv == "prov":
            ub = cargar_ub().assign(k=lambda x: x.UBIGEO.str[:4]).drop_duplicates("k").set_index("k")
            nombre_col = G.K.map(lambda k: f"{ub.PROVINCIA.get(k, k).title()} ({ub.DEPARTAMENTO.get(k, '').title()})")
        else:
            ub = cargar_ub().set_index("UBIGEO")
            nombre_col = G.K.map(lambda k: f"{str(ub.DISTRITO.get(k, k)).title()} ({str(ub.PROVINCIA.get(k, '')).title()})")
        G["Territorio"] = nombre_col.map(lambda s: str(s).title() if nv == "dep" else s)
        top = G.sort_values("PRODUCCION", ascending=False).head(12).iloc[::-1]
        fig = go.Figure(go.Bar(x=top.PRODUCCION, y=top.Territorio, orientation="h", marker_color=HOJA,
                               text=[f"{p:,.1f}%" for p in top.part], textposition="outside", cliponaxis=False,
                               hovertemplate="%{y}<br>%{x:,.0f} t<extra></extra>"))
        style(fig, 470, False)
        fig.update_xaxes(title="Producción (t)  ·  etiqueta = % del total del área", gridcolor="#eaf0ec")
        fig.update_layout(margin=dict(l=8, r=40, t=10, b=8))
        pc(fig)

    # insight automático
    if len(G) and cur["prod"] > 0:
        lider = G.sort_values("PRODUCCION", ascending=False).iloc[0]
        conc3 = G.sort_values("PRODUCCION", ascending=False).head(3).part.sum()
        txt = (f"<b>Lectura rápida:</b> entre enero y {MESES_NOM[corte-1]} de {anios_txt} se produjeron <b>{fmt(cur['prod'],0)} t</b> de {pretty(cultivo).lower()}"
               + (f" ({'+' if dv_prod>=0 else ''}{dv_prod:,.1f}% vs {prev_txt})" if dv_prod is not None else "")
               + f". <b>{lider.Territorio}</b> lidera con {lider.part:,.1f}% y los 3 primeros territorios concentran <b>{conc3:,.0f}%</b> de la producción.")
        st.markdown(f'<div class="insight">{txt}</div>', unsafe_allow_html=True)
    st.write("")

    # Variación acumulada por año
    a1, a2 = st.columns(2)
    ytd = DG[(DG.MES <= corte) & (DG.ANIO >= 2016)].groupby("ANIO")[["PRODUCCION"]].sum()
    ytd["var"] = ytd.PRODUCCION.pct_change() * 100
    with a1:
        titulo_graf(f"Producción acumulada Ene–{MESES_ABR[corte-1]} y variación anual")
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.62, 0.38], vertical_spacing=0.06)
        cols = [ORO if y in anios_sel else HOJA for y in ytd.index]
        fig.add_bar(x=ytd.index, y=ytd.PRODUCCION, marker_color=cols, name="Producción (t)", row=1, col=1,
                    hovertemplate="%{x}: %{y:,.0f} t<extra></extra>")
        v = ytd["var"]
        fig.add_bar(x=ytd.index, y=v, marker_color=["#1f8f55" if (x or 0) >= 0 else "#c0392b" for x in v], name="Var. %", row=2, col=1,
                    hovertemplate="%{x}: %{y:+.1f}%<extra></extra>")
        style(fig, 400, False); fig.update_xaxes(dtick=1); fig.update_yaxes(title_text="t", row=1, col=1); fig.update_yaxes(title_text="% var.", row=2, col=1)
        pc(fig)
        st.caption("2015 se excluye de los acumulados: la serie SISAGRI inicia en febrero de 2015.")
    with a2:
        mm = DG.groupby(["ANIO", "MES"]).PRODUCCION.sum().unstack(fill_value=0)
        fig = go.Figure()
        if len(anios_sel) == 1:
            titulo_graf(f"Producción mensual {anio} vs {prev} y promedio 5 años")
            if anio in mm.index:
                vals = [mm.loc[anio].get(m, 0) if m <= corte else None for m in range(1, 13)]
                fig.add_bar(x=MESES_ABR, y=vals, marker_color=HOJA, name=str(anio), hovertemplate="%{x}: %{y:,.0f} t<extra></extra>")
            if prev in mm.index:
                fig.add_scatter(x=MESES_ABR, y=[mm.loc[prev].get(m, 0) for m in range(1, 13)], mode="lines+markers", name=str(prev), line=dict(color=ORO, width=3))
            ys = [y for y in range(anio - 5, anio) if y in mm.index and y >= 2016]
            if ys:
                fig.add_scatter(x=MESES_ABR, y=[np.mean([mm.loc[y].get(m, 0) for y in ys]) for m in range(1, 13)], mode="lines", name="Prom. 5 años",
                                line=dict(color=TERRA, width=2, dash="dash"))
        else:
            titulo_graf(f"Producción mensual · años seleccionados ({anios_txt})")
            for i, y in enumerate(anios_sel):
                if y in mm.index:
                    colr = mapas.lerp_color(["#b9dfb0", "#3fa66b", "#0b3d2c"], i / max(len(anios_sel) - 1, 1))
                    fig.add_scatter(x=MESES_ABR[:corte], y=[mm.loc[y].get(m, 0) for m in range(1, corte + 1)], mode="lines+markers", name=str(y), line=dict(color=colr, width=3))
        style(fig, 400); fig.update_yaxes(title="t")
        pc(fig)

    titulo_graf("Estacionalidad: producción por año y mes (calendario de cosecha)")
    hm = DG[DG.ANIO >= 2016].groupby(["ANIO", "MES"]).PRODUCCION.sum().unstack(fill_value=0).reindex(columns=range(1, 13), fill_value=0)
    if hm.values.sum() > 0:
        fig = go.Figure(go.Heatmap(z=hm.values, x=MESES_ABR, y=[str(i) for i in hm.index], colorscale=[[0, "#f6faf3"], [.3, "#bfe0b4"], [.65, "#3fa66b"], [1, "#0b3d2c"]],
                                   hovertemplate="%{y} · %{x}: %{z:,.0f} t<extra></extra>", colorbar=dict(title="t", thickness=10)))
        style(fig, 330, False); fig.update_yaxes(autorange="reversed", gridcolor="rgba(0,0,0,0)")
        pc(fig)

    titulo_graf("Detalle por territorio")
    T = G.sort_values("PRODUCCION", ascending=False)[["Territorio", "PRODUCCION", "part", "var", "COSECHA", "rend", "precio", "SIEMBRA"]]
    T.columns = ["Territorio", "Producción (t)", "% del área", "Var. % vs año ant.", "Cosecha (ha)", "Rend. (t/ha)", "Precio chacra (S/kg)", "Siembra (ha)"]
    tabla(T, hide_index=True, height=360, column_config={
        "Producción (t)": st.column_config.NumberColumn(format="%,.0f"),
        "% del área": st.column_config.ProgressColumn(format="%.1f%%", min_value=0, max_value=max(float(T["% del área"].max()), 1)),
        "Var. % vs año ant.": st.column_config.NumberColumn(format="%+.1f%%"),
        "Cosecha (ha)": st.column_config.NumberColumn(format="%,.0f"), "Rend. (t/ha)": st.column_config.NumberColumn(format="%.2f"),
        "Precio chacra (S/kg)": st.column_config.NumberColumn(format="%.2f"), "Siembra (ha)": st.column_config.NumberColumn(format="%,.0f")})

# ═════════ TAB 2: COMERCIO ═════════
with tabs[1]:
    COM = cargar_comercio()
    CX = COM[COM.CULTIVO == cultivo]
    if CX.empty:
        st.info(f"No hay partidas arancelarias de **{pretty(cultivo)}** en SISCOMEX. Elige un cultivo con comercio exterior (p. ej. cacao, café, palta, uva, arándano, espárrago, mango, quinua, papa, arroz…).")
    else:
        cc1, cc2 = st.columns([1, 1])
        flujo = cc1.radio("Flujo", ["Exportaciones", "Importaciones"], horizontal=True)
        mtr = cc2.radio("Variable", ["Peso neto (t)", "Valor FOB (miles US$)", "Valor CIF (miles US$)"] if flujo == "Importaciones" else ["Peso neto (t)", "Valor FOB (miles US$)"], horizontal=True)
        col = {"Peso neto (t)": "PESO_T", "Valor FOB (miles US$)": "FOB", "Valor CIF (miles US$)": "CIF"}[mtr]
        X = CX[CX.TIPO == flujo.upper()]
        mx_mes = X[X.ANIO == anio].MES.max() if (X.ANIO == anio).any() else None
        corte_c = min(corte, int(mx_mes)) if mx_mes == mx_mes and mx_mes is not None else corte
        if mx_mes is not None and mx_mes == mx_mes and corte > mx_mes:
            st.caption(f"Comercio exterior disponible hasta **{MESES_NOM[int(mx_mes)-1]} {anio}**; se acumula hasta ese mes.")
        Xc = X[X.ANIO.isin(anios_sel) & (X.MES <= corte_c)]
        Xp = X[X.ANIO.isin(prev_anios) & (X.MES <= corte_c)]
        tp, tpp = Xc.PESO_T.sum(), Xp.PESO_T.sum()
        tf, tfp = Xc.FOB.sum(), Xp.FOB.sum()
        k1, k2, k3, k4 = st.columns(4)
        kpi(k1, f"{flujo}: valor FOB", fmt_big(tf * 1000, " US$"), "", chip(delta(tf, tfp)) if prev_ok else chip(None), "oro")
        kpi(k2, "Peso neto", fmt(tp, 0), "t", chip(delta(tp, tpp)))
        kpi(k3, "Precio implícito FOB", fmt(tf / tp if tp > 0 else np.nan, 2), "US$/kg", chip(delta(tf / tp if tp else None, tfp / tpp if tpp else None)), "terra")
        kpi(k4, "Mercados de destino" if flujo == "Exportaciones" else "Países de origen", fmt(int((Xc.groupby("PAIS")[col].sum() > 0).sum()), 0), "países", "", "verde")
        st.write("")
        mc1, mc2 = st.columns([1.5, 1])
        with mc1:
            titulo_graf(f"{flujo} · {mtr} · Ene–{MESES_ABR[corte_c-1]} · {anios_txt}")
            xy = cargar_paises_xy()
            gp = Xc.groupby("PAIS")[col].sum()
            gp = gp[gp > 0]
            wm = mapas.base_map(f"{flujo} de {pretty(cultivo)}", f"{mtr} · ene–{MESES_ABR[corte_c-1].lower()} · {anios_txt}")
            wm.options["minZoom"] = 2
            cmw = mapas.Escala(list(gp.values), PALETA_ORO, n=5)
            keyval = {xy[p]["key"]: (p, v) for p, v in gp.items() if p in xy and xy[p]["key"]}
            tot = gp.sum()
            fe = []
            for f in cargar_geo("world")["features"]:
                kk = f["properties"]["key"]
                if kk in keyval:
                    p, v = keyval[kk]
                    fe.append({"type": "Feature", "geometry": f["geometry"], "properties": {"pais": p.title(), "v": float(v), "txt": f"{v:,.1f}", "pct": f"{v/tot*100:,.1f}%"}})
            if fe:
                folium.GeoJson({"type": "FeatureCollection", "features": fe}, style_function=lambda f: {"fillColor": cmw.color(f["properties"]["v"]), "color": "#fff", "weight": .6, "fillOpacity": .88},
                               highlight_function=lambda f: {"weight": 2, "color": "#0E3B2E"},
                               tooltip=folium.GeoJsonTooltip(fields=["pais", "txt", "pct"], aliases=["País", mtr, "% del total"], sticky=True)).add_to(wm)
            # burbujas para territorios sin polígono + flujos desde Perú para el top 10
            for p, v in gp.items():
                if p in xy and not xy[p]["key"]:
                    folium.CircleMarker([xy[p]["lat"], xy[p]["lon"]], radius=5 + 12 * math.sqrt(v / gp.max()), color="#7a3b1d", weight=1,
                                        fill=True, fill_color=ORO, fill_opacity=.85, tooltip=f"{p.title()}: {v:,.1f}").add_to(wm)
            peru = (-9.2, -75.0)
            for p, v in gp.sort_values(ascending=False).head(10).items():
                if p in xy and p != "PERU":
                    la, lo = xy[p]["lat"], xy[p]["lon"]
                    mid = ((peru[0] + la) / 2 + 0.22 * abs(lo - peru[1]) ** 0.9 * (1 if la > -50 else 0), (peru[1] + lo) / 2)
                    pts = [((1 - t) ** 2 * peru[0] + 2 * (1 - t) * t * mid[0] + t ** 2 * la, (1 - t) ** 2 * peru[1] + 2 * (1 - t) * t * mid[1] + t ** 2 * lo) for t in np.linspace(0, 1, 30)]
                    folium.PolyLine(pts, color=TERRA, weight=1 + 5 * v / gp.max(), opacity=.55, tooltip=f"{p.title()}: {v:,.1f}").add_to(wm)
            folium.Marker(peru, icon=folium.DivIcon(html='<div style="font-size:22px">📍</div>'), tooltip="Perú").add_to(wm)
            mapas.agregar_leyenda(wm, cmw.legend(mtr, lambda x: f"{x:,.0f}"))
            folium.LayerControl(collapsed=True, position="topright").add_to(wm)
            wm.fit_bounds([[-48, -125], [62, 150]])
            mostrar_mapa(wm, 540, f"wm_{cultivo}_{flujo}_{col}_{anios_txt}_{corte_c}")
            if "ZONAS FRANCAS DEL PERU" in Xc.PAIS.values:
                zf = Xc[Xc.PAIS == "ZONAS FRANCAS DEL PERU"][col].sum()
                if zf > 0: st.caption(f"Además, {zf:,.1f} ({mtr}) corresponden a Zonas Francas del Perú (sin ubicación en el mapa).")
        with mc2:
            titulo_graf("Principales destinos" if flujo == "Exportaciones" else "Principales orígenes")
            tp10 = gp.sort_values(ascending=False).head(10).iloc[::-1]
            fig = go.Figure(go.Bar(x=tp10.values, y=[s.title() for s in tp10.index], orientation="h", marker_color=ORO,
                                   text=[f"{v/tot*100:,.0f}%" for v in tp10.values], textposition="outside", cliponaxis=False))
            style(fig, 500, False); fig.update_layout(margin=dict(l=8, r=40, t=10, b=8)); fig.update_xaxes(title=mtr)
            pc(fig)
        s1, s2 = st.columns(2)
        ser = X[X.MES <= corte_c].groupby("ANIO")[["PESO_T", "FOB", "CIF"]].sum()
        ser = ser[ser.index >= 2015]
        with s1:
            titulo_graf(f"Evolución {flujo.lower()} · acumulado Ene–{MESES_ABR[corte_c-1]}")
            fig = make_subplots(specs=[[{"secondary_y": True}]])
            fig.add_bar(x=ser.index, y=ser[col], marker_color=[ORO if y in anios_sel else "#9fd3b0" for y in ser.index], name=mtr, secondary_y=False)
            fig.add_scatter(x=ser.index, y=ser.FOB / ser.PESO_T.replace(0, np.nan), mode="lines+markers", name="Precio FOB (US$/kg)", line=dict(color=TERRA, width=3), secondary_y=True)
            style(fig, 360); fig.update_xaxes(dtick=1); fig.update_yaxes(title_text=mtr, secondary_y=False); fig.update_yaxes(title_text="US$/kg", secondary_y=True, showgrid=False)
            pc(fig)
        with s2:
            titulo_graf("Estacionalidad del comercio (mensual)")
            ys_m = anios_sel if len(anios_sel) > 1 else [prev, anio]
            mensual = X[X.ANIO.isin(ys_m)].groupby(["ANIO", "MES"])[col].sum().unstack(0)
            fig = go.Figure()
            for i, y in enumerate(ys_m):
                if y in mensual.columns:
                    colr = ORO if (len(ys_m) == 2 and y == prev) else mapas.lerp_color(["#b9dfb0", "#3fa66b", "#0b3d2c"], i / max(len(ys_m) - 1, 1))
                    fig.add_scatter(x=[MESES_ABR[m - 1] for m in mensual.index], y=mensual[y], mode="lines+markers", name=str(y), line=dict(color=colr, width=3))
            style(fig, 360); fig.update_yaxes(title=mtr)
            pc(fig)
        if flujo == "Importaciones" or True:
            bal = COM[COM.CULTIVO == cultivo]
            b = bal[bal.MES <= corte_c].groupby(["ANIO", "TIPO"]).FOB.sum().unstack(fill_value=0)
            if {"EXPORTACIONES", "IMPORTACIONES"} <= set(b.columns):
                titulo_graf("Balanza comercial del cultivo (FOB, miles US$)")
                fig = go.Figure()
                fig.add_bar(x=b.index, y=b.EXPORTACIONES, name="Exportaciones", marker_color=HOJA)
                fig.add_bar(x=b.index, y=-b.IMPORTACIONES, name="Importaciones (−)", marker_color=TERRA)
                fig.add_scatter(x=b.index, y=b.EXPORTACIONES - b.IMPORTACIONES, name="Saldo", mode="lines+markers", line=dict(color="#222", width=2))
                style(fig, 320); fig.update_layout(barmode="relative"); fig.update_xaxes(dtick=1)
                pc(fig)
        st.caption("Unidades según la fuente: valores FOB/CIF en miles de US$ y peso neto en toneladas. Las partidas arancelarias se asignan al cultivo por capítulo/partida (ver nota metodológica).")

# ═════════ TAB 3: PRECIOS Y VBP ═════════
with tabs[2]:
    p1, p2 = st.columns(2)
    # Producción + precio chacra anual
    full = DG.copy()
    an = full.groupby("ANIO").agg(PRODUCCION=("PRODUCCION", "sum"), PXP=("PXP", "sum"), PRODP=("PRODP", "sum"))
    an["precio"] = an.PXP / an.PRODP.replace(0, np.nan)
    an = an[an.index >= 2016]
    with p1:
        titulo_graf("Producción anual y precio en chacra")
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_bar(x=an.index, y=an.PRODUCCION, marker_color=["#9fd3b0" if not (y == ult_anio and ult_mes < 12) else "#cfe6bf" for y in an.index], name="Producción (t)",
                    text=[fmt_big(v) for v in an.PRODUCCION], textposition="outside", cliponaxis=False, secondary_y=False)
        fig.add_scatter(x=an.index, y=an.precio, mode="lines+markers", name="Precio chacra (S/kg)", line=dict(color=TERRA, width=3), secondary_y=True)
        style(fig, 380); fig.update_xaxes(dtick=1); fig.update_yaxes(title_text="t", secondary_y=False); fig.update_yaxes(title_text="S/ por kg", secondary_y=True, showgrid=False)
        pc(fig); st.caption(f"{ult_anio} es un año parcial (hasta {MESES_NOM[ult_mes-1]}).")
    with p2:
        titulo_graf("Precio en chacra vs precio mayorista")
        S = cargar_sisap()
        SC = S[S.CULTIVO == cultivo]
        if SC.empty:
            st.info("SISAP no registra precios mayoristas para este cultivo.")
        else:
            vars_ = ["Promedio de variedades"] + sorted(SC.VARIEDAD.unique())
            vsel = st.selectbox("Variedad mayorista", vars_, label_visibility="collapsed")
            sm = (SC if vsel == vars_[0] else SC[SC.VARIEDAD == vsel]).groupby("ANIO").PRECIO_KG.mean()
            fig = go.Figure()
            fig.add_scatter(x=an.index, y=an.precio, name="Precio chacra", mode="lines+markers", line=dict(color=HOJA, width=3))
            fig.add_scatter(x=sm.index, y=sm.values, name="Precio mayorista (SISAP)", mode="lines+markers", line=dict(color=ORO, width=3))
            style(fig, 340); fig.update_yaxes(title="S/ por kg"); fig.update_xaxes(dtick=1)
            pc(fig)
            comp = pd.concat([an.precio.rename("c"), sm.rename("m")], axis=1).dropna()
            if len(comp):
                last = comp.iloc[-1]
                st.caption(f"En {int(comp.index[-1])}, el mayorista fue {last.m:,.2f} S/kg vs {last.c:,.2f} S/kg en chacra: margen de comercialización de {(last.m/last.c-1)*100:,.0f}%.")
    st.markdown("---")
    # VBP
    V = cargar_vbp()
    VC = V[(V.CULTIVO == cultivo) & (V.TIPO == "AGRÍCOLA")]
    if VC.empty:
        st.info("Este cultivo no figura en la base de Valor Bruto de la Producción (VBP).")
    else:
        VCg = VC if dep == "Todos" else VC[VC.DEPARTAMENTO == dep]
        VT = V[(V.TIPO == "AGRÍCOLA") & (V.MESN <= corte)]
        vy = VCg[VCg.MESN <= corte].groupby("ANIO").VBP.sum()
        nat = VT.groupby("ANIO").VBP.sum()
        vk = vy[vy.index.isin(anios_sel)].sum()
        vk_prev = vy[vy.index.isin(prev_anios)].sum() if prev_ok else None
        nat_sel = nat[nat.index.isin(anios_sel)].sum()
        q1, q2, q3 = st.columns(3)
        kpi(q1, f"VBP Ene–{MESES_ABR[corte-1]} · {anios_txt}" + (f" · {dep.title()}" if dep != "Todos" else ""), fmt(vk, 1), "millones S/", chip(delta(vk, vk_prev)), "oro")
        kpi(q2, "Participación en el VBP agrícola nacional", fmt(vk / nat_sel * 100 if nat_sel else np.nan, 2), "%", '<span class="nd">VBP del cultivo / VBP agrícola total</span>', "verde")
        rk = VT[VT.ANIO.isin(anios_sel)].groupby("CULTIVO").VBP.sum().rank(ascending=False)
        kpi(q3, "Posición entre cultivos (VBP)", f"#{int(rk.get(cultivo, 0))}" if cultivo in rk.index else "N/D", f"de {len(rk)}", "", "verde")
        st.write("")
        v1, v2 = st.columns(2)
        with v1:
            titulo_graf(f"VBP acumulado Ene–{MESES_ABR[corte-1]} (millones S/)")
            vv = vy[vy.index >= 2010]
            fig = make_subplots(specs=[[{"secondary_y": True}]])
            fig.add_bar(x=vv.index, y=vv.values, marker_color=[ORO if y in anios_sel else HOJA for y in vv.index], name="VBP", secondary_y=False)
            sh = (vv / nat.reindex(vv.index) * 100)
            fig.add_scatter(x=sh.index, y=sh.values, name="% del VBP agrícola", mode="lines+markers", line=dict(color=TERRA, width=3), secondary_y=True)
            style(fig, 360); fig.update_yaxes(title_text="millones S/", secondary_y=False); fig.update_yaxes(title_text="%", secondary_y=True, showgrid=False)
            pc(fig)
        with v2:
            titulo_graf(f"VBP por departamento · Ene–{MESES_ABR[corte-1]} · {anios_txt}")
            vd = VC[VC.ANIO.isin(anios_sel) & (VC.MESN <= corte)].groupby("DEPARTAMENTO").VBP.sum().sort_values().tail(12)
            fig = go.Figure(go.Bar(x=vd.values, y=[x.title() for x in vd.index], orientation="h", marker_color=VERDE2,
                                   text=[f"{v:,.1f}" for v in vd.values], textposition="outside", cliponaxis=False))
            style(fig, 360, False); fig.update_layout(margin=dict(l=8, r=40, t=10, b=8)); fig.update_xaxes(title="millones S/")
            pc(fig)
        st.caption("VBP = producción × precio en chacra, en millones de soles corrientes, según la base DATA_VBP.")

# ═════════ TAB 4: COMPARADOR ═════════
with tabs[3]:
    st.markdown("Compara hasta 5 cultivos en el período acumulado **Ene–" + MESES_ABR[corte - 1] + "**.")
    cmp_def = [c for c in [cultivo, "PALTA", "UVA", "ARANDANO", "CAFE"] if c in CAT.cultivo.values][:4]
    sel = st.multiselect("Cultivos", CAT.cultivo.tolist(), default=cmp_def, max_selections=5, format_func=pretty)
    mt = st.radio("Indicador", ["Producción (t)", "Precio chacra (S/kg)", "VBP (millones S/)", "Exportaciones FOB (miles US$)"], horizontal=True)
    base100 = st.toggle("Índice base 100 (primer año disponible)", value=True)
    series = {}
    for c in sel:
        r = CAT[CAT.cultivo == c].iloc[0]
        if mt in ("Producción (t)", "Precio chacra (S/kg)"):
            d = cargar_cultivo(r.slug, r.nivel)
            d = d[(d.MES <= corte) & (d.ANIO >= 2016)]
            g = d.groupby("ANIO")[["PRODUCCION", "PXP", "PRODP"]].sum()
            series[c] = g.PRODUCCION if mt.startswith("Prod") else g.PXP / g.PRODP.replace(0, np.nan)
        elif mt.startswith("VBP"):
            vv = cargar_vbp(); vv = vv[(vv.CULTIVO == c) & (vv.TIPO == "AGRÍCOLA") & (vv.MESN <= corte) & (vv.ANIO >= 2016)]
            series[c] = vv.groupby("ANIO").VBP.sum()
        else:
            cx_ = cargar_comercio(); cx_ = cx_[(cx_.CULTIVO == c) & (cx_.TIPO == "EXPORTACIONES") & (cx_.MES <= corte)]
            series[c] = cx_.groupby("ANIO").FOB.sum()
    SER = pd.DataFrame(series).dropna(how="all")
    SER = SER[[c for c in SER.columns if SER[c].notna().any()]]
    if SER.empty:
        st.warning("Sin datos para la selección.")
    else:
        P = SER.copy()
        if base100:
            P = SER.apply(lambda s: s / s.dropna().iloc[0] * 100 if s.dropna().iloc[0] else s)
        fig = go.Figure()
        colores = [HOJA, ORO, TERRA, VERDE2, "#5b6fb5"]
        for i, c in enumerate(P.columns):
            fig.add_scatter(x=P.index, y=P[c], mode="lines+markers", name=pretty(c), line=dict(color=colores[i % 5], width=3))
        style(fig, 430); fig.update_xaxes(dtick=1); fig.update_yaxes(title="Índice (base 100)" if base100 else mt)
        pc(fig)
        crec = []
        for c in SER.columns:
            s = SER[c].dropna()
            if len(s) > 1 and s.iloc[0] > 0:
                n = len(s) - 1
                crec.append({"Cultivo": pretty(c), f"Último año ({int(s.index[-1])})": s.iloc[-1], "Crec. promedio anual (TCAC %)": ((s.iloc[-1] / s.iloc[0]) ** (1 / n) - 1) * 100,
                             "Variación último año %": (s.iloc[-1] / s.iloc[-2] - 1) * 100 if len(s) > 1 and s.iloc[-2] else np.nan})
        if crec:
            tabla(pd.DataFrame(crec), hide_index=True, column_config={"Crec. promedio anual (TCAC %)": st.column_config.NumberColumn(format="%+.1f%%"),
                                                                       "Variación último año %": st.column_config.NumberColumn(format="%+.1f%%")})

# ═════════ TAB 5: DATOS ═════════
with tabs[4]:
    st.markdown("Descarga los datos del cultivo y la ubicación seleccionados.")
    mens = DG.groupby(["ANIO", "MES"]).agg(PRODUCCION_t=("PRODUCCION", "sum"), COSECHA_ha=("COSECHA", "sum"), SIEMBRA_ha=("SIEMBRA", "sum"),
                                           VERDE_ACTUAL_ha=("VERDE_ACTUAL", "sum"), PXP=("PXP", "sum"), PRODP=("PRODP", "sum")).reset_index()
    mens["PRECIO_CHACRA_S_kg"] = mens.PXP / mens.PRODP.replace(0, np.nan)
    mens = mens.drop(columns=["PXP", "PRODP"])
    st.markdown("**Serie mensual**"); tabla(mens, hide_index=True, height=300)
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as xw:
        mens.to_excel(xw, sheet_name="Serie_mensual", index=False)
        T.to_excel(xw, sheet_name="Territorios_periodo", index=False)
        if not CX.empty: CX.to_excel(xw, sheet_name="Comercio_exterior", index=False)
        if not VC.empty: VC.to_excel(xw, sheet_name="VBP", index=False)
    d1, d2 = st.columns(2)
    d1.download_button("⬇️ Descargar Excel", buf.getvalue(), file_name=f"perfil_{info.slug}_{'_'.join(map(str, anios_sel))}.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    d2.download_button("⬇️ Descargar CSV (serie mensual)", mens.to_csv(index=False).encode("utf-8-sig"), file_name=f"serie_{info.slug}.csv", mime="text/csv")

with st.expander("ℹ️ Notas metodológicas"):
    st.markdown(f"""
- **Producción, siembra, cosecha, superficie instalada y precio en chacra**: SISAGRI (mensual, distrital). Las variedades se agrupan por cultivo (p. ej. *Palta Hass/Fuerte → Palta*). Los registros múltiples de un mismo distrito-mes se suman.
- **Precio en chacra** = promedio ponderado por producción (S/ por kg). **Rendimiento** = producción ÷ superficie cosechada del período.
- **Cosecha y rendimiento** se muestran como N/D en el año en curso (se consolidan al cierre), igual que el tablero original.
- **Superficie instalada** = área "verde actual" al último mes del acumulado (es un stock, no se suma entre meses).
- **Variaciones** comparan el mismo período Ene–mes del año anterior. 2015 se excluye por iniciar en febrero.
- **Arándano, caña de azúcar (azúcar/etanol), palma aceitera y frijol loctao**: solo detalle departamental (archivo *Otros cultivos*).
- **Comercio exterior**: SISCOMEX, partidas arancelarias asignadas por capítulo/partida al cultivo. FOB/CIF en miles de US$; peso neto en toneladas.
- **Precio mayorista**: SISAP (promedio anual por variedad). **VBP**: DATA_VBP en millones de S/.
- **Clasificación permanente/transitorio**: criterio propio basado en el tablero de referencia; ajustable en `common.py`.
- **Número de productores**: no está disponible en las fuentes entregadas, por eso se reemplazó por *distritos productores*.
""")
