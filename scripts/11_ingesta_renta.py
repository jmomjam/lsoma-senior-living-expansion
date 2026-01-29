import pandas as pd
import numpy as np
import os

# --- CONFIGURACIÓN ---
ARCHIVO_RANKING = "../datos/ranking_fase3_resonancia.csv"
ARCHIVO_RENTA = "../datos/renta2023.csv"
OUTPUT_FINAL = "../datos/ranking_fase4_completo.csv"

# Parámetros de Negocio
RENTA_MINIMA_VIABLE = 25000  # Umbral suave: debajo de esto, el score cae mucho
INDICADOR_OBJETIVO = "Renta neta media por hogar"
ANIO_OBJETIVO = 2023

def limpiar_numero_espanol(serie):
    """Convierte '46.939' (str) a 46939.0 (float)"""
    s = serie.astype(str)
    s = s.str.replace('.', '', regex=False)
    s = s.str.replace(',', '.', regex=False)
    return pd.to_numeric(s, errors='coerce')

def fusionar_tensor_economico():
    print("--- FASE 4: FUSIÓN DE TENSOR ECONÓMICO (RENTA 2023) ---")
    
    # 1. CARGAR RANKING DEMOGRÁFICO
    print(">>> Cargando Ranking de Resonancia...")
    if not os.path.exists(ARCHIVO_RANKING):
        print("❌ Error: No encuentro ranking_fase3_resonancia.csv")
        return
    df_rank = pd.read_csv(ARCHIVO_RANKING, sep=';')
    print(f"   Candidatos demográficos: {len(df_rank):,.0f}")
    
    # 2. CARGAR DATOS DE RENTA
    print(">>> Cargando Renta 2023...")
    try:
        # El INE suele usar ';' o tabuladores. Probamos ';' primero por ser CSV.
        # Si falla, el script avisará.
        df_renta = pd.read_csv(ARCHIVO_RENTA, sep=';', dtype=str)
        
        # Si leyó todo en una columna, probamos con tabulador
        if df_renta.shape[1] < 3:
            df_renta = pd.read_csv(ARCHIVO_RENTA, sep='\t', dtype=str)
            
        print(f"   Filas crudas renta: {len(df_renta):,.0f}")
        print(f"   Columnas: {df_renta.columns.tolist()}")
        
        # Normalizamos nombres de columnas (quita espacios extra)
        df_renta.columns = [c.strip() for c in df_renta.columns]
        
        # FILTRO 1: Descartar filas sin Sección (Totales municipales)
        # Buscamos la columna 'Secciones'. Si está vacía, fuera.
        if 'Secciones' not in df_renta.columns:
            print("❌ Error: No encuentro la columna 'Secciones'. Revisa el CSV.")
            return
            
        df_renta = df_renta.dropna(subset=['Secciones'])
        
        # FILTRO 2: Año y Tipo de Renta
        # Columna 'Periodo' y 'Indicadores de renta media' (según tus fotos)
        df_renta = df_renta[
            (df_renta['Periodo'].astype(str) == str(ANIO_OBJETIVO)) & 
            (df_renta['Indicadores de renta media'] == INDICADOR_OBJETIVO)
        ].copy()
        
        print(f"   Filas filtradas ({INDICADOR_OBJETIVO} - {ANIO_OBJETIVO}): {len(df_renta):,.0f}")
        
        if len(df_renta) == 0:
            print("❌ ALERTA: El filtro devolvió 0 filas. Revisa si el nombre del indicador es exacto.")
            # Intento de ayuda: imprimir únicos
            # print(df_renta_raw['Indicadores de renta media'].unique())
            return

        # 3. EXTRACCIÓN DE CÓDIGOS (LA LLAVE MAESTRA)
        print(">>> Estandarizando Códigos INE...")
        
        # En Renta: "0100201002 Amurrio..." -> "0100201002"
        # Cogemos la primera palabra (el número)
        df_renta['CUSEC'] = df_renta['Secciones'].astype(str).str.split(' ').str[0]
        
        # En Ranking: "3120104001 Pamplona..." -> "3120104001"
        df_rank['CUSEC'] = df_rank['Seccion'].astype(str).str.split(' ').str[0]
        
        # Limpieza del valor de Renta
        df_renta['Renta_Hogar'] = limpiar_numero_espanol(df_renta['Total'])
        
        # 4. CRUCE (MERGE)
        print(">>> Cruzando Demografía (P) con Economía (E)...")
        
        # Hacemos merge usando el código CUSEC
        df_final = pd.merge(df_rank, df_renta[['CUSEC', 'Renta_Hogar']], on='CUSEC', how='left')
        
        # Rellenar Renta faltante con 0 (para que se vayan al fondo del ranking)
        df_final['Renta_Hogar'] = df_final['Renta_Hogar'].fillna(0)
        
        # 5. CÁLCULO DEL SCORE DE NEGOCIO (L-SOMA)
        print(">>> Calculando L-SOMA Score...")
        
        # Factor Económico: Logarítmico para suavizar
        # Si Renta < 25k, penaliza mucho. Si es > 40k, bonifica.
        # +1 para evitar log(0)
        df_final['Log_Renta'] = np.log10(df_final['Renta_Hogar'] + 1)
        
        # Score = Resonancia * (Log_Renta / Log_Ref)
        # Log(35.000) approx 4.54
        # Normalizamos dividiendo por un valor de referencia razonable (ej 5.0 que es 100k)
        df_final['Factor_Econ'] = df_final['Log_Renta'] / 5.0
        
        # PENALIZACIÓN DURA (Hard Cutoff)
        # Si la renta es menor a RENTA_MINIMA_VIABLE (25k), el score se reduce a la mitad
        # Porque aunque haya viejos, no pagarán la cuota.
        df_final['Castigo_Pobreza'] = np.where(df_final['Renta_Hogar'] < RENTA_MINIMA_VIABLE, 0.5, 1.0)
        
        df_final['LSOMA_Score'] = df_final['Resonancia'] * df_final['Factor_Econ'] * df_final['Castigo_Pobreza']
        
        # Ordenar
        df_final = df_final.sort_values(by='LSOMA_Score', ascending=False)
        
        # Guardar
        df_final.to_csv(OUTPUT_FINAL, sep=';', index=False)
        print(f"✅ FINALIZADO. Ranking Completo guardado en {OUTPUT_FINAL}")
        
        # 6. VISUALIZACIÓN DEL TESORO
        print("\n--- TOP 15 OPORTUNIDADES DE NEGOCIO (EL MAPA DEL TESORO) ---")
        cols_show = ['Seccion', 'Resonancia', 'Renta_Hogar', 'LSOMA_Score']
        print(df_final[cols_show].head(15).to_string(index=False))
        
        # Estadística
        ricos = len(df_final[df_final['Renta_Hogar'] > 40000])
        print(f"\n[INSIGHT] Secciones con Renta > 40.000€: {ricos} de {len(df_final)}")

    except Exception as e:
        print(f"❌ Error Fatal: {e}")

if __name__ == "__main__":
    fusionar_tensor_economico()
