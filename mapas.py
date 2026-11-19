"""Constructores de mapas Folium (estilo editorial: tarjeta de título, buscador, capas base, leyendas propias)."""
import json
import math

import folium
import numpy as np
from branca.element import MacroElement, Template
from folium.plugins import Fullscreen, HeatMap, MarkerCluster, MousePosition, Search

# Tiles: CARTO ya exige API key, por eso se usan Esri / OpenTopoMap / sin fondo.
BLANK = "data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"
ESRI = "https://server.arcgisonline.com/ArcGIS/rest/services/{}/MapServer/tile/{{z}}/{{y}}/{{x}}"
OCEANO = "#cfe2ec"

FONT = "font-family:'Source Sans 3',Segoe UI,Arial,sans-serif;"
CARD = "background:rgba(255,255,255,.95);border-radius:10px;box-shadow:0 1px 8px rgba(0,0,0,.28);"

# Colores fijos por cultivo (coherentes en todos los mapas); el resto usa la paleta de respaldo
COLORES_CULTIVO = {
    "PAPA": "#8d6e63", "PALTA": "#2e7d32", "ARROZ": "#f6c244", "ESPARRAGO": "#17958b", "ARANDANO": "#3f51b5",
    "UVA": "#8e24aa", "MAIZ AMARILLO DURO": "#f57c00", "MAIZ AMILACEO": "#ffb74d", "MAIZ CHALA": "#9ccc65",
    "MAIZ CHOCLO": "#d4e157", "ALFALFA": "#43a047", "CEBADA": "#c0ca33", "TRIGO BLANDO": "#afb42b",
    "PIMIENTO": "#e53935", "CEBOLLA": "#d81b60", "CAFE": "#4e342e", "CACAO": "#a1665a", "PLATANO": "#fdd835",
    "MANGO": "#ff9800", "LIMON": "#cddc39", "MANDARINA": "#ffa726", "NARANJA": "#fb8c00", "QUINUA": "#ab47bc",
    "YUCA": "#bcaaa4", "FRIJOL GRANO SECO": "#795548", "HABA GRANO SECO": "#689f38", "ARVEJA GRANO VERDE": "#7cb342",
    "ACEITUNA": "#6d6f2b", "PIÑA": "#ffd54f", "TOMATE": "#ef5350", "ALCACHOFA": "#26a69a", "CAMOTE": "#ba68c8",
    "PAPRIKA": "#c62828", "MAIZ MORADO": "#6a1b9a", "OLLUCO": "#ec407a", "PASTOS": "#81c784", "AVENA FORRAJERA": "#aed581",
}
PALETA_RESPALDO = ["#5c6bc0", "#26c6da", "#ff7043", "#8d6e63", "#78909c", "#d4a017", "#00897b", "#ad1457", "#558b2f", "#6d4c41"]


def colores_para(cultivos):
    out, k = {}, 0
    for c in cultivos:
        if c in COLORES_CULTIVO:
            out[c] = COLORES_CULTIVO[c]
        else:
            out[c] = PALETA_RESPALDO[k % len(PALETA_RESPALDO)]; k += 1
    return out


# ───────────────────────── Escalas y leyendas ─────────────────────────
def _hex(c): return tuple(int(c[i:i + 2], 16) for i in (1, 3, 5))


def lerp_color(paleta, t):
    t = min(max(t, 0), 1) * (len(paleta) - 1)
    i = min(int(t), len(paleta) - 2); f = t - i
    a, b = _hex(paleta[i]), _hex(paleta[i + 1])
    return "#%02x%02x%02x" % tuple(round(a[k] + (b[k] - a[k]) * f) for k in range(3))


