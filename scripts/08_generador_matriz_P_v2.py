import pandas as pd
import numpy as np
import os
import gc

# --- CONFIGURACIÓN ---
DIR_PROCESSED = "../datos/processed"
ARCHIVO_CENSO = "../datos/2021-2025.csv"
ARCHIVO_TARGET = "../datos/target_vector_Q.csv"
OUTPUT_MATRIZ = "../datos/matriz_P_nacional_filtrada.parquet"
UMBRAL_POBLACION_MINIMA = 400 

def limpiar_numero_espanol(serie):
    """Limpia formatos '1.234' a float de forma segura (regex=False)."""
    s = serie.astype(str)
    s = s.str.replace('.', '', regex=False)
    s = s.str.replace(',', '.', regex=False)
    return pd.to_numeric(s, errors='coerce').fillna(0)

def generar_matriz_estado_v4():
    print("--- FASE 2: GENERACIÓN DE MATRIZ P (V4 - SANITIZACIÓN ESTRICTA) ---")
    
    # 1. CARGAR MOLDE Q
    print(">>> Cargando Molde Q...")
    df_target = pd.read_csv(ARCHIVO_TARGET, sep=';')
    cols_hombres = [f"H_{rango}" for rango in df_target['Rango_Edad']]
    cols_mujeres = [f"M_{rango}" for rango in df_target['Rango_Edad']]
    COLUMNAS_ESPERADAS = cols_hombres + cols_mujeres
    print(f"   Esperamos {len(COLUMNAS_ESPERADAS)} columnas (Ej: {COLUMNAS_ESPERADAS[:3]})")
    
    # 2. CARGAR CENSO
    print(">>> Cargando Datos Crudos Censo...")
    try:
        df = pd.read_csv(ARCHIVO_CENSO, sep='\t', dtype=str, usecols=['Secciones', 'Sexo', 'Edad', 'Periodo', 'Total'])
        
        # Filtro Año
        anio_target = '2025'
        if anio_target not in df['Periodo'].unique(): anio_target = '2024'
        df = df[df['Periodo'] == anio_target].copy()
        print(f"   Usando año: {anio_target}")

        # Filtro Secciones vacías
        df = df.dropna(subset=['Secciones'])
        
        # --- DIAGNÓSTICO DE VALORES ÚNICOS (ANTES DE FILTRAR) ---
        print(f"   [DEBUG] Valores únicos en columna 'Sexo' encontrados: {df['Sexo'].unique()}")
        
        # SANITIZACIÓN DE TEXTO (TRIM)
        # Quitamos espacios delante y detrás que puedan romper el filtro
        df['Sexo'] = df['Sexo'].str.strip()
        df['Edad'] = df['Edad'].str.strip()
        
        # EXCLUIR REGISTROS AGREGADOS "Todas las edades"
        # Estos contienen la suma de todos los rangos y duplicarían los datos
        df = df[~df['Edad'].str.contains('Todas las edades', case=False, na=False)]
        
        # Filtro de Sexo ESTRICTO (Excluyendo 'Total' y 'Ambos Sexos')
        # Nos quedamos solo con lo que empiece por H o M (Hombres, Mujeres)
        df = df[df['Sexo'].isin(['Hombres', 'Mujeres'])]
        
        # Limpieza Numérica
        df['Total_Clean'] = limpiar_numero_espanol(df['Total'])
        
        # CHECK DE POBLACIÓN (Debe ser ~47M, no 98M)
        poblacion_raw = df['Total_Clean'].sum()
        print(f"   [CHECK] Población procesada: {poblacion_raw:,.0f}")
        
        if poblacion_raw > 60000000:
            print("❌ ALERTA: Seguimos duplicando datos. Revisa los valores únicos de Sexo arriba.")
            # Parada de emergencia para no procesar basura
            return

        # 3. CONSTRUCCIÓN DE CLAVES
        print(">>> Construyendo Claves Vectoriales...")
        
        # Limpieza de Edad: Transformar "De X a Y años" → "X-Y" para coincidir con Target Q
        # Ejemplos: "De 0 a 4 años" → "0-4", "De 85 a 89 años" → "85-89", "100 y más años" → "100 y más"
        df['Edad_Clean'] = (df['Edad']
            .str.replace(' años', '', regex=False)
            .str.replace('De ', '', regex=False)
            .str.replace(' a ', '-', regex=False)
            .str.strip()
        )
        
        # Mapeo Sexo
        sexo_map = {'Hombres': 'H', 'Mujeres': 'M'}
        df['Sexo_Short'] = df['Sexo'].map(sexo_map)
        
        # Construir Columna
        df['Columna_Vector'] = df['Sexo_Short'] + "_" + df['Edad_Clean']
        
        # --- DIAGNÓSTICO DE CLAVES ---
        claves_generadas = set(df['Columna_Vector'].unique())
        claves_esperadas = set(COLUMNAS_ESPERADAS)
        
        # Verificamos si coinciden
        interseccion = claves_generadas.intersection(claves_esperadas)
        print(f"   [DEBUG] Claves generadas en datos: {len(claves_generadas)} (Ej: {list(claves_generadas)[:3]})")
        print(f"   [DEBUG] Coincidencias con Target Q: {len(interseccion)} de {len(claves_esperadas)}")
        
        if len(interseccion) == 0:
            print("❌ ERROR FATAL: Las columnas generadas NO coinciden con las del Vector Q.")
            print("   Diferencia (Ejemplo):")
            print(f"   Esperado: {list(claves_esperadas)[:3]}")
            print(f"   Encontrado: {list(claves_generadas)[:3]}")
            return

        # 4. PIVOT TABLE
        print(">>> Pivotando Tabla...")
        matriz_P = df.pivot_table(index='Secciones', columns='Columna_Vector', values='Total_Clean', aggfunc='sum', fill_value=0)
        
        # Asegurar columnas
        for col in COLUMNAS_ESPERADAS:
            if col not in matriz_P.columns: matriz_P[col] = 0.0
        matriz_P = matriz_P[COLUMNAS_ESPERADAS]
        
        # 5. FILTRO ANTI-RUIDO
        print(f">>> Aplicando Filtro Anti-Ruido ({UMBRAL_POBLACION_MINIMA} hab)...")
        poblacion_seccion = matriz_P.sum(axis=1)
        
        print(f"   [CHECK] Población media por sección: {poblacion_seccion.mean():.2f}")
        
        matriz_P_filtrada = matriz_P[poblacion_seccion >= UMBRAL_POBLACION_MINIMA].copy()
        
        print(f"   ✅ Secciones Finales: {len(matriz_P_filtrada):,.0f} de {len(matriz_P):,.0f}")
        
        if len(matriz_P_filtrada) > 0:
            # 6. NORMALIZACIÓN Y GUARDADO
            poblacion_fiable = poblacion_seccion[poblacion_seccion >= UMBRAL_POBLACION_MINIMA]
            matriz_PDF = matriz_P_filtrada.div(poblacion_fiable, axis=0).fillna(0)
            matriz_PDF['Poblacion_Total'] = poblacion_fiable
            
            matriz_PDF.to_parquet(OUTPUT_MATRIZ)
            print(f"✅ EXITO. Matriz guardada en {OUTPUT_MATRIZ}")
        else:
            print("❌ El filtro eliminó todo. Revisa el [CHECK] de Población media.")

    except Exception as e:
        print(f"❌ Error Fatal: {e}")

if __name__ == "__main__":
    generar_matriz_estado_v4()
