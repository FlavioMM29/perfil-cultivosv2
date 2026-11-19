import json, pandas as pd
ALIAS = {'UNITED STATES':'UNITED STATES OF AMERICA','RUSSIAN FEDERATION':'RUSSIA','VIET NAM':'VIETNAM',
 'IRAN (ISLAMIC REPUBLIC OF)':'IRAN','KOREA, REPUBLIC OF':'SOUTH KOREA',"KOREA, DEMOCRATIC PEOPLE'S REP. OF":'NORTH KOREA',
 'TAIWAN, PROVINCE OF CHINA':'TAIWAN','LIBYAN ARAB JAMAHIRIYA':'LIBYA','MACEDONIA F.Y.R.':'MACEDONIA','SERVIA':'REPUBLIC OF SERBIA',
 'KYRGYSTAN':'KYRGYZSTAN',"COTE D'IVOIRE":'IVORY COAST','TANZANIA':'UNITED REPUBLIC OF TANZANIA'}
# territorios sin polígono en el geojson -> coordenadas manuales (lat, lon)
MANUAL = {'HONG KONG':(22.3,114.2),'SINGAPORE':(1.35,103.8),'BAHRAIN':(26.0,50.55),'MALDIVES':(3.2,73.2),
 'MAURITIUS':(-20.3,57.6),'ARUBA':(12.5,-69.97),'CURACAO':(12.17,-69.0),'BARBADOS':(13.19,-59.54),'BAHAMAS':(25.0,-77.4),
 'CAPE VERDE':(16.0,-24.0),'MACAU':(22.2,113.55),'REUNION':(-21.1,55.5),'MARTINIQUE':(14.64,-61.0),'GUADELOUPE':(16.25,-61.55),
 'FRENCH POLYNESIA':(-17.7,-149.4),'KIRIBATI':(1.9,-157.4),'DOMINICA':(15.4,-61.37),'PHILIPSBURG':(18.03,-63.05),
 'SAO TOME AND PRINCIPE':(0.2,6.6),'TOKELAU':(-9.2,-171.8)}
w = json.load(open('geo/world.geojson'))
xy = {}
for f in w['features']:
    n = f['properties']['name'].upper(); f['properties'] = {'key': n, 'name': f['properties']['name']}
    g = f['geometry']; polys = g['coordinates'] if g['type']=='MultiPolygon' else [g['coordinates']]
    big = max(polys, key=lambda p: len(p[0]))
    xs=[c[0] for c in big[0]]; ys=[c[1] for c in big[0]]
    xy[n] = ((min(ys)+max(ys))/2, (min(xs)+max(xs))/2)
json.dump(w, open('geo/world.geojson','w'))
cx = pd.read_parquet('data/comercio.parquet'); out = {}
for p in sorted(set(cx.PAIS)):
    k = ALIAS.get(p, p)
    if k in xy: out[p] = {'key': k, 'lat': xy[k][0], 'lon': xy[k][1]}
    elif p in MANUAL: out[p] = {'key': None, 'lat': MANUAL[p][0], 'lon': MANUAL[p][1]}
json.dump(out, open('geo/paises_xy.json','w'))
print(len(out), 'sin ubicar:', sorted(set(cx.PAIS)-set(out)))
