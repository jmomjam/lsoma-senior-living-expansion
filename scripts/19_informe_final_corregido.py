import pandas as pd
import numpy as np
import geopandas as gpd
from sklearn.cluster import DBSCAN
import os

# --- CONFIGURACIÓN ---
ARCHIVO_INPUT_GEO = "../datos/ranking_fase6_geo_ready.csv"
ARCHIVO_MATRIZ_P = "../datos/matriz_P_nacional_filtrada.parquet"
ARCHIVO_SHAPEFILE = "../datos/seccionado_2024/SECC_CE_20240101.shp" # Opcional para recuperar geo
OUTPUT_EXCEL = "../datos/INFORME_FINAL_MASTER.xlsx"

# PARÁMETROS DE NEGOCIO
COLS_TARGET = ['M_80-84', 'M_85-89', 'M_90-94', 'M_95-99', 'M_100 y más']
MARKET_SHARES = [0.015, 0.02, 0.03, 0.05] # 1.5% (Conservador) a 5% (Agresivo)
CAMAS_BREAK_EVEN = 85
RADIO_CLUSTER = 1.5      # km
MIN_SECCIONES = 3

def generar_informe_maestro():
    print("==========================================================")
    print("   GENERADOR DE INFORME MAESTRO (CORREGIDO Y AUDITADO)    ")
    print("==========================================================\n")

    # 1. CARGAR DATOS
    print(">>> 1. Cargando Matriz P y Ranking Geo...")
    if not os.path.exists(ARCHIVO_INPUT_GEO) or not os.path.exists(ARCHIVO_MATRIZ_P):
        print("❌ Faltan archivos base.")
        return

    df_geo = pd.read_csv(ARCHIVO_INPUT_GEO, sep=';')
    df_matriz = pd.read_parquet(ARCHIVO_MATRIZ_P)
    
    # 2. CORRECCIÓN CRÍTICA 1: CÁLCULO REAL DE TARGETS
    # En lugar de usar constante 110, calculamos la realidad biológica de cada sección
    print(">>> 2. Calculando Población Target Real (Mujeres 80+) desde Matriz P...")
    
    # Asegurar cruce por índice o columna común
    # El df_geo tiene 'CUSEC' (o similar) y df_matriz tiene índice 'Seccion'
    # Vamos a usar 'Seccion' como clave
    
    # Calculamos el % de target en la matriz
    df_matriz['Pct_Target'] = df_matriz[COLS_TARGET].sum(axis=1)
    
    # Cruzamos ese % con el df_geo que tiene la Poblacion_Total
    # Primero limpiamos nombres para asegurar match
    df_merged = pd.merge(df_geo, df_matriz[['Pct_Target']], left_on='Seccion', right_index=True, how='left')
    
    # Población Target Absoluta = Poblacion Total * % Target
    df_merged['Poblacion_Target_Real'] = df_merged['Poblacion_Total'] * df_merged['Pct_Target']
    
    # Rellenar nulos con 0 (si alguna sección no cruzó)
    df_merged['Poblacion_Target_Real'] = df_merged['Poblacion_Target_Real'].fillna(0)
    
    media_real = df_merged['Poblacion_Target_Real'].mean()
    print(f"   [AUDITORÍA] Target Promedio Real detectado: {media_real:.1f} mujeres/sección")
    print(f"   (La constante anterior de 110 era {'OPTIMISTA' if 110 > media_real else 'PESIMISTA'})")

    # 3. CORRECCIÓN GEO: RECUPERACIÓN DE COORDENADAS (Opcional)
    print(">>> 3. Verificando integridad geoespacial...")
    sin_coords = df_merged[df_merged['LATITUD'].isna()]
    n_sin = len(sin_coords)
    
    if n_sin > 0 and os.path.exists(ARCHIVO_SHAPEFILE):
        print(f"   ⚠️ Detectadas {n_sin} secciones sin coordenadas. Intentando recuperar con Shapefile...")
        try:
            gdf = gpd.read_file(ARCHIVO_SHAPEFILE)
            # Normalizar CUSEC
            if 'CUSEC' not in gdf.columns: gdf['CUSEC'] = gdf['CPRO'] + gdf['CMUN'] + gdf['CDIS'] + gdf['CSEC']
            
            # Calcular centroides
            gdf['cent_lat'] = gdf.to_crs(epsg=4326).geometry.centroid.y
            gdf['cent_lon'] = gdf.to_crs(epsg=4326).geometry.centroid.x
            
            # Cruzar para rellenar
            # Asumimos que df_merged tiene columna 'CUSEC' limpia (del paso 13)
            # Si no, la creamos rápido
            df_merged['CUSEC_JOIN'] = df_merged['Seccion'].astype(str).str.split(' ').str[0].str.strip()
            
            # Merge update
            merged_recup = df_merged.merge(gdf[['CUSEC', 'cent_lat', 'cent_lon']], 
                                         left_on='CUSEC_JOIN', right_on='CUSEC', how='left')
            
            # Rellenar NaNs
            df_merged['LATITUD'] = df_merged['LATITUD'].fillna(merged_recup['cent_lat'])
            df_merged['LONGITUD'] = df_merged['LONGITUD'].fillna(merged_recup['cent_lon'])
            
            nuevos_nans = df_merged['LATITUD'].isna().sum()
            print(f"   ✅ Recuperadas {n_sin - nuevos_nans} coordenadas. Faltan: {nuevos_nans}")
            
        except Exception as e:
            print(f"   ❌ Falló la recuperación geo: {e}")
    
    # Limpieza final de geo
    df_clean = df_merged.dropna(subset=['LATITUD', 'LONGITUD']).copy()

    # 4. CLUSTERING FINAL
    print(">>> 4. Ejecutando Clustering Final (DBSCAN)...")
    # Filtro Calidad (Top 15%)
    umbral_score = df_clean['Score_Global'].quantile(0.85)
    df_premium = df_clean[df_clean['Score_Global'] > umbral_score].copy()
    
    coords = np.radians(df_premium[['LATITUD', 'LONGITUD']].values)
    db = DBSCAN(eps=RADIO_CLUSTER/6371., min_samples=MIN_SECCIONES, metric='haversine').fit(coords)
    df_premium['Cluster_ID'] = db.labels_
    df_clusters = df_premium[df_premium['Cluster_ID'] != -1].copy()

    # 5. GENERACIÓN DE ESCENARIOS (SENSIBILIDAD)
    print(">>> 5. Calculando Escenarios de Viabilidad...")
    
    # Agregamos por Cluster
    agg = df_clusters.groupby('Cluster_ID').agg({
        'Seccion': 'count',
        'Poblacion_Target_Real': 'sum', # Suma real de abuelas en el cluster
        'Renta_Hogar': 'mean',
        'Score_Global': 'mean'
    })
    
    escenarios = []
    
    for share in MARKET_SHARES:
        col_name = f'Camas_Share_{share*100:.1f}%'
        agg[col_name] = agg['Poblacion_Target_Real'] * share
        
        # Filtro de Viabilidad
        viables = agg[agg[col_name] >= CAMAS_BREAK_EVEN]
        
        total_camas = viables[col_name].sum()
        num_residencias = int(total_camas / 100)
        
        escenarios.append({
            'Escenario': f"Share {share*100:.1f}%",
            'Clusters_Viables': len(viables),
            'Residencias_Potenciales': num_residencias,
            'Gap_Objetivo_1000': 1000 - num_residencias
        })

    df_escenarios = pd.DataFrame(escenarios)

    # 6. EXPORTACIÓN
    print(f"\n[RESULTADOS FINALES AUDITADOS]")
    print(df_escenarios.to_string(index=False))
    
    with pd.ExcelWriter(OUTPUT_EXCEL) as writer:
        df_escenarios.to_excel(writer, sheet_name='Resumen_Ejecutivo')
        agg.to_excel(writer, sheet_name='Detalle_Clusters')
        df_premium.to_excel(writer, sheet_name='Data_Raw')
        
    print(f"\n✅ INFORME MAESTRO GUARDADO: {OUTPUT_EXCEL}")

if __name__ == "__main__":
    generar_informe_maestro()
