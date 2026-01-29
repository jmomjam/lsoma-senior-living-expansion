import pandas as pd
import numpy as np
import os

# --- CONFIGURACIÓN ---
ARCHIVO_RANKING_PREVIO = "../datos/ranking_fase4_refinado.csv"
ARCHIVO_MATRIZ_P = "../datos/matriz_P_nacional_filtrada.parquet"
OUTPUT_FINAL = "../datos/ranking_fase5_score_final.csv"

def feature_engineering_disparadores():
    print("--- FASE 5: FEATURE ENGINEERING (DISPARADORES DE DECISIÓN) ---")
    
    # 1. CARGAR DATOS
    print(">>> Cargando Ranking Económico...")
    if not os.path.exists(ARCHIVO_RANKING_PREVIO):
        print("❌ Falta el archivo de la fase 4.")
        return
    df_rank = pd.read_csv(ARCHIVO_RANKING_PREVIO, sep=';')
    
    print(">>> Cargando Matriz Biológica (Parquet)...")
    # Necesitamos la matriz original para contar a las "Hijas" y "Abuelas" específicas
    df_matriz = pd.read_parquet(ARCHIVO_MATRIZ_P)
    
    # 2. DEFINICIÓN DE VARIABLES SOCIOLÓGICAS
    # A. La Generación Sándwich (Decisoras)
    # Rango: Mujeres 45-64 años
    cols_hijas = ['M_45-49', 'M_50-54', 'M_55-59', 'M_60-64']
    
    # B. La Soledad / Viudedad (Target Crítico)
    # Rango: Mujeres 80+ años
    cols_abuelas = ['M_80-84', 'M_85-89', 'M_90-94', 'M_95-99', 'M_100 y más']
    
    # Verificar que las columnas existen
    available_cols = df_matriz.columns.tolist()
    
    # Lógica segura para encontrar columnas (por si el nombre varía ligeramente)
    # Buscamos columnas que terminen con los rangos definidos
    final_cols_hijas = [c for c in available_cols if any(c.endswith(r) for r in cols_hijas)]
    final_cols_abuelas = [c for c in available_cols if any(c.endswith(r) for r in cols_abuelas)]
    
    print(f"   Columnas Decisoras detectadas: {len(final_cols_hijas)}")
    print(f"   Columnas Target detectadas: {len(final_cols_abuelas)}")
    
    # 3. CÁLCULO DE DENSIDADES (PRESIÓN SOCIAL)
    print(">>> Calculando Tensores de Presión (Burnout)...")
    
    # Suma de probabilidades (Como la matriz es PDF, esto nos da el % de población en ese grupo)
    df_matriz['Ratio_Hijas'] = df_matriz[final_cols_hijas].sum(axis=1)
    df_matriz['Ratio_Abuelas'] = df_matriz[final_cols_abuelas].sum(axis=1)
    
    # Ratio de Dependencia Local (Carga de Cuidados)
    # Cuántas Abuelas hay por cada Hija en el mismo barrio
    # Si este número es alto, el burnout es inminente.
    # Sumamos un epsilon (0.001) para evitar división por cero
    df_matriz['Presion_Cuidados'] = df_matriz['Ratio_Abuelas'] / (df_matriz['Ratio_Hijas'] + 0.001)
    
    # 4. FUSIÓN CON RANKING
    print(">>> Fusionando variables con el Score Económico...")
    
    # El índice de df_matriz es la Sección (string completo o código). 
    # En df_rank tenemos 'Seccion' y 'CUSEC'. 
    # Vamos a usar el índice de la matriz para cruzar con la columna 'Seccion' del ranking.
    
    # Preparamos subset de la matriz
    df_features = df_matriz[['Ratio_Hijas', 'Ratio_Abuelas', 'Presion_Cuidados']].copy()
    
    # Merge
    df_final = pd.merge(df_rank, df_features, left_on='Seccion', right_index=True, how='left')
    df_final = df_final.fillna(0)
    
    # 5. CÁLCULO DEL SCORE L-SOMA FINAL
    # Formula Maestra basada en tu input de Fase 5
    # Score = (Base Económica) * (Factor Burnout)
    
    # Normalizamos la Presión de Cuidados para que actúe como multiplicador
    # La media nacional de presión servirá de base 1.0
    media_presion = df_final['Presion_Cuidados'].mean()
    df_final['Factor_Burnout'] = df_final['Presion_Cuidados'] / media_presion
    
    # Capamos el factor para que no distorsione locamente (Max x1.5 boost)
    df_final['Factor_Burnout'] = df_final['Factor_Burnout'].clip(0.5, 1.5)
    
    # SCORE DEFINITIVO
    # LSOMA_Score (Fase 4) ya incluía Resonancia y Renta.
    # Ahora le inyectamos la variable "Hija Saturada".
    df_final['Score_Global'] = df_final['LSOMA_Score'] * df_final['Factor_Burnout']
    
    # Ordenar
    df_final = df_final.sort_values(by='Score_Global', ascending=False)
    
    # Guardar
    df_final.to_csv(OUTPUT_FINAL, sep=';', index=False)
    print(f"✅ SCORE FINAL CALCULADO. Guardado en {OUTPUT_FINAL}")
    
    # 6. RESULTADOS FINALES
    print("\n--- TOP 15 FINAL: LAS ZONAS DE MÁXIMA OPORTUNIDAD ---")
    cols_show = ['Seccion', 'Renta_Hogar', 'Ratio_Hijas', 'Presion_Cuidados', 'Score_Global']
    # Formato amigable
    pd.options.display.float_format = '{:,.3f}'.format
    print(df_final[cols_show].head(15).to_string(index=False))
    
    print("\n[GLOSARIO]")
    print("   Ratio_Hijas: % de mujeres 45-64 en el barrio.")
    print("   Presion_Cuidados: Abuelas dependientes por cada Hija potencial.")
    print("   Score_Global: La métrica final de idoneidad.")

if __name__ == "__main__":
    feature_engineering_disparadores()