class Escala:
    """Escala por cuantiles (clases) con color de 'sin dato'."""

    def __init__(self, vals, paleta, n=6, nodata="#e4e8e5"):
        v = np.array([x for x in vals if x is not None and np.isfinite(x) and x > 0], dtype=float)
        self.nodata = nodata
        if v.size == 0:
            self.edges, self.cols = [0.0, 1.0], [nodata]
            return
        qs = np.unique(np.quantile(v, np.linspace(0, 1, n + 1)))
        if len(qs) < 2: qs = np.array([v.min(), v.min() + 1e-9])
        self.edges = [float(x) for x in qs]
        k = len(qs) - 1
        self.cols = [lerp_color(paleta, i / max(k - 1, 1)) for i in range(k)]

    def color(self, v):
        if v is None or not np.isfinite(v) or v <= 0: return self.nodata
        i = int(np.searchsorted(self.edges, v, side="right")) - 1
        return self.cols[min(max(i, 0), len(self.cols) - 1)]

    def legend(self, titulo, fmt=lambda x: f"{x:,.1f}"):
        rows = "".join(f'<div style="display:flex;align-items:center;gap:7px;margin:2px 0"><span style="width:18px;height:12px;background:{c};border-radius:2px;border:1px solid rgba(0,0,0,.15)"></span>'
                       f'{fmt(self.edges[i])} – {fmt(self.edges[i + 1])}</div>' for i, c in enumerate(self.cols))
        rows += f'<div style="display:flex;align-items:center;gap:7px;margin:2px 0;color:#7a8680"><span style="width:18px;height:12px;background:{self.nodata};border-radius:2px;border:1px solid rgba(0,0,0,.15)"></span>Sin dato</div>'
        return _legend_box(titulo, rows)


class EscalaDiv:
    """Escala divergente simétrica en torno a 0 (variaciones %)."""

    def __init__(self, m, colores=("#c0392b", "#f6f4ee", "#1f8f55"), nodata="#e4e8e5"):
        self.m, self.colores, self.nodata = m, list(colores), nodata

    def color(self, v):
        if v is None or not np.isfinite(v): return self.nodata
        return lerp_color(self.colores, (max(-self.m, min(self.m, v)) + self.m) / (2 * self.m))

    def legend(self, titulo, fmt=None):
        g = f"linear-gradient(90deg,{','.join(self.colores)})"
        rows = (f'<div style="width:170px;height:12px;background:{g};border-radius:3px;border:1px solid rgba(0,0,0,.15)"></div>'
                f'<div style="display:flex;justify-content:space-between;width:170px;margin-top:2px"><span>−{self.m:,.0f}%</span><span>0</span><span>+{self.m:,.0f}%</span></div>'
                f'<div style="margin-top:4px;color:#7a8680"><span style="display:inline-block;width:12px;height:10px;background:{self.nodata};border:1px solid rgba(0,0,0,.15);margin-right:5px"></span>Sin dato</div>')
        return _legend_box(titulo, rows)


def _legend_box(titulo, rows_html):
    return f'<div style="{CARD}{FONT}padding:8px 11px;font-size:12px;color:#26372f;max-height:300px;overflow:auto"><div style="font-weight:700;margin-bottom:5px">{titulo}</div>{rows_html}</div>'


def legend_categorica(titulo, items):
    rows = "".join(f'<div style="display:flex;align-items:center;gap:7px;margin:2px 0"><span style="width:12px;height:12px;background:{c};border-radius:50%;border:1px solid rgba(0,0,0,.2)"></span>{t}</div>' for t, c in items)
    return _legend_box(titulo, rows)


# ───────────────────────── Controles (JS) ─────────────────────────
class _Ctl(MacroElement):
    _template = Template("""{% macro script(this, kwargs) %}
(function(){ try {
  var map_ = {{ this._parent.get_name() }};
  var c = L.control({position: '{{ this.position }}'});
  c.onAdd = function(){
    var d = L.DomUtil.create('div'); d.innerHTML = {{ this.html_json }};
    L.DomEvent.disableClickPropagation(d); L.DomEvent.disableScrollPropagation(d);
    {{ this.js_after }}
    return d;
  };
  c.addTo(map_);
} catch(e) { console.error('control', e); } })();
{% endmacro %}""")

    def __init__(self, html, position="topright", js_after=""):
        super().__init__()
        self._name = "Ctl"
        self.html_json, self.position, self.js_after = json.dumps(html), position, js_after


