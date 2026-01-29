#!/usr/bin/env python3
"""
Script para calcular métricas reales del informe L-SOMA
Genera todos los datos necesarios para sustituir los inventados
"""

import pandas as pd
import numpy as np
import os

# Configuración
DATA_DIR = "/Users/cosotos/proyectos/akademia/casoprácticoIA/datos"

print("=" * 60)
print("AUDITORÍA DE DATOS DEL INFORME L-SOMA")
print("=" * 60)

# =============================================================================
# 1. NÚMERO TOTAL DE SECCIONES CENSALES
# =============================================================================
print("\n### 1. SECCIONES CENSALES TOTALES ###")

# Cargar archivo con todos los scores
df_scores = pd.read_csv(os.path.join(DATA_DIR, "ranking_fase5_score_final.csv"), sep=";")
total_secciones = len(df_scores)
print(f"Secciones totales (ranking_fase5): {total_secciones:,}")

# =============================================================================
# 2. SECCIONES TOP 15% (PERCENTIL 85)
# =============================================================================
print("\n### 2. SECCIONES TOP 15% (Percentil 85) ###")

# Cargar archivo con datos de clustering
df_geo = pd.read_csv(os.path.join(DATA_DIR, "ranking_fase8_puntos_con_cluster.csv"), sep=";")
secciones_clustering = len(df_geo)
print(f"Secciones en clustering (fase8): {secciones_clustering:,}")

# Calcular teórico del 15%
teorico_15pct = int(total_secciones * 0.15)
print(f"15% teórico de {total_secciones}: {teorico_15pct:,}")

# =============================================================================
# 3. ESTADÍSTICAS DE CLUSTERS
# =============================================================================
print("\n### 3. ESTADÍSTICAS DE CLUSTERS ###")

df_clusters = pd.read_csv(os.path.join(DATA_DIR, "ranking_fase7_clusters.csv"), sep=";")
n_clusters = len(df_clusters)
print(f"Clusters detectados: {n_clusters}")

# Secciones viables vs ruido
secciones_viables = df_geo[df_geo['Es_Viable'] == True].shape[0] if 'Es_Viable' in df_geo.columns else "N/A"
secciones_ruido = df_geo[df_geo['Es_Viable'] == False].shape[0] if 'Es_Viable' in df_geo.columns else "N/A"
print(f"Secciones viables (Es_Viable=True): {secciones_viables:,}")
print(f"Secciones ruido (Es_Viable=False): {secciones_ruido:,}")

# =============================================================================
# 4. TOP 10 CLUSTERS - VERIFICACIÓN
# =============================================================================
print("\n### 4. TOP 10 CLUSTERS ###")

df_clusters_sorted = df_clusters.sort_values('Potencia_Total', ascending=False).head(10)
print("\nRank | Secciones | Renta Media | Potencia")
print("-" * 50)
for i, (_, row) in enumerate(df_clusters_sorted.iterrows(), 1):
    print(f"{i:4d} | {row['Num_Secciones']:9d} | {row['Renta_Media']:11,.0f} | {row['Potencia_Total']:8.1f}")

# =============================================================================
# 5. ANÁLISIS DE ESCENARIOS POR CUOTA DE MERCADO
# =============================================================================
print("\n### 5. ANÁLISIS DE ESCENARIOS POR CUOTA DE MERCADO ###")

# Cargar clusters analizados con capacidad de camas
df_clusters_analisis = pd.read_csv(os.path.join(DATA_DIR, "ranking_fase8_clusters_analizados.csv"), sep=";")

# El umbral de viabilidad es 85 camas según el informe
UMBRAL_CAMAS = 85
CAMAS_POR_RESIDENCIA = 100  # Asumido

# La capacidad actual está calculada con algún share base
# Necesitamos saber el share base usado
# Mirando los datos: Capacidad_Teorica_Camas parece estar calculada con un share

# Analizar la relación entre secciones y capacidad
print("\nCapacidad actual en archivo (share desconocido):")
print(df_clusters_analisis[['Cluster_ID', 'Num_Secciones', 'Capacidad_Teorica_Camas', 'Es_Viable']].head(10).to_string())

# Calculamos el share implícito
# Si tenemos población target y capacidad, podemos inferir el share
# Pero necesitamos la población target

# Alternativa: recalcular para diferentes shares
# La fórmula es: Capacidad = Sum(Target_i) * share
# Target_i = Poblacion_i * ratio_M80+

