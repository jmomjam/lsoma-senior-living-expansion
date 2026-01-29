#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
EXPANSION_1000_RESIDENCIAS.PY - Algoritmo de Expansión Adaptativa
================================================================================
Objetivo: Encontrar ~1000 ubicaciones viables para residencias mediante
          relajación inteligente de restricciones.

Autor: Senior Data Scientist - L-SOMA Project
Fecha: Enero 2026
================================================================================
"""

import pandas as pd
import numpy as np
from sklearn.cluster import DBSCAN
import os
from datetime import datetime

# ==============================================================================
# CONFIGURACIÓN DE RUTAS
# ==============================================================================
ARCHIVO_INPUT_GEO = "../datos/ranking_fase6_geo_ready.csv"
ARCHIVO_MATRIZ_P = "../datos/matriz_P_nacional_filtrada.parquet"
OUTPUT_LOG = "../datos/expansion_log.csv"
OUTPUT_CLUSTERS = "../datos/expansion_clusters_final.csv"

# ==============================================================================
# PARÁMETROS INMUTABLES (NO TOCAR)
# ==============================================================================
RADIO_CLUSTER_KM = 1.5  # Radio DBSCAN en km (NO MODIFICAR)
MIN_SECCIONES = 3       # Mínimo de secciones por cluster
COLS_TARGET = ['M_80-84', 'M_85-89', 'M_90-94', 'M_95-99', 'M_100 y más']

# ==============================================================================
# PARÁMETROS INICIALES "PRIME" (Punto de partida)
# ==============================================================================
PARAMS_PRIME = {
    'percentil_score': 85,      # Percentil mínimo de Score_Global
    'market_share': 0.03,       # 3% cuota de mercado
    'penalizacion_renta': 0.4,  # Penalización para rentas < 30k
    'camas_minimas': 85         # Umbral de break-even
}

# ==============================================================================
# LÍMITES DE RELAJACIÓN (Jerarquía de Riesgo)
# ==============================================================================
LIMITES = {
    # Nivel 1 - BAJO RIESGO: Umbral de Resonancia
    'percentil_score': {'min': 60, 'step': -1, 'nivel': 1, 'nombre': 'Percentil Score'},
    # Nivel 2 - RIESGO MEDIO: Market Share  
    'market_share': {'max': 0.06, 'step': 0.002, 'nivel': 2, 'nombre': 'Market Share'},
    # Nivel 3 - RIESGO ALTO: Penalización Económica
    'penalizacion_renta': {'max': 0.7, 'step': 0.05, 'nivel': 3, 'nombre': 'Penalización Renta'},
    # Nivel 4 - RIESGO CRÍTICO: Masa Crítica
    'camas_minimas': {'min': 60, 'step': -1, 'nivel': 4, 'nombre': 'Camas Mínimas'}
}

# ==============================================================================
# OBJETIVO
# ==============================================================================
OBJETIVO_RESIDENCIAS = 1000
MAX_ITERACIONES = 500  # Límite de seguridad

# ==============================================================================
# FUNCIONES DEL MODELO
# ==============================================================================

def cargar_datos():
    """Carga y prepara los datos de entrada."""
    print("=" * 70)
    print("   ALGORITMO DE EXPANSIÓN ADAPTATIVA - L-SOMA")
    print("=" * 70)
    print(f"\n>>> Cargando datos...")
    
    if not os.path.exists(ARCHIVO_INPUT_GEO):
        raise FileNotFoundError(f"No se encuentra: {ARCHIVO_INPUT_GEO}")
    
    df = pd.read_csv(ARCHIVO_INPUT_GEO, sep=';')
    print(f"    ✓ ranking_fase6_geo_ready.csv: {len(df):,} secciones")
    
    # Cargar Matriz P para cálculo real de targets
    if os.path.exists(ARCHIVO_MATRIZ_P):
        df_matriz = pd.read_parquet(ARCHIVO_MATRIZ_P)
        df_matriz['Pct_Target'] = df_matriz[COLS_TARGET].sum(axis=1)
        df = pd.merge(df, df_matriz[['Pct_Target']], left_on='Seccion', right_index=True, how='left')
        df['Pct_Target'] = df['Pct_Target'].fillna(0)
        df['Poblacion_Target_Real'] = df['Poblacion_Total'] * df['Pct_Target']
        print(f"    ✓ Matriz P cargada. Target medio: {df['Poblacion_Target_Real'].mean():.1f} mujeres/sección")
    else:
        # Fallback: estimación 6%
        df['Poblacion_Target_Real'] = df['Poblacion_Total'] * 0.06
        print("    ⚠ Matriz P no encontrada, usando estimación 6%")
    
    # Limpiar coordenadas
    df_clean = df.dropna(subset=['LATITUD', 'LONGITUD']).copy()
    print(f"    ✓ Secciones con coordenadas válidas: {len(df_clean):,}")
    
    return df_clean


def aplicar_penalizacion_renta(df, penalizacion):
    """Aplica penalización económica a secciones con renta baja."""
    df = df.copy()
    # Penalización para rentas < 30,000€
    df['Coef_Penalizacion'] = np.where(df['Renta_Hogar'] < 30000, penalizacion, 1.0)
    df['Score_Ajustado'] = df['Score_Global'] * df['Coef_Penalizacion']
    return df


def ejecutar_modelo(df, params):
    """
    Ejecuta el modelo completo con los parámetros dados.
    Retorna: (num_residencias, num_clusters_viables, df_clusters, camas_totales)
    """
    # 1. Aplicar penalización económica
    df = aplicar_penalizacion_renta(df, params['penalizacion_renta'])
    
    # 2. Filtrar por percentil de Score
    umbral_score = df['Score_Ajustado'].quantile(params['percentil_score'] / 100)
    df_filtrado = df[df['Score_Ajustado'] > umbral_score].copy()
    
    if len(df_filtrado) < MIN_SECCIONES:
        return 0, 0, pd.DataFrame(), 0
    
    # 3. Ejecutar DBSCAN
    coords = np.radians(df_filtrado[['LATITUD', 'LONGITUD']].values)
    eps_rad = RADIO_CLUSTER_KM / 6371.0  # Convertir km a radianes
    
    db = DBSCAN(eps=eps_rad, min_samples=MIN_SECCIONES, metric='haversine', algorithm='ball_tree')
    df_filtrado['Cluster_ID'] = db.fit_predict(coords)
    
    # 4. Eliminar ruido
    df_clusters = df_filtrado[df_filtrado['Cluster_ID'] != -1].copy()
    
    if len(df_clusters) == 0:
        return 0, 0, pd.DataFrame(), 0
    
    # 5. Agregar por cluster
    stats = df_clusters.groupby('Cluster_ID').agg({
        'Seccion': 'count',
        'Poblacion_Target_Real': 'sum',
        'Renta_Hogar': 'mean',
        'Score_Global': 'mean',
        'Score_Ajustado': 'mean',
        'LATITUD': 'mean',
        'LONGITUD': 'mean'
    }).rename(columns={'Seccion': 'Num_Secciones'})
    
    # 6. Calcular capacidad teórica
    stats['Camas_Potenciales'] = stats['Poblacion_Target_Real'] * params['market_share']
    
    # 7. Filtrar por viabilidad
    stats['Es_Viable'] = stats['Camas_Potenciales'] >= params['camas_minimas']
    viables = stats[stats['Es_Viable']].copy()
    
    # 8. Calcular residencias (cada 100 camas = 1 residencia)
    if len(viables) > 0:
        camas_totales = viables['Camas_Potenciales'].sum()
        num_residencias = int(camas_totales / 100)
    else:
        camas_totales = 0
        num_residencias = 0
    
    return num_residencias, len(viables), viables.reset_index(), camas_totales


def calcular_impacto_relajacion(df, params_actuales, parametro):
    """
    Calcula el impacto incremental de relajar un parámetro específico.
    Retorna: ganancia_marginal de residencias por unidad de relajación.
    """
    params_test = params_actuales.copy()
    limite_info = LIMITES[parametro]
    
    # Verificar si el parámetro ya está en su límite
    if 'min' in limite_info:
        if params_actuales[parametro] <= limite_info['min']:
            return 0, False  # Ya en límite
        params_test[parametro] = params_actuales[parametro] + limite_info['step']
    else:  # max
        if params_actuales[parametro] >= limite_info['max']:
            return 0, False  # Ya en límite
        params_test[parametro] = params_actuales[parametro] + limite_info['step']
    
    # Ejecutar modelo con parámetro relajado
    res_actual, _, _, _ = ejecutar_modelo(df, params_actuales)
    res_nuevo, _, _, _ = ejecutar_modelo(df, params_test)
    
    ganancia = res_nuevo - res_actual
    
    # Normalizar por nivel de riesgo (mayor riesgo = menor preferencia)
    ganancia_ajustada = ganancia / limite_info['nivel']
    
    return ganancia_ajustada, True


def seleccionar_mejor_relajacion(df, params_actuales):
    """
    Implementa la selección inteligente del parámetro a relajar.
    Prioriza maximizar ganancia con mínimo deterioro del modelo.
    """
    mejor_param = None
    mejor_ganancia = -1
    
    print("    Evaluando opciones de relajación:")
    
    for parametro in ['percentil_score', 'market_share', 'penalizacion_renta', 'camas_minimas']:
        ganancia, disponible = calcular_impacto_relajacion(df, params_actuales, parametro)
        
        estado = "✓" if disponible else "✗ (límite)"
        nombre = LIMITES[parametro]['nombre']
        nivel = LIMITES[parametro]['nivel']
        
        print(f"      - {nombre} (Nivel {nivel}): +{ganancia:.2f} resid/step {estado}")
        
        if disponible and ganancia > mejor_ganancia:
            mejor_ganancia = ganancia
            mejor_param = parametro
    
    return mejor_param, mejor_ganancia


def relajar_parametro(params, parametro):
    """Aplica la relajación al parámetro seleccionado."""
    nuevo_params = params.copy()
    limite_info = LIMITES[parametro]
    nuevo_params[parametro] = nuevo_params[parametro] + limite_info['step']
    return nuevo_params


def formatear_params(params):
    """Formatea los parámetros para logging."""
    return (f"P{params['percentil_score']:.0f}_"
            f"S{params['market_share']*100:.1f}%_"
            f"R{params['penalizacion_renta']:.2f}_"
            f"C{params['camas_minimas']:.0f}")


def ejecutar_expansion():
    """Función principal del algoritmo de expansión."""
    
    # Cargar datos
    df = cargar_datos()
    
    # Inicializar parámetros
    params = PARAMS_PRIME.copy()
    
    # Log de iteraciones
    log_iteraciones = []
    
    # Ejecutar modelo inicial (Prime)
    print(f"\n>>> Ejecutando modelo PRIME inicial...")
    res_inicial, clusters_iniciales, _, camas_iniciales = ejecutar_modelo(df, params)
    
    print(f"    Parámetros: {formatear_params(params)}")
    print(f"    Resultado: {res_inicial} residencias | {clusters_iniciales} clusters | {camas_iniciales:.0f} camas")
    
    log_iteraciones.append({
        'Iteracion': 0,
        'Params_Usados': formatear_params(params),
        'Residencias_Viables': res_inicial,
        'Camas_Totales': camas_iniciales,
        'Clusters_Viables': clusters_iniciales,
        'Param_Modificado': 'INICIAL'
    })
    
    # Guardar modelo Prime para comparación final
    modelo_prime = {
        'residencias': res_inicial,
        'clusters': clusters_iniciales,
        'camas': camas_iniciales,
        'params': params.copy()
    }
    
    # Bucle de expansión
    iteracion = 1
    residencias_actuales = res_inicial
    
    print(f"\n>>> Iniciando bucle de expansión (Objetivo: {OBJETIVO_RESIDENCIAS} residencias)...")
    print("=" * 70)
    
    while residencias_actuales < OBJETIVO_RESIDENCIAS and iteracion <= MAX_ITERACIONES:
        print(f"\n[Iteración {iteracion}] Residencias actuales: {residencias_actuales} | Gap: {OBJETIVO_RESIDENCIAS - residencias_actuales}")
        
        # Seleccionar mejor parámetro a relajar
        mejor_param, ganancia = seleccionar_mejor_relajacion(df, params)
        
        if mejor_param is None:
            print("\n⚠ TODOS LOS PARÁMETROS EN LÍMITE. No es posible expandir más.")
            break
        
        # Aplicar relajación
        params = relajar_parametro(params, mejor_param)
        nombre_param = LIMITES[mejor_param]['nombre']
        nuevo_valor = params[mejor_param]
        
        print(f"    >> Relajando [{nombre_param}] -> {nuevo_valor}")
        
        # Ejecutar modelo con nuevos parámetros
        residencias, clusters, df_viables, camas = ejecutar_modelo(df, params)
        
        print(f"    Resultado: {residencias} residencias | {clusters} clusters | {camas:.0f} camas")
        
        # Registrar en log
        log_iteraciones.append({
            'Iteracion': iteracion,
            'Params_Usados': formatear_params(params),
            'Residencias_Viables': residencias,
            'Camas_Totales': camas,
            'Clusters_Viables': clusters,
            'Param_Modificado': mejor_param
        })
        
        residencias_actuales = residencias
        iteracion += 1
    
    # Ejecutar modelo final para obtener clusters
    print("\n" + "=" * 70)
    print(">>> FINALIZANDO EXPANSIÓN...")
    
    res_final, clusters_final, df_clusters_final, camas_final = ejecutar_modelo(df, params)
    
    # Guardar resultados
    print(f"\n>>> Guardando resultados...")
    
    # Log de iteraciones
    df_log = pd.DataFrame(log_iteraciones)
    df_log.to_csv(OUTPUT_LOG, sep=';', index=False)
    print(f"    ✓ {OUTPUT_LOG}")
    
    # Clusters finales
    if len(df_clusters_final) > 0:
        df_clusters_final.to_csv(OUTPUT_CLUSTERS, sep=';', index=False)
        print(f"    ✓ {OUTPUT_CLUSTERS}")
    
    # ==============================================================================
    # COMPARATIVA FINAL
    # ==============================================================================
    print("\n" + "=" * 70)
    print("                    COMPARATIVA FINAL")
    print("=" * 70)
    
    # Re-ejecutar Prime para obtener estadísticas detalladas
    _, _, df_prime_clusters, _ = ejecutar_modelo(df, PARAMS_PRIME)
    
    # Calcular métricas
    if len(df_prime_clusters) > 0:
        renta_prime = df_prime_clusters['Renta_Hogar'].mean()
        score_prime = df_prime_clusters['Score_Global'].mean()
        camas_media_prime = df_prime_clusters['Camas_Potenciales'].mean()
    else:
        renta_prime = score_prime = camas_media_prime = 0
    
    if len(df_clusters_final) > 0:
        renta_final = df_clusters_final['Renta_Hogar'].mean()
        score_final = df_clusters_final['Score_Global'].mean()
        camas_media_final = df_clusters_final['Camas_Potenciales'].mean()
    else:
        renta_final = score_final = camas_media_final = 0
    
    print(f"\n{'Métrica':<30} {'Modelo PRIME':>20} {'Modelo EXPANDIDO':>20} {'Δ Cambio':>15}")
    print("-" * 85)
    print(f"{'Residencias Potenciales':<30} {modelo_prime['residencias']:>20} {res_final:>20} {res_final - modelo_prime['residencias']:>+15}")
    print(f"{'Clusters Viables':<30} {modelo_prime['clusters']:>20} {clusters_final:>20} {clusters_final - modelo_prime['clusters']:>+15}")
    print(f"{'Camas Totales':<30} {modelo_prime['camas']:>20,.0f} {camas_final:>20,.0f} {camas_final - modelo_prime['camas']:>+15,.0f}")
    print(f"{'Renta Media Cluster (€)':<30} {renta_prime:>20,.0f} {renta_final:>20,.0f} {renta_final - renta_prime:>+15,.0f}")
    print(f"{'Score Demográfico Medio':<30} {score_prime:>20.4f} {score_final:>20.4f} {score_final - score_prime:>+15.4f}")
    print(f"{'Tamaño Medio Residencia (camas)':<30} {camas_media_prime:>20.1f} {camas_media_final:>20.1f} {camas_media_final - camas_media_prime:>+15.1f}")
    
    print("\n" + "=" * 70)
    print(f"PARÁMETROS FINALES: {formatear_params(params)}")
    print(f"TOTAL ITERACIONES: {iteracion - 1}")
    
    if residencias_actuales >= OBJETIVO_RESIDENCIAS:
        print(f"\n✅ OBJETIVO ALCANZADO: {residencias_actuales} residencias >= {OBJETIVO_RESIDENCIAS}")
    else:
        print(f"\n⚠ LÍMITE DE EXPANSIÓN: {residencias_actuales} residencias (máximo posible)")
        print(f"   Gap restante: {OBJETIVO_RESIDENCIAS - residencias_actuales} residencias")
    
    print("=" * 70)
    
    return df_log, df_clusters_final


# ==============================================================================
# EJECUCIÓN
# ==============================================================================
if __name__ == "__main__":
    print(f"\nInicio: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    df_log, df_clusters = ejecutar_expansion()
    print(f"\nFin: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