class _Chrome(MacroElement):
    """Fondo del mapa + tarjeta de título centrada (como en los mapas de referencia)."""
    _template = Template("""{% macro script(this, kwargs) %}
(function(){ try {
  var map_ = {{ this._parent.get_name() }};
  var ct = map_.getContainer(); ct.style.background = '{{ this.bg }}';
  var d = L.DomUtil.create('div', '', ct);
  d.style.cssText = {{ this.css_json }};
  d.innerHTML = {{ this.html_json }};
} catch(e) { console.error('chrome', e); } })();
{% endmacro %}""")

    def __init__(self, titulo, subtitulo, bg):
        super().__init__()
        self._name = "Chrome"
        self.bg = bg
        self.css_json = json.dumps("position:absolute;top:12px;left:50%;transform:translateX(-50%);z-index:1000;pointer-events:none;"
                                   "text-align:center;max-width:55%;padding:8px 18px;" + CARD + FONT)
        self.html_json = json.dumps(f'<div style="font-weight:700;font-size:15px;color:#14261d">{titulo}</div>'
                                    f'<div style="font-size:11.5px;color:#66756d">{subtitulo}</div>')


def base_map(titulo, subtitulo, bg=OCEANO, claro=True, mouse=True):
    m = folium.Map(location=[-9.2, -75], zoom_start=5, tiles=None, control_scale=True, prefer_canvas=True, zoom_snap=0.25)
    folium.TileLayer(BLANK, attr=" ", name="Sin fondo (limpio)", overlay=False, control=True).add_to(m)
    folium.TileLayer(ESRI.format("World_Imagery"), attr="Esri World Imagery", name="Satélite (Esri)", overlay=False, show=False).add_to(m)
    folium.TileLayer("https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png", attr="OpenTopoMap", name="Relieve (OpenTopoMap)", overlay=False, show=False).add_to(m)
    folium.TileLayer(ESRI.format("World_Topo_Map"), attr="Esri World Topo", name="Topográfico (Esri)", overlay=False, show=False).add_to(m)
    folium.TileLayer(ESRI.format("Elevation/World_Hillshade"), attr="Esri", name="Sombreado de relieve", overlay=True, show=False, opacity=.55).add_to(m)
    folium.TileLayer(ESRI.format("Reference/World_Boundaries_and_Places"), attr="Esri", name="Nombres de lugares (Esri)", overlay=True, show=False).add_to(m)
    Fullscreen(position="topleft", title="Pantalla completa", title_cancel="Salir").add_to(m)
    if mouse:
        MousePosition(position="bottomleft", prefix="Lat/Lon:", separator=" · ", num_digits=3).add_to(m)
    m.add_child(_Chrome(titulo, subtitulo, bg))
    return m


def agregar_selector_dpto(m, bounds_dep, texto_todos="Todo el Perú", nacional=((-18.5, -81.5), (0.0, -68.5)), actual=None):
    opts = f'<option value="__all">{texto_todos}</option>' + "".join(f'<option value="{k}"{" selected" if k == actual else ""}>{k.title()}</option>' for k in sorted(bounds_dep))
    b = dict(bounds_dep); b["__all"] = [list(nacional[0]), list(nacional[1])]
    html = f'<div style="{CARD}{FONT}padding:5px 8px;font-size:13px;display:flex;gap:6px;align-items:center">📍<select style="border:1px solid #ccd5cf;border-radius:6px;padding:2px 4px;{FONT}">{opts}</select></div>'
    js = f"d.querySelector('select').onchange=function(){{var B={json.dumps(b)};map_.fitBounds(B[this.value],{{padding:[10,10]}});}};"
    m.add_child(_Ctl(html, "topleft", js))


def agregar_leyenda(m, html, pos="bottomleft"):
    m.add_child(_Ctl(html, pos))


def etiquetas(m, items, nombre="Etiquetas", show=True, color="#1b2b23", halo="#ffffff", size=11):
    """items: (lat, lon, titulo, subtitulo|None)"""
    fg = folium.FeatureGroup(name=nombre, show=show)
    sh = f"-1px -1px 0 {halo},1px -1px 0 {halo},-1px 1px 0 {halo},1px 1px 0 {halo}"
    for la, lo, t, s in items:
        sub = f'<div style="font-weight:600;font-size:{size-1}px">{s}</div>' if s else ""
        html = f'<div style="transform:translate(-50%,-50%);text-align:center;white-space:nowrap;{FONT}font-weight:700;font-size:{size}px;color:{color};text-shadow:{sh};line-height:1.1">{t}{sub}</div>'
        folium.Marker([la, lo], icon=folium.DivIcon(html=html, icon_size=(0, 0), icon_anchor=(0, 0)), interactive=False).add_to(fg)
    fg.add_to(m)


