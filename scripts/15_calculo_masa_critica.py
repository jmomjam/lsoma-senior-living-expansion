import pandas as pd
import numpy as np
from sklearn.cluster import DBSCAN
import os

# --- CONFIGURACIÓN ---
ARCHIVO_PUNTOS_RAW = "../datos/ranking_fase6_geo_ready.csv"
ARCHIVO_MATRIZ_P = "../datos/matriz_P_nacional_filtrada.parquet"  # Para cálculo real de targets
OUTPUT_CLUSTERS = "../datos/ranking_fase8_clusters_analizados.csv"
OUTPUT_PUNTOS_TAGGED = "../datos/ranking_fase8_puntos_con_cluster.csv"

# CONSTANTES FÍSICAS DEL NEGOCIO
COLS_TARGET = ['M_80-84', 'M_85-89', 'M_90-94', 'M_95-99', 'M_100 y más']  # Columnas de mujeres 80+
MARKET_SHARE = 0.03         # Cuota de captura (3%)
UMBRAL_CAMAS = 85           # Break-even operativo

def calcular_masa_critica():
    print("--- SCRIPT 15: CÁLCULO DE MASA CRÍTICA Y VIABILIDAD (CORREGIDO) ---")
    
    # 1. CARGAR DATOS CRUDOS
    df = pd.read_csv(ARCHIVO_PUNTOS_RAW, sep=';')
    
    # 1.1 CORRECCIÓN CRÍTICA: Cargar Matriz P para cálculo real de targets
    print("   Cargando Matriz P para cálculo real de targets...")
    import os
    if os.path.exists(ARCHIVO_MATRIZ_P):
        df_matriz = pd.read_parquet(ARCHIVO_MATRIZ_P)
        # Calcular % de target (mujeres 80+) por sección
        df_matriz['Pct_Target'] = df_matriz[COLS_TARGET].sum(axis=1)
        # Mergear con df principal
        df = pd.merge(df, df_matriz[['Pct_Target']], left_on='Seccion', right_index=True, how='left')
        df['Pct_Target'] = df['Pct_Target'].fillna(0)
        # Población Target Real = Población Total * % Target
        df['Poblacion_Target_Real'] = df['Poblacion_Total'] * df['Pct_Target']
        print(f"   ✔ Target promedio real calculado: {df['Poblacion_Target_Real'].mean():.1f} mujeres/sección")
    else:
        # Fallback: usar estimación del 6% de la población
        print("   ⚠️ Matriz P no encontrada, usando estimación (6% población)")
        df['Poblacion_Target_Real'] = df['Poblacion_Total'] * 0.06
    
    # Filtro de Calidad previo al Clustering (Top 15% Score)
    umbral_score = df['Score_Global'].quantile(0.85)
    df_ml = df[df['Score_Global'] > umbral_score].copy()
    print(f"   Puntos analizados (Top 15%): {len(df_ml)}")

    # 2. GENERAR CLUSTERS (DBSCAN)
    # Re-calculamos aquí para asegurar que tenemos el ID en cada punto
    # Primero eliminamos filas con coordenadas faltantes (NaN)
    filas_antes = len(df_ml)
    df_ml = df_ml.dropna(subset=['LATITUD', 'LONGITUD'])
    filas_despues = len(df_ml)
    if filas_antes != filas_despues:
        print(f"   ⚠️ Eliminadas {filas_antes - filas_despues} filas sin coordenadas válidas")
    
    if len(df_ml) == 0:
        print("❌ No quedan puntos con coordenadas válidas.")
        return
    
    coords = np.radians(df_ml[['LATITUD', 'LONGITUD']].values)
    # Radio 1.5km
    db = DBSCAN(eps=1.5/6371., min_samples=3, metric='haversine', algorithm='ball_tree').fit(coords)
    
    df_ml['Cluster_ID'] = db.labels_
    
    # Descartamos el ruido (-1)
    df_ml = df_ml[df_ml['Cluster_ID'] != -1].copy()

    # 3. ANÁLISIS DE MASA CRÍTICA POR CLUSTER
    # Agrupamos para ver las propiedades macroscópicas
    stats = df_ml.groupby('Cluster_ID').agg({
        'Seccion': 'count',                 # Número de secciones (Volumen)
        'Score_Global': 'mean',             # Calidad media
        'Renta_Hogar': 'mean',
        'Presion_Cuidados': 'mean',
        'LATITUD': 'mean',
        'LONGITUD': 'mean',
        'Poblacion_Target_Real': 'sum'      # SUMA REAL de mujeres 80+ en el cluster
    }).rename(columns={'Seccion': 'Num_Secciones'})
    
    # FÓRMULA DE VIABILIDAD (CORREGIDA)
    # Capacidad = Suma_Target_Real * Share (ya no usa constante fija)
    stats['Capacidad_Teorica_Camas'] = stats['Poblacion_Target_Real'] * MARKET_SHARE
    
    # ETIQUETADO BINARIO
    stats['Es_Viable'] = stats['Capacidad_Teorica_Camas'] >= UMBRAL_CAMAS
    
    # Estadísticas Globales
    viables = stats[stats['Es_Viable']]
    subcriticos = stats[~stats['Es_Viable']]
    
    camas_totales = viables['Capacidad_Teorica_Camas'].sum()
    residencias_posibles = int(camas_totales / 100)
    
    print("\n--- RESULTADOS DEL CÁLCULO ---")
    print(f"   Clusters Totales Detectados: {len(stats)}")
    print(f"   ✅ Clusters VIABLES (>85 camas): {len(viables)}")
    print(f"   ⚠️ Clusters SUB-CRÍTICOS (Descartados): {len(subcriticos)}")
    print(f"   🏭 Potencial de Construcción (Solo Viables): {residencias_posibles} Residencias")
    
    if residencias_posibles < 1000:
        deficit = 1000 - residencias_posibles
        print(f"   📉 DÉFICIT DE OBJETIVO: Faltan {deficit} residencias para llegar a 1000.")
        print("      -> Se recomienda estrategia M&A (Adquisiciones) para cubrir el hueco.")

    # 4. GUARDADO DE DATOS
    # Guardamos el resumen de clusters
    stats.to_csv(OUTPUT_CLUSTERS, sep=';')
    
    # Guardamos los puntos individuales ETIQUETADOS (para poder pintarlos luego)
    # Hacemos merge para pegar la info de viabilidad a cada punto
    df_final_puntos = pd.merge(df_ml, stats[['Es_Viable', 'Capacidad_Teorica_Camas']], 
                               left_on='Cluster_ID', right_index=True)
    
    # Limpiamos el código CUSEC para el cruce con Shapefile (quitamos espacios y texto)
    # De "3120104001 Pamplona..." a "3120104001"
    df_final_puntos['CUSEC_LIMPIO'] = df_final_puntos['Seccion'].astype(str).str.split(' ').str[0].str.strip()
    
    df_final_puntos.to_csv(OUTPUT_PUNTOS_TAGGED, sep=';', index=False)
    
    print(f"\n✅ Datos procesados guardados en:")
    print(f"   1. Resumen Clusters: {OUTPUT_CLUSTERS}")
    print(f"   2. Detalle Puntos: {OUTPUT_PUNTOS_TAGGED}")

if __name__ == "__main__":
    calcular_masa_critica()
