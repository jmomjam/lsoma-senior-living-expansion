import pandas as pd
import os

# Ruta directa al archivo de 2022 (nuestro Ground Truth)
ruta = "/Users/cosotos/proyectos/akademia/casoprácticoIA/datos/Censo_muestra_2024.csv"

print(f"--- INSPECCIÓN PROFUNDA DE COLUMNAS (2022) ---")
try:
    # Leemos solo los encabezados
    df = pd.read_csv(ruta, sep='\t', nrows=1, encoding='latin-1')
    
    # Si falló el separador, probamos punto y coma
    if df.shape[1] == 1:
        df = pd.read_csv(ruta, sep=';', nrows=1, encoding='latin-1')

    columnas = list(df.columns)
    print(f"Total Columnas: {len(columnas)}")
    print("Nombres EXACTOS de las columnas:")
    print(columnas)
    
    # Verificación de viabilidad
    tiene_seccion = any("SEC" in c.upper() for c in columnas)
    if tiene_seccion:
        print("\n✅ ¡BUENAS NOTICIAS! La sección está ahí (quizás con nombre raro).")
    else:
        print("\n❌ MALAS NOTICIAS: No hay datos de sección censal en este archivo.")
        print("SOLUCIÓN: Debemos descargar el 'Fichero de Resultados Detallados' (Tabla agregada) en lugar de Microdatos individuales.")

except Exception as e:
    print(f"Error: {e}")
