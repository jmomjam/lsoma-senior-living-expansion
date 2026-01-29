import pandas as pd
import numpy as np

# --- CONFIGURACIÓN ---
BINS_EDAD = [
    '0-4', '5-9', '10-14', '15-19', '20-24', '25-29', '30-34', '35-39',
    '40-44', '45-49', '50-54', '55-59', '60-64', '65-69', '70-74',
    '75-79', '80-84', '85-89', '90-94', '95-99', '100 y más'
]

def crear_vector_objetivo():
    print("--- FASE 1: DEFINICIÓN DEL VECTOR DE ESTADO OBJETIVO (Q) - GRADIENTE SUAVE ---")
    
    df_target = pd.DataFrame({'Rango_Edad': BINS_EDAD})
    
    # --- ASIGNACIÓN DE PESOS (SECCIÓN EFICAZ DE INGRESO) ---
    
    # AJUSTE BASADO EN TU FEEDBACK Y EL ESTUDIO:
    # - 75-79: Subimos peso a 0.3 (Demanda Latente / Inicio de fragilidad).
    # - 80-84: Zona Principal (Media 82 años).
    # - 85+: Zona Crítica (Pluripatología y Soledad).
    
    pesos_edad = {
        '0-69': 0.001,  # Ruido de fondo
        '70-74': 0.05,  # Pre-alerta muy baja
        '75-79': 0.3,   # RAMPA DE INGRESO (Tu corrección)
        '80-84': 0.9,   # ZONA CALIENTE (Media del mercado)
        '85-89': 1.0,   # ZONA CRÍTICA
        '90-94': 1.0,   # ZONA CRÍTICA
        '95-99': 1.0,   # ZONA CRÍTICA
        '100 y más': 1.0
    }
    
    # Factor de Feminizacion: 
    # Justificación: "Crisis de cuidados tiene rostro de mujer" y "Mayor esperanza de vida".
    FACTOR_FEMINIZACION = 1.3 
    
    vector_hombres = []
    vector_mujeres = []
    
    for bin in BINS_EDAD:
        if '100' in bin:
            edad_min = 100
        else:
            edad_min = int(bin.split('-')[0])
            
        # Lógica de asignación suave
        if edad_min < 70: peso = pesos_edad['0-69']
        elif 70 <= edad_min <= 74: peso = pesos_edad['70-74']
        elif 75 <= edad_min <= 79: peso = pesos_edad['75-79']
        elif 80 <= edad_min <= 84: peso = pesos_edad['80-84']
        else: peso = 1.0 # 85+
        
        vector_hombres.append(peso)
        vector_mujeres.append(peso * FACTOR_FEMINIZACION)

    df_target['Peso_Hombres'] = vector_hombres
    df_target['Peso_Mujeres'] = vector_mujeres
    
    # --- NORMALIZACIÓN ---
    total_masa = df_target['Peso_Hombres'].sum() + df_target['Peso_Mujeres'].sum()
    df_target['Prob_Hombres'] = df_target['Peso_Hombres'] / total_masa
    df_target['Prob_Mujeres'] = df_target['Peso_Mujeres'] / total_masa
    
    # Guardamos
    ruta_salida = "../datos/target_vector_Q.csv"
    df_target.to_csv(ruta_salida, sep=';', index=False)
    
    print(f"✅ Vector Q Generado en {ruta_salida}")
    print("[VISUALIZACIÓN DE LA RAMPA DE EDAD - PROBABILIDAD RELATIVA]")
    # Mostramos solo las columnas de probabilidad para ver el gradiente
    vista = df_target[['Rango_Edad', 'Prob_Mujeres']].tail(8)
    vista['Barra'] = vista['Prob_Mujeres'].apply(lambda x: '#' * int(x * 500)) # ASCII Art
    print(vista.to_string(index=False))

if __name__ == "__main__":
    crear_vector_objetivo()
