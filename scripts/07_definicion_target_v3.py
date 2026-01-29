import pandas as pd
import numpy as np

# --- CONFIGURACIÓN ---
BINS_EDAD = [
    '0-4', '5-9', '10-14', '15-19', '20-24', '25-29', '30-34', '35-39',
    '40-44', '45-49', '50-54', '55-59', '60-64', '65-69', '70-74',
    '75-79', '80-84', '85-89', '90-94', '95-99', '100 y más'
]

def crear_vector_objetivo_realista():
    print("--- FASE 1 (RECALIBRACIÓN): VECTOR Q REALISTA (BARRIO, NO RESIDENCIA) ---")
    
    df_target = pd.DataFrame({'Rango_Edad': BINS_EDAD})
    
    # --- NUEVA LÓGICA DE PESOS (CORRECCIÓN DE RESONANCIA) ---
    # Ya no usamos 0.001 para jóvenes. Aceptamos que un barrio "Ideal"
    # tiene una estructura demográfica base, pero muy distorsionada hacia la vejez.
    
    pesos_edad = {
        # RUIDO DE FONDO (Población activa necesaria)
        # Peso 0.15 permite que existan sin penalizar demasiado la divergencia
        '0-59': 0.15,
        
        # TRANSICIÓN (Jubilados activos)
        # Peso 0.5 indica que esperamos ver bastantes, es la "cantera" de clientes
        '60-74': 0.5,
        
        # LA RAMPA (Fragilidad incipiente)
        '75-79': 1.0,
        
        # EL TARGET (La Anomalía que buscamos)
        # Peso 4.0 hace que el algoritmo "grite" cuando ve a estos grupos
        '80-84': 4.0,   
        '85-89': 5.0,   
        '90-94': 5.0,
        '95-99': 5.0,
        '100 y más': 5.0
    }
    
    # Mantenemos la feminización (Soledad)
    FACTOR_FEMINIZACION = 1.3 
    
    vector_hombres = []
    vector_mujeres = []
    
    for bin in BINS_EDAD:
        if '100' in bin:
            edad_min = 100
        else:
            edad_min = int(bin.split('-')[0])
            
        # Asignación de pesos suavizada
        if edad_min < 60: peso = pesos_edad['0-59']
        elif 60 <= edad_min <= 74: peso = pesos_edad['60-74']
        elif 75 <= edad_min <= 79: peso = pesos_edad['75-79']
        elif 80 <= edad_min <= 84: peso = pesos_edad['80-84']
        else: peso = 5.0 # 85+ (Explosión de peso)
        
        vector_hombres.append(peso)
        vector_mujeres.append(peso * FACTOR_FEMINIZACION)

    df_target['Peso_Hombres'] = vector_hombres
    df_target['Peso_Mujeres'] = vector_mujeres
    
    # --- NORMALIZACIÓN ---
    total_masa = df_target['Peso_Hombres'].sum() + df_target['Peso_Mujeres'].sum()
    df_target['Prob_Hombres'] = df_target['Peso_Hombres'] / total_masa
    df_target['Prob_Mujeres'] = df_target['Peso_Mujeres'] / total_masa
    
    # Guardamos (Sobrescribimos el archivo anterior)
    ruta_salida = "../datos/target_vector_Q.csv"
    df_target.to_csv(ruta_salida, sep=';', index=False)
    
    print(f"✅ Vector Q Recalibrado guardado en {ruta_salida}")
    print("[VISUALIZACIÓN DE LA NUEVA ESTRUCTURA OBJETIVO]")
    
    # Mostramos la probabilidad real que esperamos encontrar
    # Observa cómo ahora los jóvenes tienen 'algo' de barra, y los viejos tienen 'mucha' barra
    vista = df_target[['Rango_Edad', 'Prob_Mujeres']]
    vista['Barra'] = vista['Prob_Mujeres'].apply(lambda x: '#' * int(x * 200)) 
    print(vista.to_string(index=False))

if __name__ == "__main__":
    crear_vector_objetivo_realista()