def bbox(features):
    xs, ys = [], []
    def rec(c):
        if isinstance(c[0], (int, float)): xs.append(c[0]); ys.append(c[1])
        else:
            for k in c: rec(k)
    for f in features:
        if f.get("geometry"): rec(f["geometry"]["coordinates"])
    return [[min(ys), min(xs)], [max(ys), max(xs)]] if xs else [[-18.5, -81.5], [0.0, -68.5]]


def agregar_buscador(m, layer, campo="n", placeholder="Buscar territorio…"):
    Search(layer=layer, geom_type="Polygon", placeholder=placeholder, collapsed=True, search_label=campo,
           position="topleft", search_zoom=9).add_to(m)


def contorno(m, features, nombre="Límite departamental", color="#14261d", peso=1.6, show=True):
    folium.GeoJson({"type": "FeatureCollection", "features": features}, name=nombre, show=show,
                   style_function=lambda f: {"fillOpacity": 0, "color": color, "weight": peso}, interactive=False).add_to(m)


def _n(x, d=1):
    return "N/D" if x is None or (isinstance(x, float) and not np.isfinite(x)) else f"{x:,.{d}f}"


# ───────────────────────── Mapas multicultivo (distrito × cultivo) ─────────────────────────
def _agrupa(M, ctx):
    """M: filas (CULTIVO, UBIGEO, PRODUCCION, PXP, COSECHA) ya agregadas por distrito-cultivo."""
    return M[(M.PRODUCCION > 0) | (M.PXP > 0)].copy()


def mapa_cultivo_principal(M, feats, names, titulo, subtitulo, bounds_dep, contorno_feats, nombres_cultivo):
    M = _agrupa(M, None)
    M["V"] = M.PXP / 1000.0                          # millones de S/
    tot = M.groupby("UBIGEO").V.sum()
    M = M.sort_values(["UBIGEO", "V"], ascending=[True, False])
    top = M.groupby("UBIGEO").head(1).set_index("UBIGEO")
    top3 = M.groupby("UBIGEO").head(3).groupby("UBIGEO").apply(
        lambda g: "<br>".join(f"{nombres_cultivo[c]}: {v:,.2f} M S/" for c, v in zip(g.CULTIVO, g.V)), include_groups=False)
    orden = top.CULTIVO.value_counts()
    cols = colores_para(list(orden.index))
    fe = []
    for f in feats:
        k = f["properties"]["IDDIST"]
        if k in top.index:
            c, v = top.loc[k, "CULTIVO"], float(top.loc[k, "V"])
            fe.append({"type": "Feature", "geometry": f["geometry"], "properties": {
                "n": names[k][0].title(), "ctx": f"{names[k][1].title()} · {names[k][2].title()}", "cult": nombres_cultivo[c], "col": cols[c],
                "val": f"{v:,.2f} M S/", "part": f"{v / tot[k] * 100:,.0f}%" if tot[k] > 0 else "N/D", "top3": top3.get(k, "")}})
        else:
            fe.append({"type": "Feature", "geometry": f["geometry"], "properties": {"n": names.get(f["properties"]["IDDIST"], ("",))[0].title(), "ctx": "", "cult": "Sin registro", "col": "#e4e8e5", "val": "N/D", "part": "N/D", "top3": ""}})
    m = base_map(titulo, subtitulo)
    g = folium.GeoJson({"type": "FeatureCollection", "features": fe}, name="Cultivo principal",
                       style_function=lambda f: {"fillColor": f["properties"]["col"], "color": "#fff", "weight": .5, "fillOpacity": .9},
                       highlight_function=lambda f: {"weight": 2, "color": "#14261d"},
                       tooltip=folium.GeoJsonTooltip(fields=["n", "ctx", "cult", "val", "part", "top3"],
                                                     aliases=["Distrito", "Ubicación", "Cultivo principal", "Valor", "% del valor distrital", "Top 3"], sticky=True, style=FONT + "font-size:12.5px;"))
    g.add_to(m)
    contorno(m, contorno_feats)
    agregar_buscador(m, g, "n", "Buscar distrito…")
    items = [(nombres_cultivo[c], cols[c]) for c in orden.index[:14]]
    if len(orden) > 14: items.append((f"Otros ({len(orden) - 14})", "#9aa5a0"))
    agregar_leyenda(m, legend_categorica(f"Cultivo principal (por valor) · {len(top)} distritos", items))
    agregar_selector_dpto(m, bounds_dep)
    folium.LayerControl(collapsed=True, position="topright").add_to(m)
    m.fit_bounds(bbox(feats))
    return m


