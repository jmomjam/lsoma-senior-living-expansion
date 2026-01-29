import pandas as pd
import os

# --- CONFIGURACIÓN ---
ARCHIVO_GEO = "../datos/Datos caso práctico 2025 - renta y localizacion.xlsx" 

def espiar_excel_geo():
    print("--- DIAGNÓSTICO DE COORDENADAS ---")
    
    if not os.path.exists(ARCHIVO_GEO):
        print(f"❌ No encuentro el archivo: {ARCHIVO_GEO}")
        print("   Asegúrate de que está en la carpeta 'datos'.")
        return

    try:
        # Leemos solo la cabecera (header) para ir rápido
        df = pd.read_excel(ARCHIVO_GEO, nrows=5)
        
        print(f"✅ Archivo leído correctamente.")
        print("\n--- COLUMNAS DISPONIBLES ---")
        for col in df.columns:
            # Mostramos el nombre y un ejemplo de valor
            ejemplo = df[col].iloc[0]
            print(f"   📄 '{col}'  (Ej: {ejemplo})")
            
        print("\n----------------------------")
        print("BUSCA ALGO COMO: 'Lat', 'Lon', 'X_COORD', 'Y_COORD', 'Georef'...")
        
    except Exception as e:
        print(f"❌ Error leyendo el Excel: {e}")

if __name__ == "__main__":
    espiar_excel_geo()
