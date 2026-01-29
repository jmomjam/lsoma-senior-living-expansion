#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
VALIDACION_COMPETENCIA_V4.PY - CON DISTANCIA Y NOMBRES
================================================================================
Objetivo: 
1. Buscar competidores reales.
2. Calcular la DISTANCIA exacta (metros) desde el centro del cluster.
3. Guardar los nombres de los rivales en el CSV para inspección humana.
================================================================================
"""

import pandas as pd
import os
import yaml
from datetime import datetime
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Cargar Configuración Centralizada
with open("../config.yaml", "r") as f:
    config = yaml.safe_load(f)

# ==============================================================================
# CONFIGURACIÓN
# ==============================================================================
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY") 

INPUT_FILE = "../datos/expansion_clusters_final.csv"
OUTPUT_FILE = "../datos/clusters_359_validado_FINAL.csv"

# Parámetros desde config.yaml
RADIO_BUSQUEDA_METROS = config['competition']['search_radius_meters']
CAMAS_POR_COMPETIDOR = config['competition']['beds_per_competitor_estimate']
 
QUERY_TEXTO = "Residencia de ancianos OR Geriátrico" # Query limpia
PLACES_URL = "https://places.googleapis.com/v1/places:searchText"

# ==============================================================================
# FORMULA DE HAVERSINE (Distancia entre dos puntos geográficos)
# ==============================================================================
def calcular_distancia(lat1, lon1, lat2, lon2):
    R = 6371000 # Radio Tierra en metros
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    
    return round(R * c) # Retorna metros

# ==============================================================================
# BUSCADOR
# ==============================================================================
def analizar_cluster(lat_centro, lon_centro):
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": GOOGLE_API_KEY,
        "X-Goog-FieldMask": "places.displayName,places.location,places.types"
    }

    payload = {
        "textQuery": QUERY_TEXTO,
        "maxResultCount": 20, 
        "locationBias": {
            "circle": {
                "center": {"latitude": lat_centro, "longitude": lon_centro},
                "radius": RADIO_BUSQUEDA_METROS
            }
        }
    }
    
    try:
        response = requests.post(PLACES_URL, headers=headers, json=payload, timeout=10)
        data = response.json()
        lugares = data.get("places", [])
        
        competidores_validos = []
        
        blacklist = ["farmacia", "ortopedia", "gimnasio", "club", "asociación", "parking", "ayuntamiento"]
        
        for lugar in lugares:
            nombre = lugar.get("displayName", {}).get("text", "Sin nombre")
            tipos = lugar.get("types", [])
            loc = lugar.get("location", {})
            lat_comp = loc.get("latitude")
            lon_comp = loc.get("longitude")
            
            # Filtros
            nombre_lower = nombre.lower()
            if any(bad in nombre_lower for bad in blacklist): continue
            
            es_tipo = any(t in tipos for t in ["nursing_home", "assisted_living_complex", "health"])
            es_nombre = any(x in nombre_lower for x in ["residencia", "geriatri", "mayores", "vivienda", "tercera edad"])
            
            if es_tipo or es_nombre:
                # CALCULAR DISTANCIA REAL
                dist = calcular_distancia(lat_centro, lon_centro, lat_comp, lon_comp)
                
                # Solo contamos si realmente cae dentro del radio (la API a veces es laxa)
                if dist <= RADIO_BUSQUEDA_METROS:
                    competidores_validos.append({
                        "nombre": nombre,
                        "distancia": dist
                    })
        
        # Ordenar por cercanía (los más peligrosos primero)
        competidores_validos.sort(key=lambda x: x['distancia'])
        
        return competidores_validos
            
    except Exception as e:
        print(f"    ✗ Error conexión: {e}")
        return []

def clasificar_oceano(i_sat):
    if i_sat < 0.20: return "Blue Ocean" # Muy exigente
    elif i_sat <= 1.0: return "Batalla"
    else: return "Saturado"

# ==============================================================================
# MAIN
# ==============================================================================
def ejecutar_final():
    print("=" * 70)
    print("   ANÁLISIS FINAL DE COMPETENCIA (CON DISTANCIAS)")
    print("=" * 70)
    
    df = pd.read_csv(INPUT_FILE, sep=';')
    print(f"    ✓ {len(df)} clusters cargados")
    
    # Columnas nuevas
    df['Num_Competidores'] = 0
    df['Rivales_Cercanos'] = "" # Guardaremos los nombres aquí
    df['Distancia_Media_Competencia'] = 0
    df['Indice_Saturacion'] = 0.0
    df['Tipo_Oceano'] = ""
    
    total = len(df)
    blue_oceans = 0
    
    for idx, row in df.iterrows():
        lat = row['LATITUD']
        lon = row['LONGITUD']
        camas_pot = row['Camas_Potenciales']
        
        competidores = analizar_cluster(lat, lon)
        num_comp = len(competidores)
        
        # Guardar nombres de los 3 más cercanos (ej: "Sanitas (200m) | DomusVi (500m)")
        top_3 = competidores[:3]
        nombres_str = " | ".join([f"{c['nombre']} ({c['distancia']}m)" for c in top_3])
        
        # Distancia media
        if num_comp > 0:
            dist_media = sum(c['distancia'] for c in competidores) / num_comp
        else:
            dist_media = 0
            
        oferta = num_comp * CAMAS_POR_COMPETIDOR
        i_sat = oferta / camas_pot if camas_pot > 0 else 0
        oceano = clasificar_oceano(i_sat)
        
        if oceano == "Blue Ocean": blue_oceans += 1
        
        df.at[idx, 'Num_Competidores'] = num_comp
        df.at[idx, 'Rivales_Cercanos'] = nombres_str
        df.at[idx, 'Distancia_Media_Competencia'] = int(dist_media)
        df.at[idx, 'Indice_Saturacion'] = round(i_sat, 4)
        df.at[idx, 'Tipo_Oceano'] = oceano
        
        if (idx + 1) % 5 == 0:
            print(f"    [{idx + 1}/{total}] Cluster {idx}: {num_comp} rivales -> {oceano}")
            if num_comp > 0:
                print(f"       -> Más cercano: {competidores[0]['nombre']} a {competidores[0]['distancia']}m")
        
        time.sleep(0.1)

    df.to_csv(OUTPUT_FILE, sep=';', index=False)
    print("\n" + "=" * 70)
    print(f"✅ ANÁLISIS COMPLETADO")
    print(f"📂 Archivo generado: {OUTPUT_FILE}")
    print(f"🌊 BLUE OCEANS ENCONTRADOS: {blue_oceans}")
    print("=" * 70)

if __name__ == "__main__":
    ejecutar_final()