def mapa_burbujas(M, feats, names, cent, titulo, subtitulo, bounds_dep, contorno_feats, nombres_cultivo, topk=5, max_burbujas=1800):
    M = _agrupa(M, None)
    M["V"] = M.PXP / 1000.0
    M = M[M.V > 0].sort_values(["UBIGEO", "V"], ascending=[True, False])
    M = M.groupby("UBIGEO").head(topk)
    if len(M) > max_burbujas:
        M = M.nlargest(max_burbujas, "V")
    orden = M.groupby("CULTIVO").V.sum().sort_values(ascending=False)
    cols = colores_para(list(orden.index))
    m = base_map(titulo, subtitulo)
    folium.GeoJson({"type": "FeatureCollection", "features": [{"type": "Feature", "geometry": f["geometry"], "properties": {}} for f in feats]},
                   style_function=lambda f: {"fillColor": "#f5f2e6", "color": "#b7b2a0", "weight": .5, "fillOpacity": 1}, interactive=False, name="Distritos").add_to(m)
    contorno(m, contorno_feats)
    vmax = float(M.V.max()) if len(M) else 1.0
    grp = {c: folium.FeatureGroup(name=nombres_cultivo[c]) for c in orden.index}
    idx = {}
    for r in M.itertuples():
        k = r.UBIGEO
        if k not in cent["dist"]: continue
        j = idx.get(k, 0); idx[k] = j + 1
        la, lo = cent["dist"][k]
        ang = 2 * math.pi * j / max(topk, 1) + (hash(k) % 628) / 100
        off = 0.0 if j == 0 else 0.028
        la, lo = la + off * math.sin(ang), lo + off * math.cos(ang)
        rend = r.PRODUCCION / r.COSECHA if r.COSECHA > 0 else None
        pop = (f'<div style="{FONT}font-size:12.5px"><b>{nombres_cultivo[r.CULTIVO]}</b><br>{names[k][0].title()} · {names[k][1].title()}<br>'
               f'Producción: <b>{_n(r.PRODUCCION, 1)} t</b><br>Valor: <b>{_n(r.V, 2)} M S/</b><br>Cosecha: {_n(r.COSECHA, 0)} ha · Rend.: {_n(rend, 2)} t/ha</div>')
        folium.CircleMarker([la, lo], radius=3 + 17 * math.sqrt(r.V / vmax), color="#ffffff", weight=1, fill=True, fill_color=cols[r.CULTIVO], fill_opacity=.82,
                            tooltip=f"{nombres_cultivo[r.CULTIVO]} · {names[k][0].title()}: {r.V:,.2f} M S/", popup=folium.Popup(pop, max_width=260)).add_to(grp[r.CULTIVO])
    for g in grp.values(): g.add_to(m)
    items = [(nombres_cultivo[c], cols[c]) for c in orden.index[:14]]
    agregar_leyenda(m, legend_categorica(f"Cultivo (top {topk} por distrito) · tamaño = valor", items))
    agregar_selector_dpto(m, bounds_dep)
    folium.LayerControl(collapsed=True, position="topright").add_to(m)
    m.fit_bounds(bbox(feats))
    return m


