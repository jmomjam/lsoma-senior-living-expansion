import pandas as pd
import os
import glob

# --- CONFIGURACIÓN ---
DIR_RAW = "../datos/padron_raw"
DIR_PROCESSED = "../datos/processed"
ARCHIVO_CENSO = "../datos/2021-2025.csv"

def reparar_con_tabuladores():
    print("--- INICIANDO REPARACIÓN FORZADA (TABULADORES) ---")
    
    if not os.path.exists(DIR_PROCESSED):
        os.makedirs(DIR_PROCESSED)

    # 1. PROCESAR HISTÓRICO (2016-2020)
    carpetas_anio = sorted([f for f in os.listdir(DIR_RAW) if f.startswith("padron_")])
    
    for carpeta in carpetas_anio:
        anio = carpeta.split("_")[1]
        ruta_carpeta = os.path.join(DIR_RAW, carpeta)
        archivos_csv = glob.glob(os.path.join(ruta_carpeta, "*.csv"))
        
        if not archivos_csv: continue
        
        print(f"\n>>> Procesando Año {anio} con separador TABULADOR...")
        
        dfs = []
        for csv_file in archivos_csv:
            try:
                # FORZAMOS sep='\t' y dtype=str para no perder ceros iniciales en códigos postales/INE
                # Usamos encoding 'latin-1' que es el estándar de los ficheros antiguos del INE
                df = pd.read_csv(csv_file, sep='\t', encoding='latin-1', dtype=str)
                
                # Si falla y lee 1 sola columna, intentamos limpiar comillas
                if df.shape[1] < 2:
                    # Intento de fallback por si acaso no son tabs puros sino espacios raros
                    df = pd.read_csv(csv_file, sep=r'\s+', encoding='latin-1', dtype=str)
                
                dfs.append(df)
            except Exception as e:
                print(f"   ❌ Error en {os.path.basename(csv_file)}: {e}")
        
        if dfs:
            df_final = pd.concat(dfs, ignore_index=True)
            
            # Limpieza de nombres de columnas (quita espacios y comillas)
            df_final.columns = [c.strip().replace('"', '') for c in df_final.columns]
            
            # Guardamos YA PROCESADO con punto y coma (estándar CSV moderno) para evitar líos futuros
            ruta_salida = os.path.join(DIR_PROCESSED, f"padron_{anio}_nacional.csv")
            df_final.to_csv(ruta_salida, sep=';', index=False, encoding='utf-8')
            
            print(f"   ✅ GUARDADO: padron_{anio}_nacional.csv")
            print(f"      Dimensiones: {df_final.shape[0]} filas x {df_final.shape[1]} columnas")
            print(f"      Columnas detectadas: {list(df_final.columns)}")
            
            if df_final.shape[1] < 3:
                print("   ⚠️ ALERTA: Siguen saliendo pocas columnas. Verifica el archivo raw.")
        else:
            print(f"   ⚠️ No se encontraron datos válidos para {anio}")

    # 2. VERIFICAR EL GOLDEN DATASET (2021-2025)
    print(f"\n>>> Verificando Dataset 2021-2025 con TABULADORES...")
    if os.path.exists(ARCHIVO_CENSO):
        try:
            # Leemos solo 5 filas para verificar
            df_censo = pd.read_csv(ARCHIVO_CENSO, sep='\t', nrows=5, encoding='utf-8', dtype=str)
            
            print(f"   ✅ LECTURA EXITOSA.")
            print(f"      Columnas: {list(df_censo.columns)}")
            
            # Verificación de Variables Clave
            cols_upper = [c.upper() for c in df_censo.columns]
            tiene_seccion = any("SEC" in c for c in cols_upper)
            tiene_edad = any("EDA" in c or "GRUPO" in c for c in cols_upper)
            
            print(f"      Variables Clave presentes: {'SÍ' if (tiene_seccion and tiene_edad) else 'NO ❌'}")
            
        except Exception as e:
            print(f"   ❌ Error leyendo el Censo 2021-2025: {e}")
            print("      Prueba cambiando encoding='latin-1' si falla con utf-8.")
    else:
        print("   ❌ No se encuentra el archivo 2021-2025.csv")

if __name__ == "__main__":
    reparar_con_tabuladores()
