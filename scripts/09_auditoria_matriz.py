import pandas as pd
import numpy as np
import os

# --- CONFIGURACIÓN ---
ARCHIVO_TARGET = "../datos/target_vector_Q.csv"
ARCHIVO_MATRIZ = "../datos/matriz_P_nacional_filtrada.parquet"

def auditar_matriz():
    print("--- FASE 2.5: AUDITORÍA FORENSE DE LA MATRIZ P ---")
    
    # 1. CARGAR DATOS
    print(">>> Cargando archivos...")
    if not os.path.exists(ARCHIVO_MATRIZ):
        print(f"❌ ERROR: No existe el archivo {ARCHIVO_MATRIZ}. Ejecuta el script 08 primero.")
        return

    df_target = pd.read_csv(ARCHIVO_TARGET, sep=';')
    try:
        df_matriz = pd.read_parquet(ARCHIVO_MATRIZ)
    except Exception as e:
        print(f"❌ ERROR leyendo Parquet: {e}")
        return

    print(f"   Matriz cargada. Dimensiones: {df_matriz.shape[0]} Secciones x {df_matriz.shape[1]} Columnas")

    # 2. AUDITORÍA DE DIMENSIONES (ESTRUCTURA)
    print("\n>>> 1. Verificación de Estructura Vectorial...")
    cols_hombres = [f"H_{rango}" for rango in df_target['Rango_Edad']]
    cols_mujeres = [f"M_{rango}" for rango in df_target['Rango_Edad']]
    COLUMNAS_ESPERADAS = cols_hombres + cols_mujeres
    
    # Extraemos las columnas de la matriz que NO son metadatos (quitamos Poblacion_Total)
    cols_matriz = [c for c in df_matriz.columns if c != 'Poblacion_Total']
    
    if set(cols_matriz) == set(COLUMNAS_ESPERADAS):
        print(f"   ✅ ESTRUCTURA CORRECTA: Las 42 dimensiones coinciden con el Vector Q.")
    else:
        print(f"   ❌ ERROR DE ESTRUCTURA: Las columnas no coinciden.")
        faltantes = set(COLUMNAS_ESPERADAS) - set(cols_matriz)
        sobrantes = set(cols_matriz) - set(COLUMNAS_ESPERADAS)
        print(f"      Faltan: {list(faltantes)[:5]}...")
        print(f"      Sobran: {list(sobrantes)[:5]}...")

    # 3. AUDITORÍA DE MASA (POBLACIÓN)
    print("\n>>> 2. Verificación de Masa (Población)...")
    if 'Poblacion_Total' in df_matriz.columns:
        poblacion_total = df_matriz['Poblacion_Total'].sum()
        print(f"   Población Total Representada: {poblacion_total:,.0f}")
        
        # En 2025 esperamos ~48.6M. Si filtramos secciones pequeñas (<400), bajará un poco (quizás a 45-46M).
        if 40000000 <= poblacion_total <= 50000000:
            print("   ✅ MASA COHERENTE: La población está en el rango esperado (España).")
        else:
            print("   ⚠️ ALERTA DE MASA: La población total es sospechosa (demasiado alta o baja).")
            print("      Nota: Si es <40M, el filtro de 400 hab puede haber sido muy agresivo.")
    else:
        print("   ❌ ERROR: No se encuentra la columna 'Poblacion_Total'.")

    # 4. AUDITORÍA DE PROBABILIDAD (TERMODINÁMICA)
    print("\n>>> 3. Verificación de Probabilidades (Suma=1)...")
    # Sumamos solo las columnas de vectores (excluyendo metadatos)
    suma_probs = df_matriz[cols_matriz].sum(axis=1)
    media_suma = suma_probs.mean()
    min_suma = suma_probs.min()
    max_suma = suma_probs.max()
    
    print(f"   Suma media de filas: {media_suma:.6f}")
    print(f"   Rango: [{min_suma:.6f} - {max_suma:.6f}]")
    
    # Permitimos un error infinitesimal por punto flotante (0.99999 - 1.00001)
    if 0.99 < media_suma < 1.01:
        print("   ✅ NORMALIZACIÓN CORRECTA: Las secciones son funciones de densidad válidas.")
    else:
        print("   ❌ ERROR MATEMÁTICO: Las filas no suman 1. Revisa la normalización.")

    print("\n--- CONCLUSIÓN DE LA AUDITORÍA ---")
    if (0.99 < media_suma < 1.01) and (40000000 <= poblacion_total <= 50000000) and (set(cols_matriz) == set(COLUMNAS_ESPERADAS)):
        print("🟢 SISTEMA ESTABLE. PROCEDIENDO A FASE 3.")
    else:
        print("🔴 SISTEMA INESTABLE. NO AVANZAR.")

if __name__ == "__main__":
    auditar_matriz()