def mapa_clusters(M, feats, names, cent, titulo, subtitulo, bounds_dep, contorno_feats, nombres_cultivo, max_reg=2500):
    M = _agrupa(M, None)
    M["V"] = M.PXP / 1000.0
    n_total = len(M)
    if n_total > max_reg: M = M.nlargest(max_reg, "V")
    orden = M.CULTIVO.value_counts()
    cols = colores_para(list(orden.index))
    m = base_map(titulo, subtitulo)
    folium.GeoJson({"type": "FeatureCollection", "features": [{"type": "Feature", "geometry": f["geometry"], "properties": {}} for f in feats]},
                   style_function=lambda f: {"fillColor": "#f5f2e6", "color": "#b7b2a0", "weight": .5, "fillOpacity": 1}, interactive=False, name="Distritos").add_to(m)
    contorno(m, contorno_feats)
    mc = MarkerCluster(name="Registros distrito-cultivo", options={"showCoverageOnHover": False, "maxClusterRadius": 45}).add_to(m)
    for r in M.itertuples():
        k = r.UBIGEO
        if k not in cent["dist"]: continue
        rend = r.PRODUCCION / r.COSECHA if r.COSECHA > 0 else None
        pop = (f'<div style="{FONT}font-size:12.5px"><b>{nombres_cultivo[r.CULTIVO]}</b><br>{names[k][0].title()} · {names[k][1].title()} · {names[k][2].title()}<br>'
               f'Producción: <b>{_n(r.PRODUCCION, 1)} t</b><br>Valor: <b>{_n(r.V, 2)} M S/</b><br>Rend.: {_n(rend, 2)} t/ha</div>')
        dot = f'<div style="width:14px;height:14px;border-radius:50%;background:{cols[r.CULTIVO]};border:2px solid #fff;box-shadow:0 0 3px rgba(0,0,0,.5)"></div>'
        folium.Marker(cent["dist"][k], icon=folium.DivIcon(html=dot, icon_size=(14, 14), icon_anchor=(7, 7)),
                      tooltip=f"{nombres_cultivo[r.CULTIVO]} · {names[k][0].title()}", popup=folium.Popup(pop, max_width=260)).add_to(mc)
    items = [(f"{nombres_cultivo[c]} ({n})", cols[c]) for c, n in orden.items()][:14]
    nota = f" (top {max_reg:,} por valor)" if n_total > max_reg else ""
    agregar_leyenda(m, legend_categorica(f"Registros: {len(M):,}{nota}", items))
    agregar_selector_dpto(m, bounds_dep)
    folium.LayerControl(collapsed=True, position="topright").add_to(m)
    m.fit_bounds(bbox(feats))
    return m


def mapa_calor(M, feats, cent, names, titulo, subtitulo, bounds_dep, prov_labels):
    M = _agrupa(M, None)
    M["w"] = M.PRODUCCION / M.groupby("CULTIVO").PRODUCCION.transform("max").replace(0, np.nan)     # normaliza por cultivo
    W = M.groupby("UBIGEO").w.sum()
    pts = [[*cent["dist"][k], float(v)] for k, v in W.items() if k in cent["dist"] and v > 0]
    mx = max([p[2] for p in pts]) if pts else 1.0
    pts = [[a, b, (c / mx) ** 0.6] for a, b, c in pts]
    m = base_map(titulo, subtitulo, bg="#0b0d0c")
    folium.GeoJson({"type": "FeatureCollection", "features": [{"type": "Feature", "geometry": f["geometry"], "properties": {}} for f in feats]},
                   style_function=lambda f: {"fillColor": "#141917", "color": "#3a4540", "weight": .4, "fillOpacity": 1}, interactive=False, name="Distritos").add_to(m)
    HeatMap(pts, name="Polos agroproductivos", radius=26, blur=22, min_opacity=.3, max_zoom=9,
            gradient={0.2: "#2b4a6f", 0.4: "#7a9a5b", 0.6: "#e8b25a", 0.8: "#ee6c3c", 1.0: "#e11d1d"}).add_to(m)
    if prov_labels: etiquetas(m, prov_labels, "Nombres de provincias", color="#f2f5f3", halo="#0b0d0c", size=11)
    agregar_leyenda(m, '<div style="background:rgba(20,25,23,.92);color:#e9efec;border-radius:10px;padding:8px 11px;font-size:12px;' + FONT +
                    'box-shadow:0 1px 8px rgba(0,0,0,.5)"><b>Intensidad</b><div style="width:150px;height:10px;margin-top:5px;border-radius:3px;background:linear-gradient(90deg,#2b4a6f,#7a9a5b,#e8b25a,#ee6c3c,#e11d1d)"></div>'
                    '<div style="display:flex;justify-content:space-between;width:150px"><span>baja</span><span>alta</span></div></div>')
    agregar_selector_dpto(m, bounds_dep)
    folium.LayerControl(collapsed=True, position="topright").add_to(m)
    m.fit_bounds(bbox(feats))
    return m