print("\n### RECÁLCULO PARA DIFERENTES SHARES ###")

# Calcular población target por cluster
# Necesitamos la suma de Target por cluster desde ranking_fase8_puntos

# Agrupar por cluster y sumar población
if 'Poblacion_Total' in df_geo.columns:
    # Calcular target como % de mujeres 80+
    # El ratio está en las columnas de la matriz P, pero podemos usar Ratio_Abuelas si existe
    
    df_geo_valid = df_geo[df_geo['Cluster_ID'] >= 0]  # Excluir ruido (-1)
    
    # Agrupar por cluster
    cluster_stats = df_geo_valid.groupby('Cluster_ID').agg({
        'Poblacion_Total': 'sum',
        'Score_Global': 'sum'
    }).reset_index()
    
    # Estimar target: asumimos que ~6% de población son mujeres 80+
    # (basado en pirámide demográfica típica española)
    RATIO_M80_ESTIMADO = 0.06
    cluster_stats['Target_Estimado'] = cluster_stats['Poblacion_Total'] * RATIO_M80_ESTIMADO
    
    print(f"\nTotal población en clusters: {cluster_stats['Poblacion_Total'].sum():,.0f}")
    print(f"Target estimado total (6% M80+): {cluster_stats['Target_Estimado'].sum():,.0f}")
    
    # Ahora calculamos escenarios
    shares = [0.015, 0.02, 0.03, 0.05]
    
    print("\n" + "=" * 70)
    print("ESCENARIOS DE VIABILIDAD")
    print("=" * 70)
    print(f"{'Escenario':<20} | {'Share':>8} | {'Clust.Viables':>13} | {'Residencias':>11} | {'Gap vs 1000':>11}")
    print("-" * 70)
    
    for share in shares:
        cluster_stats['Capacidad'] = cluster_stats['Target_Estimado'] * share
        clusters_viables = (cluster_stats['Capacidad'] >= UMBRAL_CAMAS).sum()
        
        # Residencias = sum(capacidad / 100) para clusters viables
        cap_viables = cluster_stats[cluster_stats['Capacidad'] >= UMBRAL_CAMAS]['Capacidad'].sum()
        n_residencias = int(cap_viables / CAMAS_POR_RESIDENCIA)
        gap = n_residencias - 1000
        
        escenario = {0.015: "Muy Conservador", 0.02: "Conservador", 0.03: "Base", 0.05: "Agresivo"}
        print(f"{escenario[share]:<20} | {share*100:>7.1f}% | {clusters_viables:>13d} | {n_residencias:>11d} | {gap:>+11d}")

# =============================================================================
# 6. VERIFICACIÓN DE HISTOGRAMA DE RESONANCIA
# =============================================================================
print("\n### 6. ESTADÍSTICAS DE RESONANCIA ###")

if 'Resonancia' in df_scores.columns:
    print(f"Media de Resonancia: {df_scores['Resonancia'].mean():.4f}")
    print(f"Mediana: {df_scores['Resonancia'].median():.4f}")
    print(f"Percentil 85: {df_scores['Resonancia'].quantile(0.85):.4f}")
    print(f"Máximo: {df_scores['Resonancia'].max():.4f}")

# =============================================================================
# 7. TARGET PROMEDIO POR SECCIÓN
# =============================================================================
print("\n### 7. TARGET PROMEDIO POR SECCIÓN ###")

if 'Poblacion_Total' in df_geo.columns:
    poblacion_media = df_geo['Poblacion_Total'].mean()
    target_estimado_medio = poblacion_media * RATIO_M80_ESTIMADO
    print(f"Población media por sección: {poblacion_media:.1f}")
    print(f"Target estimado medio (6% M80+): {target_estimado_medio:.1f}")

# =============================================================================
# RESUMEN FINAL
# =============================================================================
print("\n" + "=" * 60)
print("VALORES PARA ACTUALIZAR EN EL INFORME")
print("=" * 60)

print(f"""
DATOS VERIFICADOS:
- Total secciones censales: {total_secciones:,}
- Secciones en clustering (Top %): {secciones_clustering:,}
- Clusters detectados: {n_clusters}
- Secciones viables: {secciones_viables:,}
- Secciones ruido: {secciones_ruido:,}
- Media Resonancia: {df_scores['Resonancia'].mean():.2f}
- Percentil 85 Resonancia: {df_scores['Resonancia'].quantile(0.85):.3f}
""")
