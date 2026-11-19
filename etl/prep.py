"""Preprocesa los Excel originales -> parquet compactos para la app."""
import sys, glob, re, json, shutil, pandas as pd, numpy as np
sys.path.insert(0, '.')
from common import familia, norm, PERMANENTES

RAW = '/home/claude/work/raw/'
OUT = 'data/'
MESES = {'ENERO':1,'FEBRERO':2,'MARZO':3,'ABRIL':4,'MAYO':5,'JUNIO':6,'JULIO':7,'AGOSTO':8,'SEPTIEMBRE':9,'OCTUBRE':10,'NOVIEMBRE':11,'DICIEMBRE':12}

# ---------- SISAGRI (distrital) ----------
df = pd.concat([pd.read_parquet(f) for f in sorted(glob.glob(RAW + 's?.parquet'))], ignore_index=True)
df['ANIO'] = df.ANIO.astype('int16'); df['MES'] = df.MES.astype('int8')
prod_map = {p: familia(p) for p in df.PRODUCTO.unique()}
df['CULTIVO'] = df.PRODUCTO.map(prod_map)
df['PXP'] = df.PRECIO_CHACRA * df.PRODUCCION          # t * S/kg = miles de S/
df['PRODP'] = np.where(df.PRECIO_CHACRA > 0, df.PRODUCCION, 0)
ub = (df[['UBIGEO','DEPARTAMENTO','PROVINCIA','DISTRITO']].drop_duplicates('UBIGEO'))
ub.to_parquet(OUT + 'ubigeo.parquet')
agg = (df.groupby(['CULTIVO','ANIO','MES','UBIGEO'], observed=True, sort=False)
         [['SIEMBRA','COSECHA','PRODUCCION','VERDE_ACTUAL','PXP','PRODP']].sum().reset_index())
agg['UBIGEO'] = agg.UBIGEO.astype('category')
slug = lambda s: re.sub(r'[^A-Z0-9]+','_',norm(s).replace('Ñ','N')).strip('_')
cat = []
for c, g in agg.groupby('CULTIVO'):
    g.drop(columns='CULTIVO').astype({'UBIGEO':'str'}).to_parquet(OUT + f'agri/{slug(c)}.parquet', index=False)
    cat.append(dict(cultivo=c, slug=slug(c), nivel='distrito', filas=len(g)))
print('cultivos SISAGRI', len(cat))

# ---------- Otros cultivos (departamental) ----------
oc = pd.read_parquet(RAW + 'otros.parquet')
oc['DEPARTAMENTO'] = oc.Dpto.map(norm).replace({'LIMA METROPOLITANA':'LIMA'})
oc['CULTIVO'] = oc.CULTIVO.map(familia); oc['ANIO'] = oc['Año'].astype('int16'); oc['MES'] = oc.MES.astype(int).astype('int8')
vm = {'PRODUCCION (t)':'PRODUCCION','COSECHA (ha)':'COSECHA','PRODXPRECIO_':'PXP','SIEMBRA (ha)':'SIEMBRA'}
w = (oc[oc.Valores.isin(vm)].assign(V=lambda d: d.Valores.map(vm))
       .pivot_table(index=['CULTIVO','DEPARTAMENTO','ANIO','MES'], columns='V', values='Total', aggfunc='sum').reset_index())
w['VERDE_ACTUAL'] = 0.0; w['PRODP'] = np.where(w.PXP > 0, w.PRODUCCION, 0)
for c, g in w.groupby('CULTIVO'):
    g.drop(columns='CULTIVO').to_parquet(OUT + f'agri/{slug(c)}.parquet', index=False)
    cat.append(dict(cultivo=c, slug=slug(c), nivel='departamento', filas=len(g)))
cat = pd.DataFrame(cat).sort_values('nivel', ascending=False).drop_duplicates('cultivo', keep='first')   # 'otros cultivos' prevalece sobre registros sueltos de SISAGRI
cat['permanente'] = cat.cultivo.isin(PERMANENTES)

# ---------- VBP ----------
v = pd.read_parquet(RAW + 'vbp.parquet')
v['ANIO'] = v.ANIO.astype('int16'); v['MESN'] = v.MES.map(MESES).astype('int8')
v['CULTIVO'] = v.PRODUCTO.map(familia)
v = v.rename(columns={'MES':'MES_TXT'}).drop(columns=['COD_DEPARTAMENTO'])
v['DEPARTAMENTO'] = v.DEPARTAMENTO.map(norm)
v = v.groupby(['TIPO','CULTIVO','DEPARTAMENTO','ANIO','MESN'], as_index=False)[['PRODUCCION','VBP']].sum()
v.to_parquet(OUT + 'vbp.parquet', index=False)
vb_set = set(v.CULTIVO)

# ---------- SISAP (precio mayorista, anual) ----------
s = pd.read_parquet(RAW + 'sisap.parquet')
s['CULTIVO'] = s.TXT_DSCGENERO.map(familia)
s = s.rename(columns={'COD_ANIO':'ANIO','TXT_DSCVARIEDAD':'VARIEDAD'})[['CULTIVO','VARIEDAD','ANIO','PRECIO_KG']]
s.to_parquet(OUT + 'sisap.parquet', index=False)

# ---------- SISCOMEX ----------
from common import HS
c = pd.read_parquet(RAW + 'siscomex.parquet')
c['COD'] = c.COD_ARANCEL.astype(str).str.zfill(10)
rows = []
for cult, prefs in HS.items():
    m = np.zeros(len(c), bool)
    for p in prefs: m |= c.COD.str.startswith(p).values
    if m.any(): rows.append(c[m].assign(CULTIVO=cult))
cx = pd.concat(rows, ignore_index=True)
cx = cx.rename(columns={'COD_ANIO':'ANIO','COD_MES':'MES','TEX_PAIS_DESTINO':'PAIS','CAN_PNETO':'PESO_T','VALOR_FOB':'FOB','VALOR_CIF':'CIF'})
cx = cx.groupby(['TIPO','CULTIVO','PAIS','ANIO','MES'], as_index=False)[['PESO_T','FOB','CIF']].sum()
cx['ANIO'] = cx.ANIO.astype('int16'); cx['MES'] = cx.MES.astype('int8')
cx.to_parquet(OUT + 'comercio.parquet', index=False)

cat['tiene_comercio'] = cat.cultivo.isin(set(cx.CULTIVO))
cat['tiene_vbp'] = cat.cultivo.isin(vb_set)
cat['tiene_precio_mayorista'] = cat.cultivo.isin(set(s.CULTIVO))
# orden por VBP (último año completo 2025)
rank = v[(v.TIPO=='AGRÍCOLA') & (v.ANIO==2025)].groupby('CULTIVO').VBP.sum()
cat['vbp_2025'] = cat.cultivo.map(rank).fillna(0)
cat = cat.sort_values(['vbp_2025','filas'], ascending=False)
cat.to_parquet(OUT + 'catalogo.parquet', index=False)
print(cat.head(40).to_string())
print('con VBP', cat.tiene_vbp.sum(), 'con comercio', cat.tiene_comercio.sum(), 'con SISAP', cat.tiene_precio_mayorista.sum())
