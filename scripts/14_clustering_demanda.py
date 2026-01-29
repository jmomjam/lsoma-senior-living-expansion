import pandas as pd
import numpy as np
import os
from sklearn.cluster import DBSCAN
from geopy.distance import great_circle

# --- CONFIGURACIÓN ---
ARCHIVO_GEO_READY = "../datos/ranking_fase6_geo_ready.csv"
OUTPUT_CLUSTERS = "../datos/ranking_fase7_clusters.csv"

# --- HIPERPARÁMETROS DEL ML (Criterio de Negocio) ---
RADIO_CAPTACION_KM = 1.5   # Radio máximo para considerar que dos secciones son "vecinas"
MIN_SECCIONES_CLUSTER = 3  # Mínimo de secciones ricas juntas para formar un cluster viable
                           # (3 secciones ~ 4.500 habitantes ~ suficiente para 100 plazas)

def ejecutar_clustering():
    print("--- FASE 6: MACHINE LEARNING ESPACIAL (DBSCAN) ---")
    
    # 1. CARGAR DATOS
    print(">>> Cargando puntos geolocalizados...")
    if not os.path.exists(ARCHIVO_GEO_READY):
        print("❌ Error: Falta archivo fase 6.")
        return
        
    df = pd.read_csv(ARCHIVO_GEO_READY, sep=';')
    
    # FILTRO PREVIO AL ML:
    # No queremos agrupar "basura". Solo metemos al algoritmo las secciones 
    # que ya tienen un Score Global decente.
    # Usamos el percentil 75 como corte (Top 25% de España)
    umbral_calidad = df['Score_Global'].quantile(0.85)
    print(f"   Umbral de corte para ML (Top 15%): Score > {umbral_calidad:.4f}")
    
    df_ml = df[df['Score_Global'] > umbral_calidad].copy()
    print(f"   Puntos candidatos a clusterizar: {len(df_ml):,.0f}")
    
    if len(df_ml) == 0:
        print("❌ No hay puntos suficientes. Baja el umbral.")
        return

    # 2. PREPARACIÓN DE COORDENADAS (RADIANES)
    # DBSCAN con métrica 'haversine' necesita radianes
    # Primero eliminamos filas con coordenadas faltantes (NaN)
    filas_antes = len(df_ml)
    df_ml = df_ml.dropna(subset=['LATITUD', 'LONGITUD'])
    filas_despues = len(df_ml)
    if filas_antes != filas_despues:
        print(f"   ⚠️ Eliminadas {filas_antes - filas_despues} filas sin coordenadas válidas")
    
    if len(df_ml) == 0:
        print("❌ No quedan puntos con coordenadas válidas.")
        return
    
    coords = df_ml[['LATITUD', 'LONGITUD']].values
    coords_rad = np.radians(coords)
    
    # 3. EJECUCIÓN DEL ALGORITMO
    print(f">>> Ejecutando DBSCAN (Radio={RADIO_CAPTACION_KM}km, MinSamples={MIN_SECCIONES_CLUSTER})...")
    
    # El radio de la Tierra es aprox 6371 km
    epsilon = RADIO_CAPTACION_KM / 6371.0
    
    db = DBSCAN(eps=epsilon, min_samples=MIN_SECCIONES_CLUSTER, metric='haversine', algorithm='ball_tree')
    db.fit(coords_rad)
    
    # 4. RESULTADOS
    cluster_labels = db.labels_
    df_ml['Cluster_ID'] = cluster_labels
    
    # El label -1 significa "Ruido" (Puntos aislados que no forman grupo)
    n_clusters = len(set(cluster_labels)) - (1 if -1 in cluster_labels else 0)
    n_ruido = list(cluster_labels).count(-1)
    
    print(f"   ✅ Clusters detectados: {n_clusters}")
    print(f"   📉 Puntos descartados (aislados): {n_ruido}")
    
    # 5. CARACTERIZACIÓN DE LOS CLUSTERS
    # Ahora vamos a calcular la "Potencia" de cada cluster (Suma de Scores)
    print(">>> Analizando potencia comercial de cada cluster...")
    
    # Agrupamos por Cluster_ID (excluyendo el -1)
    df_clusters = df_ml[df_ml['Cluster_ID'] != -1]
    
    resumen_clusters = df_clusters.groupby('Cluster_ID').agg({
        'Score_Global': ['sum', 'mean', 'count'], # Potencia total, Calidad media, Tamaño
        'Renta_Hogar': 'mean',
        'Ratio_Hijas': 'mean',
        'Presion_Cuidados': 'mean',
        'LATITUD': 'mean', # Centroide del cluster
        'LONGITUD': 'mean',
        'Seccion': lambda x: list(x)[:3] # Guardamos ejemplos de nombres para saber dónde es
    })
    
    # Aplanamos nombres de columnas
    resumen_clusters.columns = ['Potencia_Total', 'Score_Medio', 'Num_Secciones', 
                                'Renta_Media', 'Ratio_Hijas_Medio', 'Presion_Media',
                                'Lat_Centro', 'Lon_Centro', 'Toponimos']
    
    # Ordenamos por Potencia Total (Score acumulado)
    resumen_clusters = resumen_clusters.sort_values(by='Potencia_Total', ascending=False)
    
    # 6. GUARDADO
    # Guardamos el resumen de Clusters (Este es tu Mapa de Tesoros)
    resumen_clusters.to_csv(OUTPUT_CLUSTERS, sep=';')
    print(f"✅ ANÁLISIS DE CLUSTERS FINALIZADO: {OUTPUT_CLUSTERS}")
    
    # 7. VISUALIZACIÓN
    print("\n--- TOP 10 ZONAS DE INVERSIÓN (MANCHAS DE DEMANDA) ---")
    # Mostramos columnas clave
    pd.options.display.max_colwidth = 50
    print(resumen_clusters[['Toponimos', 'Num_Secciones', 'Renta_Media', 'Presion_Media', 'Potencia_Total']].head(10))

if __name__ == "__main__":
    ejecutar_clustering()
