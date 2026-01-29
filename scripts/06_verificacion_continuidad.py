import pandas as pd
import os
import matplotlib.pyplot as plt

# --- CONFIGURACIÓN ---
DIR_PROCESSED = "../datos/processed"
ARCHIVO_CENSO = "../datos/2021-2025.csv"


def limpiar_numero_espanol(serie):
    """Convierte '1.234.567' a float."""
    s = serie.astype(str)
    s = s.str.replace('.', '', regex=False)
    s = s.str.replace(',', '.', regex=False)
    return pd.to_numeric(s, errors='coerce')

def verificacion_final():
    print("--- FASE 2: VERIFICACIÓN FINAL (FILTROS MATRIOSHKA) ---")
    
    series_temporales = []

    # 1. PROCESAR MUNDO ANTIGUO (2016-2020)
    print(">>> Procesando Histórico (Padrón)...")
    archivos = sorted([f for f in os.listdir(DIR_PROCESSED) if f.startswith("padron_")])
    
    for f in archivos:
        anio = f.split("_")[1]
        ruta = os.path.join(DIR_PROCESSED, f)
        
        try:
            # Leemos todo como string
            df = pd.read_csv(ruta, sep=';', dtype=str, low_memory=False)
            
            # Detectar columnas (limpiando basura UTF-8 si existe)
            col_edad = [c for c in df.columns if 'Edad' in c or 'edad' in c][0]
            col_total = [c for c in df.columns if 'Total' in c or 'total' in c][0]
            col_sexo = [c for c in df.columns if 'Sexo' in c or 'sexo' in c][0]
            col_secc = [c for c in df.columns if 'Secc' in c or 'secc' in c][0]
            
            # --- APLICACIÓN DE FILTROS SEGÚN TUS IMÁGENES ---
            
            # 1. Filtro Geográfico: ELIMINAR LOS "TOTAL"
            # Nos quedamos solo con las filas que NO dicen TOTAL en la columna sección
            df = df[df[col_secc] != 'TOTAL']
            
            # 2. Filtro de Sexo: SOLO "Ambos Sexos"
            # Para validar el total nacional, usamos la columna agregada
            df = df[df[col_sexo] == 'Ambos Sexos']
            
            # 3. Filtro de Edad: > 80 años
            filtro_edad = df[col_edad].astype(str).str.contains('80|85|90|95|100', regex=True)
            
            # Limpieza numérica y Suma
            df['Total_Clean'] = limpiar_numero_espanol(df[col_total])
            total_ancianos = df[filtro_edad]['Total_Clean'].sum()
            
            series_temporales.append({'anio': int(anio), 'total_target': total_ancianos, 'fuente': 'Padron'})
            print(f"   ✅ Año {anio}: {total_ancianos:,.0f} (Debe rondar 2.8M)")
            
        except Exception as e:
            print(f"   ❌ Error en {anio}: {e}")

    # 2. PROCESAR MUNDO NUEVO (2021-2025)
    print("\n>>> Procesando Moderno (Censo)...")
    if os.path.exists(ARCHIVO_CENSO):
        try:
            df_censo = pd.read_csv(ARCHIVO_CENSO, sep='\t', dtype=str, low_memory=False)
            
            # --- FILTROS PARA CENSO ---
            # 1. Filtro Geográfico: Eliminar filas donde 'Secciones' está vacío
            # (En el censo, los totales tienen la columna sección vacía)
            df_censo = df_censo.dropna(subset=['Secciones'])
            
            # 2. Filtro de Sexo: SOLO "Total" (Equivalente a Ambos Sexos)
            df_censo = df_censo[df_censo['Sexo'] == 'Total']
            
            # 3. Filtro de Edad
            filtro_edad_censo = df_censo['Edad'].astype(str).str.contains('80|85|90|95|100', regex=True)
            
            # Limpieza numérica
            df_censo['Total_Clean'] = limpiar_numero_espanol(df_censo['Total'])
            
            # Agrupar
            grupo = df_censo[filtro_edad_censo].groupby('Periodo')['Total_Clean'].sum().sort_index()
            
            for anio, total in grupo.items():
                try:
                    anio_int = int(float(anio))
                    series_temporales.append({'anio': anio_int, 'total_target': total, 'fuente': 'Censo'})
                    print(f"   ✅ Año {anio_int}: {total:,.0f} (Debe rondar 2.8M)")
                except: continue
                
        except Exception as e:
            print(f"   ❌ Error en Censo: {e}")

    # 3. RESULTADO FINAL
    if series_temporales:
        df_res = pd.DataFrame(series_temporales).sort_values('anio')
        print("\n--- SERIE TEMPORAL PURIFICADA ---")
        print(df_res[['anio', 'total_target', 'fuente']].to_string(index=False))
        
        # Calcular Salto 2020-2021
        try:
            val_20 = df_res[df_res['anio']==2020]['total_target'].values[0]
            val_21 = df_res[df_res['anio']==2021]['total_target'].values[0]
            delta_pct = ((val_21 - val_20) / val_20) * 100
            
            print(f"\n>>> IMPACTO COVID REAL (2020 vs 2021): {delta_pct:.2f}%")
            if -10 < delta_pct < 5:
                print("✅ VALIDADO: Los datos son coherentes y usables.")
            else:
                print("⚠️ ALERTA: Todavía hay discrepancia. Revisar filtros.")
        except:
            print("Faltan datos para calcular el salto.")

if __name__ == "__main__":
    verificacion_final()
