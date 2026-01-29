import pandas as pd
import os

# --- CONFIGURACIÓN OBLIGATORIA ---
# Pon aquí el nombre exacto del archivo descomprimido (el de 1.64 GB)
# Ejemplo: "../datos/censo_2022/nombre_del_archivo_gigante.csv"
RUTA_ARCHIVO = "/Users/cosotos/proyectos/akademia/casoprácticoIA/datos/2021-2025.csv" 

def inspeccionar_monstruo():
    print(f"--- INICIANDO BIOPSIA DEL ARCHIVO GIGANTE ---")
    print(f"Objetivo: {RUTA_ARCHIVO}")
    
    if not os.path.exists(RUTA_ARCHIVO):
        print("❌ ERROR: No encuentro el archivo. Revisa la ruta en el script.")
        return

    try:
        # 1. Detectar el separador automáticamente probando la primera línea
        with open(RUTA_ARCHIVO, 'r', encoding='utf-8') as f:
            primera_linea = f.readline()
            
        print(f"\n[Muestra cruda de la línea 1]:\n{primera_linea.strip()}")
        
        separador = ';' if ';' in primera_linea else '\t'
        if ',' in primera_linea and separador == '\t': separador = ','
        
        print(f"   -> Separador detectado: '{separador}' (Código ASCII: {ord(separador)})")

        # 2. Leer solo 5 filas con Pandas
        print("\nCargando primeras 5 filas...")
        df = pd.read_csv(RUTA_ARCHIVO, sep=separador, nrows=5, encoding='utf-8', low_memory=False)
        
        # 3. Reporte de Columnas
        cols = list(df.columns)
        print(f"\n✅ LECTURA EXITOSA.")
        print(f"   -> Número de Columnas: {len(cols)}")
        print(f"   -> Nombres de Columnas:\n      {cols}")
        
        # 4. Verificación de nuestras Variables Críticas (Vector Q)
        # Buscamos algo que suene a "Seccion", "Sexo", "Edad"
        cols_upper = [c.upper() for c in cols]
        
        tiene_secc = any("SEC" in c or "CUSEC" in c for c in cols_upper)
        tiene_sexo = any("SEX" in c for c in cols_upper)
        tiene_edad = any("EDA" in c or "GRUPO" in c for c in cols_upper)
        tiene_valor = any("TOTAL" in c or "VALOR" in c or "POB" in c for c in cols_upper)
        
        print("\n--- DIAGNÓSTICO DEL FÍSICO ---")
        print(f"   1. ¿Tiene Sección Censal?: {'SI ✅' if tiene_secc else 'NO ❌'}")
        print(f"   2. ¿Tiene Sexo?:           {'SI ✅' if tiene_sexo else 'NO ❌'}")
        print(f"   3. ¿Tiene Edad?:           {'SI ✅' if tiene_edad else 'NO ❌'}")
        print(f"   4. ¿Tiene el Dato (Valor)?:{'SI ✅' if tiene_valor else 'NO ❌'}")
        
        if tiene_secc and tiene_sexo and tiene_edad:
            print("\nCONCLUSIÓN: ✅ ESTE ES EL ARCHIVO CORRECTO (GOLDEN DATASET).")
            print("Podemos proceder a la Fase 2 (Ingesta y Filtrado).")
        else:
            print("\nCONCLUSIÓN: ⚠️ Faltan variables. Pega el resultado para que yo lo analice.")

        # 5. Muestra de datos
        print("\n[VISTA PREVIA DE DATOS]")
        print(df.head(3).to_string())

    except UnicodeDecodeError:
        print("❌ Error de codificación: Intenta cambiar encoding='utf-8' por 'latin-1' en el script.")
    except Exception as e:
        print(f"❌ Error fatal: {e}")

if __name__ == "__main__":
    inspeccionar_monstruo()
