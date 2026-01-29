import pandas as pd
import geopandas as gpd
import folium
import matplotlib.pyplot as plt
import os

# --- CONFIGURACIÓN ---
ARCHIVO_PUNTOS_TAGGED = "../datos/ranking_fase8_puntos_con_cluster.csv"
ARCHIVO_SHP = "../datos/seccionado_2024/SECC_CE_20240101.shp"
OUTPUT_HTML = "../mapa_VIABLES_premium.html"
OUTPUT_PNG = "../mapa_VIABLES_estatico.png"

def generar_mapa_premium():
    print("--- SCRIPT 3: EL MAPA DEL TESORO (SOLO VIABLES) ---")
    
    if not os.path.exists(ARCHIVO_PUNTOS_TAGGED): return
    df_puntos = pd.read_csv(ARCHIVO_PUNTOS_TAGGED, sep=';')
    
    # FILTRO: SOLO VIABLES
    df_puntos = df_puntos[df_puntos['Es_Viable'] == True].copy()
    print(f">>> Pintando solo las {len(df_puntos)} secciones de alta rentabilidad.")

    # Carga Shapefile (Misma lógica)
    try:
        gdf = gpd.read_file(ARCHIVO_SHP)
        if 'CUSEC' not in gdf.columns:
             gdf['CUSEC'] = gdf['CPRO'] + gdf['CMUN'] + gdf['CDIS'] + gdf['CSEC']
        
        # Aseguramos que ambas columnas CUSEC sean del mismo tipo (string)
        gdf['CUSEC'] = gdf['CUSEC'].astype(str)
        df_puntos['CUSEC_LIMPIO'] = df_puntos['CUSEC_LIMPIO'].astype(str)
        
        gdf_merged = gdf.merge(df_puntos, left_on='CUSEC', right_on='CUSEC_LIMPIO')
        
    except Exception as e:
        print(f"❌ Error Shapefile: {e}")
        return

    # PNG ESTÁTICO (Distinto color por Cluster ID para distinguir vecinos)
    print(">>> Generando PNG...")
    fig, ax = plt.subplots(figsize=(15, 12))
    gdf_merged.plot(ax=ax, column='Cluster_ID', cmap='tab20', legend=False)
    plt.title("Yacimientos de Demanda Certificada (>85 plazas)")
    plt.axis('off')
    plt.savefig(OUTPUT_PNG, dpi=300, bbox_inches='tight')
    print(f"✅ PNG Premium guardado: {OUTPUT_PNG}")

    # HTML INTERACTIVO
    print(">>> Generando HTML...")
    gdf_web = gdf_merged.to_crs(epsg=4326)
    m = folium.Map(location=[40.4, -3.7], zoom_start=6, tiles='CartoDB positron')
    
    # Colorear por Cluster ID (Paleta cíclica)
    colors = ['#e6194b', '#3cb44b', '#ffe119', '#4363d8', '#f58231', '#911eb4', '#46f0f0', '#f032e6']
    
    def style_function(feature):
        cid = feature['properties']['Cluster_ID']
        return {
            'fillColor': colors[cid % len(colors)],
            'color': 'black',
            'weight': 0.5,
            'fillOpacity': 0.7
        }

    folium.GeoJson(
        gdf_web,
        style_function=style_function,
        tooltip=folium.GeoJsonTooltip(
            fields=['Seccion', 'Renta_Hogar', 'Capacidad_Teorica_Camas'],
            aliases=['Ubicación:', 'Renta (€):', 'Capacidad (Camas):']
        )
    ).add_to(m)
    
    m.save(OUTPUT_HTML)
    print(f"✅ HTML Premium guardado: {OUTPUT_HTML}")

if __name__ == "__main__":
    generar_mapa_premium()
