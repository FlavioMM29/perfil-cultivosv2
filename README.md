# Perfil productivo y competitivo de cultivos · Perú
App en **Streamlit + Folium + Plotly** basada en SISAGRI, SISAP, SISCOMEX y DATA_VBP.

## Ejecutar
```bash
pip install -r requirements.txt
streamlit run app.py
```
(Requiere internet solo para las capas base del mapa y la tipografía.)

## Mapas incluidos (pestaña «Perfil productivo»)
Coroplético (producción, valor, rendimiento, precio, variación, cosecha; etiquetas y círculos opcionales) ·
Cultivo principal por distrito · Burbujas por cultivo · Clusters de registros · Mapa de calor.
Todos con tarjeta de título, buscador, selector de departamento, coordenadas y capas base
(limpio, satélite, relieve, topográfico). Se evitó CARTO porque ahora exige API key.

## Novedades
- **Varios años a la vez**: el filtro «Años» acepta uno o varios; indicadores, mapas, rankings, comercio exterior y VBP acumulan los años elegidos y se comparan con el bloque anterior de igual duración.
- **Si no ves los mapas**: activa «Modo compatible de mapas» en la barra lateral (los dibuja como HTML puro). Si pasa, actualiza con `pip install -U streamlit streamlit-folium folium`.

## Estructura
- `app.py` – aplicación.  `mapas.py` – constructores de mapas Folium.  `common.py` – normalización de cultivos y mapeo cultivo→partida arancelaria.
- `data/` – parquet ya procesados (223 cultivos, distrital). `geo/` – geojson de departamentos, provincias, distritos y países.
- `etl/` – scripts que convirtieron los Excel (SISAGRI pesa ~3 GB de XML) a parquet. Ajusta las rutas si quieres regenerar.
