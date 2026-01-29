import pandas as pd
import geopandas as gpd
import folium
import matplotlib.pyplot as plt
import os

# --- CONFIGURACIÓN ---
ARCHIVO_PUNTOS_TAGGED = "../datos/ranking_fase8_puntos_con_cluster.csv"
ARCHIVO_SHP = "../datos/seccionado_2024/SECC_CE_20240101.shp" # Ruta ajustada a tu imagen
OUTPUT_HTML = "../mapa_TOTAL_clusters.html"
OUTPUT_PNG = "../mapa_TOTAL_estatico.png"

def generar_mapa_raw():
    print("--- SCRIPT 2: VISUALIZACIÓN DE TODO EL ESPECTRO ---")
    
    # 1. CARGAR DATOS
    if not os.path.exists(ARCHIVO_PUNTOS_TAGGED): return
    df_puntos = pd.read_csv(ARCHIVO_PUNTOS_TAGGED, sep=';')
    
    # 2. CARGAR SHAPEFILE
    print(">>> Cargando geometrías (Shapefile)...")
    try:
        gdf = gpd.read_file(ARCHIVO_SHP)
        # Normalizar CUSEC en shapefile (a veces viene separado)
        # El archivo de 2024 suele tener columna 'CUSEC' o 'NCODE'.
        if 'CUSEC' not in gdf.columns:
             # Construcción estándar INE si no existe la columna
             gdf['CUSEC'] = gdf['CPRO'] + gdf['CMUN'] + gdf['CDIS'] + gdf['CSEC']
        
        # Filtrar: Solo nos quedamos con los polígonos que están en nuestro estudio
        # Esto acelera todo brutalmente
        # Aseguramos que ambas columnas CUSEC sean del mismo tipo (string)
        gdf['CUSEC'] = gdf['CUSEC'].astype(str)
        df_puntos['CUSEC_LIMPIO'] = df_puntos['CUSEC_LIMPIO'].astype(str)
        
        gdf_study = gdf[gdf['CUSEC'].isin(df_puntos['CUSEC_LIMPIO'])].copy()
        
        # Unir datos al polígono
        gdf_merged = gdf_study.merge(df_puntos, left_on='CUSEC', right_on='CUSEC_LIMPIO')
        
    except Exception as e:
        print(f"❌ Error leyendo Shapefile: {e}")
        return

    # 3. GENERAR PNG ESTÁTICO (Para PowerPoint)
    print(">>> Generando PNG estático...")
    fig, ax = plt.subplots(figsize=(12, 10))
    # Pintamos España de fondo (opcional, aquí pintamos solo clusters)
    
    # Clusters VIABLES en AZUL, SUBCRITICOS en ROJO
    gdf_merged.plot(ax=ax, 
                    column='Es_Viable', 
                    cmap='coolwarm_r', # Rojo=False, Azul=True
                    legend=True,
                    legend_kwds={'title': "Azul: Viable | Rojo: Sub-crítico"})
    
    plt.title("Distribución de Masa Crítica en España")
    plt.savefig(OUTPUT_PNG, dpi=150)
    print(f"✅ PNG guardado: {OUTPUT_PNG}")

    # 4. GENERAR HTML INTERACTIVO
    print(">>> Generando HTML interactivo...")
    # Convertir a WGS84 para web
    gdf_web = gdf_merged.to_crs(epsg=4326)
    
    m = folium.Map(location=[40.4, -3.7], zoom_start=6, tiles='CartoDB positron')
    
    # Función de estilo condicional
    def style_function(feature):
        es_viable = feature['properties']['Es_Viable']
        return {
            'fillColor': '#2ecc71' if es_viable else '#e74c3c', # Verde o Rojo
            'color': 'black',
            'weight': 0.5,
            'fillOpacity': 0.6
        }

    folium.GeoJson(
        gdf_web,
        name="Clusters",
        style_function=style_function,
        tooltip=folium.GeoJsonTooltip(fields=['Seccion', 'Capacidad_Teorica_Camas', 'Es_Viable'])
    ).add_to(m)
    
    m.save(OUTPUT_HTML)
    print(f"✅ HTML guardado: {OUTPUT_HTML}")

if __name__ == "__main__":
    generar_mapa_raw()
