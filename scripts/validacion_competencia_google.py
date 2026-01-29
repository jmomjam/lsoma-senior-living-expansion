#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
VALIDACION_COMPETENCIA_V3.1.PY - TÁCTICA TEXT SEARCH (OPTIMIZADA)
================================================================================
Objetivo: Usar 'searchText' con operador lógico para buscar múltiples términos
          ("Residencia" y "Geriátrico") en UNA sola llamada por cluster.
          
Autor: L-SOMA Project
Fecha: Enero 2026
================================================================================
"""

import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# ==============================================================================
# CONFIGURACIÓN API
# ==============================================================================
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY") 

# ==============================================================================
# PARÁMETROS
# ==============================================================================
INPUT_FILE = "../datos/expansion_clusters_final.csv"
OUTPUT_FILE = "../datos/clusters_359_validado_competencia.csv"

RADIO_BUSQUEDA_METROS = 1500
CAMAS_POR_COMPETIDOR = 80 

# OPTIMIZACIÓN: Usamos OR para buscar sinónimos en una sola llamada
QUERY_TEXTO = "Residencia de ancianos OR Geriátrico OR Centro de mayores"

# Endpoint Text Search (New API)
PLACES_URL = "https://places.googleapis.com/v1/places:searchText"

# ==============================================================================
# FUNCIONES
# ==============================================================================

def buscar_competencia_text(lat, lon):
    """
    Usa Text Search para encontrar residencias.
    """
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": GOOGLE_API_KEY,
        "X-Goog-FieldMask": "places.displayName,places.id,places.types" 
    }

    payload = {
        "textQuery": QUERY_TEXTO,
        "maxResultCount": 20, 
        "locationBias": {
            "circle": {
                "center": {
                    "latitude": lat,
                    "longitude": lon
                },
                "radius": RADIO_BUSQUEDA_METROS
            }
        }
    }
    
    try:
        response = requests.post(PLACES_URL, headers=headers, json=payload, timeout=10)
        
        if response.status_code != 200:
            # Si da error, devolvemos -1 para saber que falló, no 0
            print(f"    ⚠ Error API {response.status_code}: {response.text}")
            return -1
            
        data = response.json()
        lugares = data.get("places", [])
        
        # FILTRO DE CALIDAD POST-BÚSQUEDA
        # Aunque busquemos por texto, verificamos que no sea una farmacia o gimnasio
        validos = 0
        
        # Palabras clave negativas (si aparecen en el nombre, descartar)
        blacklist = ["farmacia", "ortopedia", "gimnasio", "club", "asociación", "parking"]
        
        for lugar in lugares:
            nombre = lugar.get("displayName", {}).get("text", "").lower()
            tipos = lugar.get("types", [])
            
            # 1. Filtro de Negativos (Nombre)
            if any(bad in nombre for bad in blacklist):
                continue
                
            # 2. Filtro de Positivos (Tipo o Nombre)
            # Si tiene el tipo correcto O el nombre suena a residencia
            es_tipo_valido = any(t in tipos for t in ["nursing_home", "assisted_living_complex", "health"])
            es_nombre_valido = any(x in nombre for x in ["residencia", "geriatri", "mayores", "vivienda", "centro de día"])
            
            if es_tipo_valido or es_nombre_valido:
                validos += 1
                
        return validos
            
    except requests.exceptions.RequestException as e:
        print(f"    ✗ Error de conexión: {e}")
        return -1

def clasificar_oceano(i_sat):
    if i_sat < 0.30: return "Blue Ocean"
    elif i_sat <= 1.0: return "Batalla"
    else: return "Saturado"

def ejecutar_validacion():
    print("=" * 70)
    print("   VALIDACIÓN DE COMPETENCIA - TÁCTICA TEXT SEARCH V3.1 (OPTIMIZADA)")
    print("=" * 70)
    
    try:
        df = pd.read_csv(INPUT_FILE, sep=';')
        print(f"    ✓ {len(df)} clusters cargados")
    except FileNotFoundError:
        print("    ✗ ERROR: No se encuentra el archivo de entrada")
        return

    # Inicializar
    df['Num_Competidores'] = 0
    df['Oferta_Estimada_Camas'] = 0
    df['Indice_Saturacion'] = 0.0
    df['Tipo_Oceano'] = ""
    
    print(f"\n>>> Buscando: '{QUERY_TEXTO}'")
    
    total = len(df)
    blue_oceans_count = 0
    errores = 0
    
    for idx, row in df.iterrows():
        lat = row['LATITUD']
        lon = row['LONGITUD']
        camas_pot = row['Camas_Potenciales']
        
        num_comp = buscar_competencia_text(lat, lon)
        
        # Gestión de errores de API
        if num_comp == -1:
            errores += 1
            num_comp = 0 # Asumimos 0 por defecto para no romper el cálculo, pero avisamos
        
        oferta = num_comp * CAMAS_POR_COMPETIDOR
        i_sat = oferta / camas_pot if camas_pot > 0 else 0
        oceano = clasificar_oceano(i_sat)
        
        if oceano == "Blue Ocean":
            blue_oceans_count += 1
        
        df.at[idx, 'Num_Competidores'] = num_comp
        df.at[idx, 'Oferta_Estimada_Camas'] = oferta
        df.at[idx, 'Indice_Saturacion'] = round(i_sat, 4)
        df.at[idx, 'Tipo_Oceano'] = oceano
        
        if (idx + 1) % 5 == 0 or idx == total - 1:
            print(f"    [{idx + 1}/{total}] Encontrados: {num_comp} -> {oceano}")
        
        time.sleep(0.1) 
    
    df.to_csv(OUTPUT_FILE, sep=';', index=False)
    print(f"\n>>> Guardado: {OUTPUT_FILE}")
    print(f"Total Blue Oceans: {blue_oceans_count}")
    if errores > 0:
        print(f"⚠ Hubo {errores} fallos de conexión con la API.")

if __name__ == "__main__":
    ejecutar_validacion()
