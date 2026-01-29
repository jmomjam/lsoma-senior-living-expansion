#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
MAPA INTERACTIVO L-SOMA - CON POLÍGONOS DE SECCIONES CENSALES
================================================================================
4 capas con polígonos reales:
1. DBSCAN Original - IDs del informe (ranking_fase8)
2. Masa Crítica Prime - IDs del informe, filtrado Es_Viable
3. Frontera Rentabilidad - IDs nuevos (secciones_frontera_competencia)
4. Competencia - Mismos IDs de Frontera, coloreados por Tipo_Oceano
================================================================================
"""

import pandas as pd
import geopandas as gpd
import folium
from folium import plugins
import os

# ==============================================================================
# CONFIGURACIÓN
# ==============================================================================
DATA_DIR = "../datos"
SHAPEFILE = "../datos/seccionado_2024/SECC_CE_20240101.shp"

# Datos para Original/Prime (IDs del informe)
RANKING_FASE8 = "../datos/ranking_fase8_puntos_con_cluster.csv"

# Datos para Frontera/Competencia (IDs nuevos)
FRONTERA_COMPETENCIA = "../datos/secciones_frontera_competencia.csv"

OUTPUT_FILE = "../reports/mapa_interactivo_lsoma.html"

# Colores
COLORES_OCEANO = {
    "Blue Ocean": "#3498db",
    "Batalla": "#f39c12", 
    "Saturado": "#e74c3c"
}

COLORES_CLUSTER = [
    '#e6194b', '#3cb44b', '#ffe119', '#4363d8', '#f58231', 
    '#911eb4', '#46f0f0', '#f032e6', '#bcf60c', '#fabebe',
    '#008080', '#e6beff', '#9a6324', '#fffac8', '#800000',
    '#aaffc3', '#808000', '#ffd8b1', '#000075', '#808080'
]

# ==============================================================================
# FUNCIONES
# ==============================================================================

def cargar_y_preparar_shapefile():
    """Carga el shapefile y prepara la columna CUSEC"""
    print(">>> Cargando shapefile...")
    gdf = gpd.read_file(SHAPEFILE)
    
    if 'CUSEC' not in gdf.columns:
        gdf['CUSEC'] = (gdf['CPRO'].astype(str) + 
                        gdf['CMUN'].astype(str) + 
                        gdf['CDIS'].astype(str) + 
                        gdf['CSEC'].astype(str))
    gdf['CUSEC'] = gdf['CUSEC'].astype(str)
    print(f"    ✓ {len(gdf)} secciones en shapefile")
    return gdf

def simplificar_geometria(gdf, tolerance=0.001):
    """Simplifica geometrías para reducir peso del HTML"""
    print(">>> Simplificando geometrías...")
    gdf = gdf.to_crs(epsg=4326)
    gdf['geometry'] = gdf['geometry'].simplify(tolerance=tolerance, preserve_topology=True)
    print(f"    ✓ Geometrías simplificadas (tolerance={tolerance})")
    return gdf

def crear_capa_geojson(gdf, layer_name, style_func, tooltip_fields, tooltip_aliases, show=False):
    """Crea una capa GeoJSON para Folium"""
    layer = folium.FeatureGroup(name=layer_name, show=show)
    
    folium.GeoJson(
        gdf.__geo_interface__,
        style_function=style_func,
        tooltip=folium.GeoJsonTooltip(
            fields=tooltip_fields,
            aliases=tooltip_aliases,
            localize=True
        )
    ).add_to(layer)
    
    return layer

# ==============================================================================
# MAIN
# ==============================================================================

print("=" * 60)
print("   MAPA INTERACTIVO L-SOMA (POLÍGONOS)")
print("=" * 60)

# 1. Cargar shapefile
gdf_base = cargar_y_preparar_shapefile()

# 2. Cargar datos Original/Prime
print("\n>>> Cargando datos Original/Prime...")
df_original = pd.read_csv(RANKING_FASE8, sep=';')
df_original['CUSEC_LIMPIO'] = df_original['CUSEC_LIMPIO'].astype(str)
print(f"    ✓ {len(df_original)} secciones en ranking_fase8")

# 3. Cargar datos Frontera/Competencia
print(">>> Cargando datos Frontera/Competencia...")
if os.path.exists(FRONTERA_COMPETENCIA):
    df_frontera = pd.read_csv(FRONTERA_COMPETENCIA, sep=';')
    df_frontera['CUSEC'] = df_frontera['CUSEC'].astype(str)
    print(f"    ✓ {len(df_frontera)} secciones en frontera/competencia")
else:
    print(f"    ✗ No existe {FRONTERA_COMPETENCIA}. Ejecuta primero unificar_datos_mapa.py")
    df_frontera = None

# ==============================================================================
# MERGE CON SHAPEFILE
# ==============================================================================

print("\n>>> Preparando geometrías...")

# Merge para Original/Prime
gdf_original = gdf_base.merge(
    df_original[['CUSEC_LIMPIO', 'Cluster_ID', 'Renta_Hogar', 'Score_Global', 
                 'Capacidad_Teorica_Camas', 'Es_Viable', 'Seccion']],
    left_on='CUSEC', right_on='CUSEC_LIMPIO', how='inner'
)
gdf_original = simplificar_geometria(gdf_original)
print(f"    ✓ Original: {len(gdf_original)} polígonos")

# Merge para Frontera/Competencia
if df_frontera is not None:
    gdf_frontera = gdf_base.merge(
        df_frontera[['CUSEC', 'Cluster_ID', 'Renta_Hogar', 'Score_Global',
                     'Camas_Potenciales', 'Es_Viable', 'Tipo_Oceano', 'Indice_Saturacion']],
        on='CUSEC', how='inner'
    )
    gdf_frontera = simplificar_geometria(gdf_frontera)
    print(f"    ✓ Frontera: {len(gdf_frontera)} polígonos")

# ==============================================================================
# CREAR MAPA
# ==============================================================================

print("\n>>> Creando mapa...")
mapa = folium.Map(location=[40.4168, -3.7038], zoom_start=6, tiles=None)

# Capas base
folium.TileLayer('cartodbpositron', name='Mapa Claro').add_to(mapa)
folium.TileLayer('cartodbdark_matter', name='Mapa Oscuro').add_to(mapa)
folium.TileLayer('openstreetmap', name='OpenStreetMap').add_to(mapa)

# ==============================================================================
# CAPA 1: DBSCAN Original
# ==============================================================================

print(">>> Generando capa 1: DBSCAN Original...")

def style_original(feature):
    cid = feature['properties'].get('Cluster_ID', 0)
    return {
        'fillColor': COLORES_CLUSTER[int(cid) % len(COLORES_CLUSTER)],
        'color': '#333',
        'weight': 0.3,
        'fillOpacity': 0.6
    }

layer1 = crear_capa_geojson(
    gdf_original,
    "🔵 DBSCAN Original (IDs informe)",
    style_original,
    ['Seccion', 'Cluster_ID', 'Renta_Hogar'],
    ['Sección:', 'Cluster:', 'Renta:'],
    show=False
)
layer1.add_to(mapa)
print(f"    ✓ Añadida")

# ==============================================================================
# CAPA 2: Masa Crítica Prime
# ==============================================================================

print(">>> Generando capa 2: Masa Crítica Prime...")

gdf_prime = gdf_original[gdf_original['Es_Viable'] == True].copy()

def style_prime(feature):
    cid = feature['properties'].get('Cluster_ID', 0)
    return {
        'fillColor': COLORES_CLUSTER[int(cid) % len(COLORES_CLUSTER)],
        'color': '#27ae60',
        'weight': 1,
        'fillOpacity': 0.7
    }

layer2 = crear_capa_geojson(
    gdf_prime,
    "🟢 Masa Crítica Prime (viables)",
    style_prime,
    ['Seccion', 'Cluster_ID', 'Renta_Hogar', 'Capacidad_Teorica_Camas'],
    ['Sección:', 'Cluster:', 'Renta:', 'Camas:'],
    show=False
)
layer2.add_to(mapa)
print(f"    ✓ Añadida ({len(gdf_prime)} polígonos)")

# ==============================================================================
# CAPA 3: Frontera de Rentabilidad
# ==============================================================================

if df_frontera is not None:
    print(">>> Generando capa 3: Frontera de Rentabilidad...")
    
    gdf_frontera_viable = gdf_frontera[gdf_frontera['Es_Viable'] == True].copy()
    
    def style_frontera(feature):
        cid = feature['properties'].get('Cluster_ID', 0)
        return {
            'fillColor': '#e67e22',
            'color': COLORES_CLUSTER[int(cid) % len(COLORES_CLUSTER)],
            'weight': 1,
            'fillOpacity': 0.6
        }
    
    layer3 = crear_capa_geojson(
        gdf_frontera_viable,
        "🟠 Frontera Rentabilidad (expandido)",
        style_frontera,
        ['Cluster_ID', 'Renta_Hogar', 'Camas_Potenciales'],
        ['Cluster:', 'Renta:', 'Camas:'],
        show=True
    )
    layer3.add_to(mapa)
    print(f"    ✓ Añadida ({len(gdf_frontera_viable)} polígonos)")

# ==============================================================================
# CAPA 4: Competencia (Blue Ocean / Batalla / Saturado)
# ==============================================================================

if df_frontera is not None:
    print(">>> Generando capa 4: Competencia...")
    
    def style_competencia(feature):
        tipo = feature['properties'].get('Tipo_Oceano', 'Saturado')
        return {
            'fillColor': COLORES_OCEANO.get(tipo, '#888'),
            'color': '#333',
            'weight': 0.5,
            'fillOpacity': 0.7
        }
    
    layer4 = crear_capa_geojson(
        gdf_frontera,
        "🎯 Competencia (Blue/Batalla/Saturado)",
        style_competencia,
        ['Cluster_ID', 'Tipo_Oceano', 'Indice_Saturacion', 'Camas_Potenciales'],
        ['Cluster:', 'Tipo:', 'I_sat:', 'Camas:'],
        show=False
    )
    layer4.add_to(mapa)
    
    # Contar por tipo
    counts = gdf_frontera['Tipo_Oceano'].value_counts()
    print(f"    ✓ Blue Ocean: {counts.get('Blue Ocean', 0)} secciones")
    print(f"    ✓ Batalla: {counts.get('Batalla', 0)} secciones")
    print(f"    ✓ Saturado: {counts.get('Saturado', 0)} secciones")

# ==============================================================================
# CONTROLES Y LEYENDA
# ==============================================================================

print("\n>>> Añadiendo controles...")

folium.LayerControl(collapsed=False).add_to(mapa)
plugins.MiniMap(toggle_display=True, position='bottomleft').add_to(mapa)
plugins.Fullscreen().add_to(mapa)

legend_html = """
<div style="position: fixed; bottom: 50px; right: 50px; z-index: 1000; 
            background: white; padding: 12px 15px; border-radius: 8px; 
            box-shadow: 0 2px 10px rgba(0,0,0,0.2); font-family: Arial; font-size: 12px;">
    <b style="font-size: 13px;">Leyenda Competencia</b><br><br>
    <span style="background: #3498db; padding: 2px 8px; border-radius: 3px; color: white;">●</span> Blue Ocean<br>
    <span style="background: #f39c12; padding: 2px 8px; border-radius: 3px; color: white;">●</span> Batalla<br>
    <span style="background: #e74c3c; padding: 2px 8px; border-radius: 3px; color: white;">●</span> Saturado<br>
</div>
"""
mapa.get_root().html.add_child(folium.Element(legend_html))

# ==============================================================================
# GUARDAR
# ==============================================================================

print(f"\n>>> Guardando: {OUTPUT_FILE}")
mapa.save(OUTPUT_FILE)

file_size = os.path.getsize(OUTPUT_FILE) / (1024 * 1024)

print("\n" + "=" * 60)
print("✅ MAPA GENERADO EXITOSAMENTE")
print(f"📂 {OUTPUT_FILE}")
print(f"📦 Tamaño: {file_size:.1f} MB")
print("=" * 60)
