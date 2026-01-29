import pandas as pd
import os

# --- CONFIGURACIÓN ---
ARCHIVO_SCORE_FINAL = "../datos/ranking_fase5_score_final.csv"
ARCHIVO_GEO = "../datos/Datos caso práctico 2025 - renta y localizacion.xlsx" 
OUTPUT_GEO_READY = "../datos/ranking_fase6_geo_ready.csv"

def inyectar_coordenadas():
    print("--- FASE 5.5: INYECCIÓN DE COORDENADAS PARA ML ---")
    
    # 1. CARGAR RANKING FINAL
    print(">>> Cargando Score Final...")
    if not os.path.exists(ARCHIVO_SCORE_FINAL):
        print("❌ Falta el archivo de la fase 5.")
        return
    df_score = pd.read_csv(ARCHIVO_SCORE_FINAL, sep=';')
    print(f"   Secciones en ranking: {len(df_score):,.0f}")
    
    # 2. CARGAR EXCEL GEO
    print(">>> Cargando Coordenadas...")
    try:
        # Leemos el Excel
        df_geo = pd.read_excel(ARCHIVO_GEO)
        
        # Seleccionamos solo lo útil y renombramos para estandarizar
        # Tus columnas detectadas: 'Seccion', 'latitud', 'longitud'
        df_geo = df_geo[['Seccion', 'latitud', 'longitud']].copy()
        df_geo.columns = ['CUSEC_GEO', 'LATITUD', 'LONGITUD']
        
        # --- CORRECCIÓN DEL CERO INICIAL (CRÍTICO) ---
        # Excel se come el cero de Álava (1001... en vez de 01001...)
        # Lo convertimos a string y le decimos: "Si tienes menos de 10 dígitos, pon ceros delante"
        df_geo['CUSEC_GEO'] = df_geo['CUSEC_GEO'].astype(str).str.zfill(10)
        
        print(f"   Coordenadas cargadas: {len(df_geo):,.0f}")
        print(f"   Ejemplo de código corregido: {df_geo['CUSEC_GEO'].iloc[0]}")
        
        # 3. PREPARAR RANKING PARA EL CRUCE
        # El ranking tiene "0100101001 Nombre..." -> Extraemos solo el código
        df_score['CUSEC_JOIN'] = df_score['Seccion'].astype(str).str.split(' ').str[0]
        
        # Aseguramos limpieza (quitar espacios)
        df_score['CUSEC_JOIN'] = df_score['CUSEC_JOIN'].str.strip()
        df_geo['CUSEC_GEO'] = df_geo['CUSEC_GEO'].str.strip()
        
        # 4. CRUCE (MERGE)
        print(">>> Cruzando tablas...")
        
        df_final = pd.merge(df_score, df_geo, 
                            left_on='CUSEC_JOIN', right_on='CUSEC_GEO', 
                            how='left')
        
        # 5. VALIDACIÓN
        con_coords = df_final.dropna(subset=['LATITUD', 'LONGITUD'])
        pct_exito = (len(con_coords) / len(df_final)) * 100
        
        print(f"   📍 Secciones geolocalizadas: {len(con_coords)} ({pct_exito:.1f}%)")
        
        if pct_exito < 80:
            print("⚠️ ALERTA: Muchas secciones se han quedado sin coordenadas. Revisa los códigos.")
        else:
            print("✅ Éxito masivo en la geolocalización.")

        # Limpieza final (borramos columnas auxiliares)
        if 'CUSEC_GEO' in df_final.columns: del df_final['CUSEC_GEO']
        if 'CUSEC_JOIN' in df_final.columns: del df_final['CUSEC_JOIN']
        
        # Guardar
        df_final.to_csv(OUTPUT_GEO_READY, sep=';', index=False)
        print(f"✅ ARCHIVO LISTO PARA ML: {OUTPUT_GEO_READY}")

    except Exception as e:
        print(f"❌ Error procesando Excel: {e}")

if __name__ == "__main__":
    inyectar_coordenadas()
