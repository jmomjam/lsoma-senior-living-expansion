import pandas as pd
import folium
import matplotlib.pyplot as plt
import seaborn as sns
import os
import branca.colormap as cm

# --- CONFIGURACIÓN ---
ARCHIVO_GEO_READY = "../datos/ranking_fase6_geo_ready.csv"
ARCHIVO_CLUSTERS = "../datos/ranking_fase7_clusters.csv"
OUTPUT_HTML = "../mapa_clusters_interactivo.html"
OUTPUT_PNG = "../mapa_estatico_top10.png"

def visualizar_resultados():
    print("--- FASE 7: VISUALIZACIÓN DE INTELIGENCIA TERRITORIAL ---")
    
    # 1. CARGAR DATOS
    if not os.path.exists(ARCHIVO_GEO_READY) or not os.path.exists(ARCHIVO_CLUSTERS):
        print("❌ Faltan archivos previos.")
        return

    # Cargamos el detalle (puntos) - para pintar las mejores secciones
    df_puntos = pd.read_csv(ARCHIVO_GEO_READY, sep=';')
    
    # Cargamos el resumen (clusters) - tiene los centroides
    df_resumen = pd.read_csv(ARCHIVO_CLUSTERS, sep=';')
    
    # Filtramos: Solo pintamos los Top N clusters y las mejores secciones por Score
    top_n_clusters = 20
    
    # Filtramos df_puntos para pintar solo las secciones con mejor Score (Top 10%)
    umbral_score = df_puntos['Score_Global'].quantile(0.90)
    df_pintar = df_puntos[df_puntos['Score_Global'] >= umbral_score].copy()
    # Eliminar filas sin coordenadas válidas
    df_pintar = df_pintar.dropna(subset=['LATITUD', 'LONGITUD'])
    
    print(f">>> Generando mapa para los Top {top_n_clusters} Clusters y {len(df_pintar)} secciones top...")

    # 2. MAPA INTERACTIVO (FOLIUM)
    # Centramos el mapa en España
    mapa = folium.Map(location=[40.4168, -3.7038], zoom_start=6, tiles='CartoDB positron')

    # Paleta de colores para diferenciar clusters
    colores = ['red', 'blue', 'green', 'purple', 'orange', 'darkred', 
               'lightred', 'beige', 'darkblue', 'darkgreen', 'cadetblue', 
               'darkpurple', 'white', 'pink', 'lightblue', 'lightgreen', 
               'gray', 'black', 'lightgray']

    # A. PINTAR LAS "MANCHAS" (SECCIONES INDIVIDUALES) - coloreadas por Score
    for idx, (_, row) in enumerate(df_pintar.iterrows()):
        # Asignar color basado en el índice secuencial
        color = colores[idx % len(colores)]
        
        # Tooltip con información clave
        texto = f"""
        <b>Sección:</b> {row['Seccion']}<br>
        <b>Renta:</b> {row['Renta_Hogar']:,.0f}€<br>
        <b>Presión Cuidados:</b> {row['Presion_Cuidados']:.2f}<br>
        <b>Score:</b> {row['Score_Global']:.3f}
        """
        
        folium.CircleMarker(
            location=[row['LATITUD'], row['LONGITUD']],
            radius=4,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.6,
            popup=folium.Popup(texto, max_width=300)
        ).add_to(mapa)

    # B. PINTAR LOS "CENTROIDES" (MARCADORES GRANDES)
    # Iteramos sobre el resumen de los top clusters
    for _, cluster in df_resumen.head(top_n_clusters).iterrows():
        cid = int(cluster['Cluster_ID'])
        color = colores[cid % len(colores)]
        
        # Calcular capacidad teórica (Regla del 3%)
        # Asumimos 90 targets/sección
        capacidad_teorica = cluster['Num_Secciones'] * 90 * 0.03
        num_residencias = int(capacidad_teorica / 100)
        if num_residencias < 1: num_residencias = 1
        
        texto_cluster = f"""
        <h4>CLUSTER {cid}</h4>
        <b>Zona:</b> {str(cluster['Toponimos'])[:50]}...<br>
        <b>Secciones:</b> {cluster['Num_Secciones']}<br>
        <b>Potencia Total:</b> {cluster['Potencia_Total']:.1f}<br>
        <b>Capacidad Estimada:</b> ~{num_residencias} Residencias (Target 3%)
        """
        
        folium.Marker(
            location=[cluster['Lat_Centro'], cluster['Lon_Centro']],
            icon=folium.Icon(color=color, icon='star', prefix='fa'),
            tooltip=f"Cluster {cid} (Potencia: {cluster['Potencia_Total']:.0f})"
        ).add_to(mapa).add_child(folium.Popup(texto_cluster, max_width=300))

    # Guardar HTML
    mapa.save(OUTPUT_HTML)
    print(f"✅ MAPA INTERACTIVO GENERADO: {OUTPUT_HTML}")
    print("   (Ábrelo en tu navegador web)")

    # 3. MAPA ESTÁTICO (MATPLOTLIB) - PARA EL POWERPOINT
    print(">>> Generando gráfico estático...")
    plt.figure(figsize=(10, 8))
    
    # Scatter plot de lat/lon
    # Coloreamos por Score_Global (mapa de calor)
    sns.scatterplot(
        data=df_pintar, 
        x='LONGITUD', 
        y='LATITUD', 
        hue='Score_Global', 
        palette='YlOrRd', 
        s=10, 
        legend=False
    )
    
    plt.title(f'Top {top_n_clusters} Clusters de Demanda (L-SOMA)', fontsize=14)
    plt.xlabel('Longitud')
    plt.ylabel('Latitud')
    plt.grid(True, linestyle='--', alpha=0.5)
    
    # Anotar los centros
    for _, cluster in df_resumen.head(10).iterrows():
        plt.text(
            cluster['Lon_Centro'], 
            cluster['Lat_Centro'], 
            str(int(cluster['Cluster_ID'])), 
            fontsize=12, 
            weight='bold',
            color='black',
            bbox=dict(facecolor='white', alpha=0.7, edgecolor='none')
        )

    plt.savefig(OUTPUT_PNG, dpi=300)
    print(f"✅ MAPA ESTÁTICO GENERADO: {OUTPUT_PNG}")

if __name__ == "__main__":
    visualizar_resultados()
