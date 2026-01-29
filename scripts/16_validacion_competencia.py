import pandas as pd
import requests
import time
import os

# --- CONFIGURACIÓN ---
ARCHIVO_CLUSTERS = "../datos/ranking_fase7_clusters.csv"
OUTPUT_COMPETENCIA = "../datos/ranking_fase8_competencia.csv"

def auditar_competencia():
    print("--- FASE 8: AUDITORÍA DE COMPETENCIA (OPENSTREETMAP) ---")
    
    # 1. CARGAR CLUSTERS
    if not os.path.exists(ARCHIVO_CLUSTERS):
        print("❌ Falta archivo de clusters.")
        return
    df_clusters = pd.read_csv(ARCHIVO_CLUSTERS, sep=';')
    
    # Analizaremos los Top 50 Clusters para no saturar la API
    df_top = df_clusters.head(50).copy()
    print(f">>> Analizando competencia en los Top {len(df_top)} Clusters...")

    # 2. FUNCIÓN DE CONSULTA A OVERPASS API (OSM)
    def contar_residencias_cercanas(lat, lon, radio_m=2000):
        # Query en lenguaje Overpass QL
        # Buscamos nodos o formas con etiqueta amenity=nursing_home o social_facility=assisted_living
        overpass_url = "http://overpass-api.de/api/interpreter"
        overpass_query = f"""
        [out:json];
        (
          node["amenity"="nursing_home"](around:{radio_m},{lat},{lon});
          way["amenity"="nursing_home"](around:{radio_m},{lat},{lon});
          rel["amenity"="nursing_home"](around:{radio_m},{lat},{lon});
          node["social_facility"="assisted_living"](around:{radio_m},{lat},{lon});
        );
        out count;
        """
        try:
            response = requests.get(overpass_url, params={'data': overpass_query}, timeout=20)
            if response.status_code == 200:
                data = response.json()
                # El conteo total está en la sección de estadísticas
                if 'elements' in data and len(data['elements']) > 0:
                    # A veces 'out count' devuelve un elemento con tags de conteo
                    return int(data['elements'][0]['tags']['total'])
                return 0
            else:
                return -1 # Error
        except Exception as e:
            return -1

    # 3. EJECUCIÓN DEL BARRIDO
    competencia_detectada = []
    
    print("   Consultando API (esto tardará unos segundos por respeto al servidor)...")
    
    for idx, row in df_top.iterrows():
        cluster_id = row['Cluster_ID']
        lat = row['Lat_Centro']
        lon = row['Lon_Centro']
        
        # Buscamos en radio de 2km desde el centro del cluster
        num_competidores = contar_residencias_cercanas(lat, lon, radio_m=2000)
        
        # Guardar resultado
        competencia_detectada.append(num_competidores)
        
        # Feedback visual
        barras = "█" * num_competidores if num_competidores > 0 else "."
        print(f"   Cluster {int(cluster_id)} ({str(row['Toponimos'])[:15]}...): {num_competidores} residencias {barras}")
        
        # Pausa para no ser bloqueados (Rate Limiting)
        time.sleep(1.5)

    df_top['Competencia_OSM'] = competencia_detectada
    
    # 4. CÁLCULO DE SATURACIÓN
    # Ratio: Plazas Estimadas vs Competencia Real
    # Asumimos que cada residencia competidora tiene ~80 plazas promedio
    df_top['Oferta_Estimada'] = df_top['Competencia_OSM'] * 80
    
    # Capacidad Teórica (Demanda) = Secciones * 90 targets * 10% (captura agresiva para ver techo)
    df_top['Demanda_Total_Cluster'] = df_top['Num_Secciones'] * 90
    
    # Ratio de Saturación = Oferta / Demanda
    # Si > 0.15 (15%), el mercado empieza a estar duro.
    df_top['Saturacion'] = df_top['Oferta_Estimada'] / df_top['Demanda_Total_Cluster']
    
    # Océano Azul Score: Bonificamos baja competencia
    # Si Saturacion es 0 (nadie), Score x 1.2
    # Si Saturacion es 0.5 (muy lleno), Score x 0.5
    df_top['Score_Oceano_Azul'] = df_top['Potencia_Total'] / (1 + df_top['Saturacion']*5)

    df_final = df_top.sort_values(by='Score_Oceano_Azul', ascending=False)
    
    df_final.to_csv(OUTPUT_COMPETENCIA, sep=';', index=False)
    print(f"✅ AUDITORÍA COMPLETADA: {OUTPUT_COMPETENCIA}")
    
    # 5. RESULTADOS
    print("\n--- TOP 10 OCÉANOS AZULES (ALTA DEMANDA / BAJA COMPETENCIA) ---")
    cols = ['Toponimos', 'Potencia_Total', 'Competencia_OSM', 'Saturacion', 'Score_Oceano_Azul']
    print(df_final[cols].head(10).to_string(index=False))

if __name__ == "__main__":
    auditar_competencia()
