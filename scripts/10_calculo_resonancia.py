import pandas as pd
import numpy as np
import os
from scipy.spatial.distance import jensenshannon

# --- CONFIGURACIÓN ---
ARCHIVO_TARGET = "../datos/target_vector_Q.csv"
ARCHIVO_MATRIZ = "../datos/matriz_P_nacional_filtrada.parquet"
OUTPUT_RANKING = "../datos/ranking_fase3_resonancia.csv"

def calcular_resonancia():
    print("--- FASE 3: CÁLCULO DE RESONANCIA (JENSEN-SHANNON) ---")
    
    # 1. CARGA DE DATOS
    print(">>> Cargando Espacio de Fases...")
    df_target = pd.read_csv(ARCHIVO_TARGET, sep=';')
    df_matriz = pd.read_parquet(ARCHIVO_MATRIZ)
    
    # Separar Metadatos (Poblacion) de Datos Vectoriales
    poblacion = df_matriz['Poblacion_Total']
    df_vectores = df_matriz.drop(columns=['Poblacion_Total'])
    
    # 2. ALINEACIÓN VECTORIAL (CRÍTICO)
    # Construimos el vector Q en el MISMO orden exacto que las columnas de P
    print(">>> Alineando Vector Q con Matriz P...")
    
    # Mapa de columnas P -> Valores Q
    # P tiene columnas tipo "H_0-4", "M_85-89"
    # Q tiene filas con "Rango_Edad", "Prob_Hombres", "Prob_Mujeres"
    
    vector_Q_alineado = []
    col_names_P = df_vectores.columns.tolist()
    
    # Diccionarios de búsqueda rápida para Q
    q_hombres = dict(zip(df_target['Rango_Edad'], df_target['Prob_Hombres']))
    q_mujeres = dict(zip(df_target['Rango_Edad'], df_target['Prob_Mujeres']))
    
    for col in col_names_P:
        # col es tipo "H_0-4" o "M_100 y más"
        tipo, rango = col.split('_', 1) # Separar por el primer guion bajo
        
        if tipo == 'H':
            val = q_hombres.get(rango)
        elif tipo == 'M':
            val = q_mujeres.get(rango)
        else:
            print(f"❌ COLUMNA DESCONOCIDA: {col}")
            return
            
        if val is None:
            print(f"❌ RANGO NO ENCONTRADO EN Q: {rango} (Columna: {col})")
            return
            
        vector_Q_alineado.append(val)
    
    vector_Q_np = np.array(vector_Q_alineado)
    
    # Validación de Probabilidad Q
    print(f"   Suma Probabilidad Vector Q Alineado: {vector_Q_np.sum():.6f} (Debe ser 1.0)")
    
    # 3. CÁLCULO MASIVO (ALGEBRA LINEAL)
    print(">>> Calculando Divergencia JS para 32k secciones...")
    
    # Convertimos Matriz P a Numpy
    matriz_P_np = df_vectores.to_numpy()
    
    # Scipy jensenshannon calcula la distancia entre vectores
    # No soporta broadcasting directo, iteramos fila por fila
    distancias = np.apply_along_axis(lambda row: jensenshannon(row, vector_Q_np), axis=1, arr=matriz_P_np)
    
    # 4. TRANSFORMACIÓN A RESONANCIA (SCORE)
    # R = 1 - Distancia
    # La distancia JS va de 0 a 1 (log base 2)
    resonancias = 1.0 - distancias
    
    # 5. CREACIÓN DEL RANKING
    print(">>> Generando Ranking...")
    df_resultado = pd.DataFrame({
        'Seccion': df_matriz.index,
        'Resonancia': resonancias,
        'Poblacion_Total': poblacion
    })
    
    # Ordenar por Resonancia Descendente (Los mejores arriba)
    df_ranking = df_resultado.sort_values(by='Resonancia', ascending=False)
    
    # Guardar
    df_ranking.to_csv(OUTPUT_RANKING, sep=';', index=False)
    
    print(f"✅ CÁLCULO FINALIZADO. Ranking guardado en {OUTPUT_RANKING}")
    
    # 6. VISUALIZACIÓN TOP 10
    print("\n--- TOP 10 SECCIONES CON MAYOR RESONANCIA DEMOGRÁFICA ---")
    print(df_ranking.head(10).to_string(index=False))
    
    # Estadísticas Globales
    media = df_ranking['Resonancia'].mean()
    top_1pct = df_ranking['Resonancia'].quantile(0.99)
    print(f"\n[ESTADÍSTICAS NACIONALES]")
    print(f"   Resonancia Media: {media:.4f}")
    print(f"   Umbral del Top 1%: {top_1pct:.4f}")
    print(f"   (Las secciones por encima de {top_1pct:.4f} son tus 'Tier 1')")

if __name__ == "__main__":
    calcular_resonancia()
