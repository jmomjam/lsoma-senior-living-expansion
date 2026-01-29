#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
UNIFICAR_DATOS_MAPA.PY - Genera datos para el mapa interactivo
================================================================================
Genera un CSV con las secciones censales para las capas de Frontera y Competencia,
usando los parámetros finales del algoritmo de expansión.

Output: secciones_frontera_competencia.csv
================================================================================
"""

import pandas as pd
import numpy as np
from sklearn.cluster import DBSCAN
import os

# ==============================================================================
# CONFIGURACIÓN
# ==============================================================================
INPUT_GEO = "../datos/ranking_fase6_geo_ready.csv"
MATRIZ_P = "../datos/matriz_P_nacional_filtrada.parquet"
OUTPUT_FILE = "../datos/secciones_frontera_competencia.csv"

# Parámetros finales del algoritmo de expansión (P60_S6.0%_R0.70_C60)
PARAMS_EXPANSION = {
    'percentil_score': 60,
    'market_share': 0.06,
    'penalizacion_renta': 0.70,
    'camas_minimas': 60
}

# Parámetros DBSCAN (inmutables)
RADIO_KM = 1.5
MIN_SECCIONES = 3
COLS_TARGET = ['M_80-84', 'M_85-89', 'M_90-94', 'M_95-99', 'M_100 y más']

# Umbrales de saturación para clasificación de océanos
UMBRAL_BLUE_OCEAN = 0.20
UMBRAL_SATURADO = 1.0

# Camas por competidor (media IMSERSO)
CAMAS_POR_COMPETIDOR = 75

print("=" * 60)
print("   UNIFICADOR DE DATOS PARA MAPA INTERACTIVO")
print("=" * 60)

# ==============================================================================
# CARGAR DATOS
# ==============================================================================

print("\n>>> Cargando datos...")

df = pd.read_csv(INPUT_GEO, sep=';')
print(f"    ✓ ranking_fase6_geo_ready.csv: {len(df):,} secciones")

# Cargar Matriz P para target real
if os.path.exists(MATRIZ_P):
    df_matriz = pd.read_parquet(MATRIZ_P)
    df_matriz['Pct_Target'] = df_matriz[COLS_TARGET].sum(axis=1)
    df = pd.merge(df, df_matriz[['Pct_Target']], left_on='Seccion', right_index=True, how='left')
    df['Pct_Target'] = df['Pct_Target'].fillna(0)
    df['Poblacion_Target_Real'] = df['Poblacion_Total'] * df['Pct_Target']
    print(f"    ✓ Matriz P cargada")
else:
    df['Poblacion_Target_Real'] = df['Poblacion_Total'] * 0.06
    print("    ⚠ Matriz P no encontrada, usando estimación")

# Limpiar coordenadas
df = df.dropna(subset=['LATITUD', 'LONGITUD']).copy()
print(f"    ✓ Secciones con coordenadas: {len(df):,}")

# ==============================================================================
# APLICAR MODELO DE EXPANSIÓN
# ==============================================================================

print("\n>>> Aplicando modelo de expansión...")
print(f"    Parámetros: P{PARAMS_EXPANSION['percentil_score']}_"
      f"S{PARAMS_EXPANSION['market_share']*100:.1f}%_"
      f"R{PARAMS_EXPANSION['penalizacion_renta']:.2f}_"
      f"C{PARAMS_EXPANSION['camas_minimas']}")

# 1. Aplicar penalización económica
df['Coef_Penalizacion'] = np.where(df['Renta_Hogar'] < 30000, 
                                    PARAMS_EXPANSION['penalizacion_renta'], 1.0)
df['Score_Ajustado'] = df['Score_Global'] * df['Coef_Penalizacion']

# 2. Filtrar por percentil
umbral = df['Score_Ajustado'].quantile(PARAMS_EXPANSION['percentil_score'] / 100)
df_filtrado = df[df['Score_Ajustado'] > umbral].copy()
print(f"    ✓ Secciones tras filtro percentil: {len(df_filtrado):,}")

# 3. Ejecutar DBSCAN
print("\n>>> Ejecutando DBSCAN geodésico...")
coords = np.radians(df_filtrado[['LATITUD', 'LONGITUD']].values)
eps_rad = RADIO_KM / 6371.0

db = DBSCAN(eps=eps_rad, min_samples=MIN_SECCIONES, metric='haversine', algorithm='ball_tree')
df_filtrado['Cluster_ID'] = db.fit_predict(coords)

# 4. Eliminar ruido
df_clusters = df_filtrado[df_filtrado['Cluster_ID'] != -1].copy()
n_clusters = df_clusters['Cluster_ID'].nunique()
print(f"    ✓ Clusters formados: {n_clusters}")
print(f"    ✓ Secciones en clusters: {len(df_clusters):,}")

# ==============================================================================
# CALCULAR ESTADÍSTICAS POR CLUSTER
# ==============================================================================

print("\n>>> Calculando estadísticas por cluster...")

stats = df_clusters.groupby('Cluster_ID').agg({
    'Seccion': 'count',
    'Poblacion_Target_Real': 'sum',
    'Renta_Hogar': 'mean',
    'Score_Global': 'mean',
    'LATITUD': 'mean',
    'LONGITUD': 'mean'
}).rename(columns={'Seccion': 'Num_Secciones'})

# Calcular camas potenciales
stats['Camas_Potenciales'] = stats['Poblacion_Target_Real'] * PARAMS_EXPANSION['market_share']

# Filtrar viables
stats['Es_Viable'] = stats['Camas_Potenciales'] >= PARAMS_EXPANSION['camas_minimas']

n_viables = stats['Es_Viable'].sum()
print(f"    ✓ Clusters viables (≥{PARAMS_EXPANSION['camas_minimas']} camas): {n_viables}")

# ==============================================================================
# SIMULAR COMPETENCIA (sin API, basado en densidad poblacional)
# ==============================================================================

print("\n>>> Simulando índice de saturación...")

# Estimación de competidores basada en densidad poblacional
# Aproximación: regiones más pobladas tienen más competidores
stats['Num_Competidores_Est'] = np.maximum(1, 
    (stats['Camas_Potenciales'] / 500).astype(int))

# Calcular índice de saturación
stats['Oferta_Estimada'] = stats['Num_Competidores_Est'] * CAMAS_POR_COMPETIDOR
stats['Indice_Saturacion'] = stats['Oferta_Estimada'] / stats['Camas_Potenciales']

# Clasificar tipo de océano
def clasificar_oceano(i_sat):
    if i_sat < UMBRAL_BLUE_OCEAN:
        return "Blue Ocean"
    elif i_sat <= UMBRAL_SATURADO:
        return "Batalla"
    else:
        return "Saturado"

stats['Tipo_Oceano'] = stats['Indice_Saturacion'].apply(clasificar_oceano)

# Mostrar distribución
print(f"    Blue Oceans: {(stats['Tipo_Oceano'] == 'Blue Ocean').sum()}")
print(f"    Batallas: {(stats['Tipo_Oceano'] == 'Batalla').sum()}")
print(f"    Saturados: {(stats['Tipo_Oceano'] == 'Saturado').sum()}")

# ==============================================================================
# UNIR STATS A SECCIONES
# ==============================================================================

print("\n>>> Uniendo estadísticas a secciones...")

# Merge stats back to sections
stats_cols = ['Camas_Potenciales', 'Es_Viable', 'Indice_Saturacion', 'Tipo_Oceano']
stats_for_merge = stats[stats_cols].reset_index()

df_final = df_clusters.merge(stats_for_merge, on='Cluster_ID', how='left')

# Seleccionar columnas para output
output_cols = [
    'Seccion', 'CUSEC', 'Cluster_ID', 'LATITUD', 'LONGITUD',
    'Renta_Hogar', 'Score_Global', 'Poblacion_Target_Real',
    'Camas_Potenciales', 'Es_Viable', 'Indice_Saturacion', 'Tipo_Oceano'
]

# Asegurar que CUSEC existe
if 'CUSEC' not in df_final.columns and 'Seccion' in df_final.columns:
    # Extraer CUSEC del nombre de sección si es necesario
    df_final['CUSEC'] = df_final['Seccion'].str.extract(r'^(\d+)')[0]

df_output = df_final[output_cols].copy()

# ==============================================================================
# GUARDAR
# ==============================================================================

print(f"\n>>> Guardando: {OUTPUT_FILE}")
df_output.to_csv(OUTPUT_FILE, sep=';', index=False)

print("\n" + "=" * 60)
print("✅ DATOS UNIFICADOS GENERADOS")
print(f"   Archivo: {OUTPUT_FILE}")
print(f"   Secciones: {len(df_output):,}")
print(f"   Clusters: {df_output['Cluster_ID'].nunique()}")
print("=" * 60)
