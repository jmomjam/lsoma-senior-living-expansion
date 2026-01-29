import pandas as pd
import numpy as np
import os

# --- CONFIGURACIÓN ---
ARCHIVO_RANKING = "../datos/ranking_fase3_resonancia.csv"
ARCHIVO_RENTA = "../datos/renta2023.csv"
OUTPUT_FINAL = "../datos/ranking_fase4_refinado.csv"

# --- PARÁMETROS DE NEGOCIO (AJUSTADOS POR ANÁLISIS CRÍTICO) ---
RENTA_MINIMA_VIABLE = 30000   # Subimos de 25k a 30k (Seguridad de zona Premium)
RENTA_MAXIMA_OPTIMA = 65000   # A partir de aquí, el suelo es demasiado caro (Trampa CAPEX)
ANIO_OBJETIVO = 2023
INDICADOR_OBJETIVO = "Renta neta media por hogar"

def limpiar_numero_espanol(serie):
    """Convierte '46.939' a float"""
    s = serie.astype(str)
    s = s.str.replace('.', '', regex=False)
    s = s.str.replace(',', '.', regex=False)
    return pd.to_numeric(s, errors='coerce')

def refinar_oportunidades():
    print("--- FASE 4 (V2): REFINAMIENTO CON LÓGICA DE NEGOCIO ---")
    
    # 1. CARGA
    df_rank = pd.read_csv(ARCHIVO_RANKING, sep=';')
    
    # Carga de Renta (Reutilizamos la lógica del script anterior)
    try:
        df_renta = pd.read_csv(ARCHIVO_RENTA, sep=';', dtype=str)
        if df_renta.shape[1] < 3: df_renta = pd.read_csv(ARCHIVO_RENTA, sep='\t', dtype=str)
        
        df_renta.columns = [c.strip() for c in df_renta.columns]
        df_renta = df_renta.dropna(subset=['Secciones'])
        df_renta = df_renta[
            (df_renta['Periodo'].astype(str) == str(ANIO_OBJETIVO)) & 
            (df_renta['Indicadores de renta media'] == INDICADOR_OBJETIVO)
        ].copy()
        
        # Limpieza Códigos y Valor
        df_renta['CUSEC'] = df_renta['Secciones'].astype(str).str.split(' ').str[0]
        df_renta['Renta_Hogar'] = limpiar_numero_espanol(df_renta['Total'])
        
        df_rank['CUSEC'] = df_rank['Seccion'].astype(str).str.split(' ').str[0]
        
        # MERGE
        df_final = pd.merge(df_rank, df_renta[['CUSEC', 'Renta_Hogar']], on='CUSEC', how='left')
        df_final['Renta_Hogar'] = df_final['Renta_Hogar'].fillna(0) # Los huecos se van a 0
        
    except Exception as e:
        print(f"❌ Error cargando renta: {e}")
        return

    # 2. CÁLCULO DE SCORE AVANZADO (CURVA DE CAMPANA)
    print(">>> Aplicando Filtros de Viabilidad y Coste de Suelo...")
    
    # A. Factor Económico Base (Logarítmico)
    df_final['Log_Renta'] = np.log10(df_final['Renta_Hogar'] + 1)
    
    # B. Penalización por POBREZA (Riesgo de Impago / Zona no Premium)
    # Coeficiente sigmoide: cae rápido si baja de 30k
    df_final['Coef_Solvencia'] = np.where(df_final['Renta_Hogar'] < RENTA_MINIMA_VIABLE, 0.4, 1.0)
    
    # C. Penalización por LUJO (Riesgo de Suelo Caro / Competencia Imposible)
    # Si la renta supera 65k, penalizamos progresivamente
    # Alguien con 100k tendrá un coeficiente de 0.6 (prefiero uno de 50k)
    df_final['Coef_Suelo'] = np.where(df_final['Renta_Hogar'] > RENTA_MAXIMA_OPTIMA, 
                                      RENTA_MAXIMA_OPTIMA / df_final['Renta_Hogar'], 
                                      1.0)
    
    # SCORE FINAL
    # Score = (Biología) * (Economía Log) * (Filtro Pobreza) * (Filtro Lujo)
    df_final['LSOMA_Score'] = (df_final['Resonancia'] * (df_final['Log_Renta'] / 4.8) * # Normalizado a aprox 1.0 para 60k
                               df_final['Coef_Solvencia'] * df_final['Coef_Suelo'])
    
    # Ordenar
    df_final = df_final.sort_values(by='LSOMA_Score', ascending=False)
    
    # Guardar
    df_final.to_csv(OUTPUT_FINAL, sep=';', index=False)
    print(f"✅ Ranking Refinado guardado en {OUTPUT_FINAL}")
    
    # VISUALIZACIÓN
    print("\n--- TOP 15 'OCÉANOS AZULES' (DEMANDA ALTA + RENTA MEDIA-ALTA) ---")
    print(df_final[['Seccion', 'Resonancia', 'Renta_Hogar', 'LSOMA_Score']].head(15).to_string(index=False))
    
    # Check de los "Descartados"
    print("\n[CHECK] ¿Qué pasó con los barrios ultra-ricos?")
    ricos = df_final[df_final['Renta_Hogar'] > 80000].head(3)
    print(ricos[['Seccion', 'Resonancia', 'Renta_Hogar', 'LSOMA_Score']].to_string(index=False))

if __name__ == "__main__":
    refinar_oportunidades()
