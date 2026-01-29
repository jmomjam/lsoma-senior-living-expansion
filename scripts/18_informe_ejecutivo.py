import pandas as pd
import numpy as np
from sklearn.cluster import DBSCAN
import sys

# --- CONFIGURACIÓN ---
ARCHIVO_INPUT = "../datos/ranking_fase6_geo_ready.csv"
ARCHIVO_MATRIZ_P = "../datos/matriz_P_nacional_filtrada.parquet"  # Para cálculo real de targets
ARCHIVO_COMPETENCIA = "../datos/ranking_fase8_competencia.csv" # Opcional, por si existe

# HIPERPARÁMETROS DE NEGOCIO
RADIO_CLUSTER_KM = 1.5
MIN_SECCIONES = 3
COLS_TARGET = ['M_80-84', 'M_85-89', 'M_90-94', 'M_95-99', 'M_100 y más']  # Columnas mujeres 80+
MARKET_SHARE = 0.03         # Cuota de captura (3%)
CAMAS_BREAK_EVEN = 85       # Umbral de rentabilidad

def generar_informe_ejecutivo():
    print("==========================================================")
    print("       INFORME EJECUTIVO FINAL: PROYECTO L-SOMA       ")
    print("==========================================================\n")
    
    # 1. CARGA Y LIMPIEZA
    try:
        df = pd.read_csv(ARCHIVO_INPUT, sep=';')
    except FileNotFoundError:
        print(f"❌ Error Crítico: No encuentro {ARCHIVO_INPUT}")
        return

    total_secciones = len(df)
    
    # 1.1 CORRECCIÓN CRÍTICA: Cargar Matriz P para cálculo real de targets
    print("   Cargando Matriz P para cálculo real de targets...")
    import os
    if os.path.exists(ARCHIVO_MATRIZ_P):
        df_matriz = pd.read_parquet(ARCHIVO_MATRIZ_P)
        df_matriz['Pct_Target'] = df_matriz[COLS_TARGET].sum(axis=1)
        df = pd.merge(df, df_matriz[['Pct_Target']], left_on='Seccion', right_index=True, how='left')
        df['Pct_Target'] = df['Pct_Target'].fillna(0)
        df['Poblacion_Target_Real'] = df['Poblacion_Total'] * df['Pct_Target']
        print(f"   ✔ Target promedio real: {df['Poblacion_Target_Real'].mean():.1f} mujeres/sección")
    else:
        print("   ⚠️ Matriz P no encontrada, usando estimación (6% población)")
        df['Poblacion_Target_Real'] = df['Poblacion_Total'] * 0.06
    
    # LIMPIEZA DE ERROR (NaNs)
    df_clean = df.dropna(subset=['LATITUD', 'LONGITUD']).copy()
    descartadas_geo = total_secciones - len(df_clean)
    
    # FILTRO DE CALIDAD (Tier 1)
    umbral_score = df_clean['Score_Global'].quantile(0.85)
    df_ml = df_clean[df_clean['Score_Global'] > umbral_score].copy()
    
    print(f"[1. AUDITORÍA DE DATOS]")
    print(f"   - Universo Total Analizado: {total_secciones:,.0f} secciones")
    print(f"   - Descartadas sin coordenadas: {descartadas_geo}")
    print(f"   - Secciones Premium (Top 15%): {len(df_ml):,.0f} (Score > {umbral_score:.3f})")

    # 2. PROCESADO DE CLUSTERS (RE-CÁLCULO ROBUSTO)
    coords = np.radians(df_ml[['LATITUD', 'LONGITUD']].values)
    db = DBSCAN(eps=RADIO_CLUSTER_KM/6371., min_samples=MIN_SECCIONES, metric='haversine').fit(coords)
    df_ml['Cluster_ID'] = db.labels_
    
    # Ignorar ruido (-1)
    df_clusters = df_ml[df_ml['Cluster_ID'] != -1].copy()
    
    # Agregación por Cluster
    resumen = df_clusters.groupby('Cluster_ID').agg({
        'Seccion': 'count',
        'Renta_Hogar': 'mean',
        'Presion_Cuidados': 'mean',
        'Score_Global': 'mean',
        'Poblacion_Target_Real': 'sum'  # SUMA REAL de mujeres 80+
    }).rename(columns={'Seccion': 'Num_Secciones'})
    
    # 3. FÍSICA DEL NEGOCIO (VIABILIDAD) - CORREGIDO
    # Capacidad = Suma_Target_Real * Share (ya no usa constante fija)
    resumen['Demanda_Total_Target'] = resumen['Poblacion_Target_Real']
    resumen['Camas_Potenciales'] = resumen['Demanda_Total_Target'] * MARKET_SHARE
    resumen['Es_Viable'] = resumen['Camas_Potenciales'] >= CAMAS_BREAK_EVEN
    
    # Separación
    viables = resumen[resumen['Es_Viable']]
    no_viables = resumen[~resumen['Es_Viable']]
    
    # Cálculo de Residencias Construibles (Floor division // 100)
    # Asumimos residencias estándar de 100 camas
    total_camas_viables = viables['Camas_Potenciales'].sum()
    num_residencias_total = int(total_camas_viables / 100)
    
    # 4. IMPRESIÓN DE CONCLUSIONES
    print(f"\n[2. RESULTADOS DE EXPANSIÓN]")
    print(f"   - Clusters Detectados: {len(resumen)}")
    print(f"   ✅ Clusters VIABLES (Masa Crítica > {CAMAS_BREAK_EVEN} camas): {len(viables)}")
    print(f"   ⚠️ Clusters SUB-CRÍTICOS (Descartados): {len(no_viables)}")
    print(f"\n   >> CAPACIDAD TOTAL DE ABSORCIÓN (SOLO VIABLES): {num_residencias_total} NUEVAS RESIDENCIAS <<")
    
    # 5. ANÁLISIS DE ABSORCIÓN COMPLETO (TODOS LOS CLUSTERS)
    # Incluye clusters viables y sub-críticos para ver el potencial máximo
    MAX_RESIDENCIAS = 1000
    CAMAS_POR_RESIDENCIA = 100
    
    total_camas_todos = resumen['Camas_Potenciales'].sum()
    num_residencias_todos = int(total_camas_todos / CAMAS_POR_RESIDENCIA)
    
    # Limitar al máximo de 1000 residencias
    residencias_efectivas = min(num_residencias_todos, MAX_RESIDENCIAS)
    
    print(f"\n[3. ANÁLISIS DE CAPACIDAD DE ABSORCIÓN (TODOS LOS CLUSTERS)]")
    print(f"   - Total Camas Potenciales (Todos clusters): {total_camas_todos:,.0f}")
    print(f"   - Residencias Potenciales (sin límite): {num_residencias_todos}")
    print(f"   - LÍMITE DE PROYECTO: {MAX_RESIDENCIAS} residencias ({CAMAS_POR_RESIDENCIA} camas c/u)")
    print(f"   - Residencias Efectivas (con límite): {residencias_efectivas}")
    
    if num_residencias_todos >= MAX_RESIDENCIAS:
        excedente = num_residencias_todos - MAX_RESIDENCIAS
        print(f"   🚀 MERCADO SATURADO: Hay demanda para {excedente} residencias adicionales (reserva)")
    else:
        deficit = MAX_RESIDENCIAS - num_residencias_todos
        pct_cubierto = (num_residencias_todos / MAX_RESIDENCIAS) * 100
        print(f"   📉 DÉFICIT: Faltan {deficit} centros para el objetivo de {MAX_RESIDENCIAS}")
        print(f"      Cobertura del Plan: {pct_cubierto:.1f}%")
    
    # Desglose por tipo de cluster
    camas_viables = viables['Camas_Potenciales'].sum()
    camas_no_viables = no_viables['Camas_Potenciales'].sum()
    residencias_viables = int(camas_viables / CAMAS_POR_RESIDENCIA)
    residencias_no_viables = int(camas_no_viables / CAMAS_POR_RESIDENCIA)
    
    print(f"\n   [DESGLOSE POR TIPO DE CLUSTER]")
    print(f"   ✅ Viables: {residencias_viables} residencias ({camas_viables:,.0f} camas)")
    print(f"   ⚠️ Sub-críticos: {residencias_no_viables} residencias ({camas_no_viables:,.0f} camas)")
    print(f"      Nota: Los sub-críticos requieren estrategia M&A o consolidación")
    
    # Análisis de Déficit original
    OBJETIVO = 1000
    if residencias_viables < OBJETIVO:
        deficit = OBJETIVO - residencias_viables
        pct_cubierto = (residencias_viables / OBJETIVO) * 100
        print(f"\n   📊 ESTRATEGIA RECOMENDADA:")
        print(f"      - Construcción directa: {residencias_viables} residencias (clusters viables)")
        if residencias_no_viables > 0:
            print(f"      - M&A en clusters sub-críticos: Potencial de {residencias_no_viables} adicionales")
        print(f"      -\u003e RECOMENDACIÓN: Combinar construcción + adquisiciones para cubrir objetivo")
    else:
        print(f"\n   🚀 OBJETIVO SUPERADO: El mercado soporta el plan de expansión solo con clusters viables.")

    print(f"\n[4. PERFIL ECONÓMICO DE LA EXPANSIÓN]")
    renta_media_target = viables['Renta_Hogar'].mean() if len(viables) > 0 else 0
    presion_media_target = viables['Presion_Cuidados'].mean() if len(viables) > 0 else 0
    print(f"   - Renta Media en Zonas Objetivo: {renta_media_target:,.0f}€")
    print(f"   - Presión de Cuidados (Ratio Abuela/Hija): {presion_media_target:.2f}")
    print("     (Interpretación: Zonas de clase media-alta con altísima carga familiar)")

    print(f"\n[5. TOP 5 'OCÉANOS AZULES' (MAYOR VOLUMEN)]")
    # Ordenar por capacidad
    top_5 = viables.sort_values(by='Camas_Potenciales', ascending=False).head(5)
    
    for cid, row in top_5.iterrows():
        # Intentar sacar un nombre de municipio del df original si es posible
        ejemplo_seccion = df_ml[df_ml['Cluster_ID'] == cid].iloc[0]['Seccion']
        nombre_zona = " ".join(str(ejemplo_seccion).split(' ')[1:3]) # Hack para sacar nombre
        
        residencias_cluster = int(row['Camas_Potenciales'] / 100)
        print(f"   ★ Cluster {cid} ({nombre_zona}...): Capacidad para {residencias_cluster} Residencias.")

    print("\n==========================================================")
    print("FIN DEL INFORME. DATOS LISTOS PARA PRESENTACIÓN.")

if __name__ == "__main__":
    generar_informe_ejecutivo()
