#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
VALIDACION_COMPETENCIA_AUDIT.PY - VERSIÓN CON REGISTRO DE TEXTO
================================================================================
Objetivo: Igual que el V3.1, pero guardando un LOG detallado de qué sitios
          está encontrando Google para verificar si son residencias reales
          o falsos positivos (Centros de día, Clubs, etc.).
================================================================================
"""

import pandas as pd
import requests
import time
import os
from datetime import datetime
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# ==============================================================================
# CONFIGURACIÓN
# ==============================================================================
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY") 

INPUT_FILE = "../datos/expansion_clusters_final.csv"
OUTPUT_FILE = "../datos/clusters_359_validado_competencia.csv"
LOG_TXT = "../datos/auditoria_competencia_detallada.txt" # <--- AQUÍ VERÁS LOS NOMBRES

RADIO_BUSQUEDA_METROS = 1500
CAMAS_POR_COMPETIDOR = 80 
QUERY_TEXTO = "Residencia de ancianos OR Residencia geriátrica"
PLACES_URL = "https://places.googleapis.com/v1/places:searchText"

def buscar_y_auditar(lat, lon, cluster_id, file_log):
    """
    Busca y escribe en el fichero de texto los nombres encontrados.
    """
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": GOOGLE_API_KEY,
        "X-Goog-FieldMask": "places.displayName,places.id,places.types,places.formattedAddress"
    }

    payload = {
        "textQuery": QUERY_TEXTO,
        "maxResultCount": 20, 
        "locationBias": {
            "circle": {
                "center": {"latitude": lat, "longitude": lon},
                "radius": RADIO_BUSQUEDA_METROS
            }
        }
    }
    
    try:
        response = requests.post(PLACES_URL, headers=headers, json=payload, timeout=10)
        data = response.json()
        lugares = data.get("places", [])
        
        validos = 0
        file_log.write(f"\n--------------------------------------------------\n")
        file_log.write(f"CLUSTER {cluster_id} (Lat: {lat:.4f}, Lon: {lon:.4f})\n")
        
        blacklist = ["farmacia", "ortopedia", "gimnasio", "club", "asociación", "parking", "ayuntamiento", "pabellón"]
        
        for lugar in lugares:
            nombre = lugar.get("displayName", {}).get("text", "Sin nombre")
            direccion = lugar.get("formattedAddress", "")
            tipos = lugar.get("types", [])
            nombre_lower = nombre.lower()
            
            # 1. Filtro de Negativos
            if any(bad in nombre_lower for bad in blacklist):
                file_log.write(f"   [DESCARTADO] {nombre} (Blacklist)\n")
                continue
                
            # 2. Filtro de Positivos
            es_tipo = any(t in tipos for t in ["nursing_home", "assisted_living_complex", "health"])
            es_nombre = any(x in nombre_lower for x in ["residencia", "geriatri", "mayores", "vivienda", "centro de día", "tercera edad"])
            
            if es_tipo or es_nombre:
                validos += 1
                # Escribimos en el log para que tú lo leas luego
                file_log.write(f"   [ACEPTADO] {nombre}\n")
                file_log.write(f"       -> Tipos: {tipos}\n")
                file_log.write(f"       -> Dir: {direccion}\n")
            else:
                file_log.write(f"   [IGNORADO] {nombre} (No parece residencia)\n")
        
        file_log.write(f"   >>> TOTAL VÁLIDOS: {validos}\n")
        return validos
            
    except Exception as e:
        print(f"    ✗ Error conexión: {e}")
        return -1

def clasificar_oceano(i_sat):
    if i_sat < 0.30: return "Blue Ocean"
    elif i_sat <= 1.0: return "Batalla"
    else: return "Saturado"

def ejecutar_auditoria():
    print("=" * 70)
    print("   VALIDACIÓN CON AUDITORÍA DE TEXTO")
    print("=" * 70)
    
    df = pd.read_csv(INPUT_FILE, sep=';')
    print(f"    ✓ {len(df)} clusters cargados")
    
    # Abrimos el fichero de texto
    with open(LOG_TXT, "w", encoding="utf-8") as f:
        f.write(f"AUDITORÍA DE COMPETENCIA - {datetime.now()}\n")
        f.write("==================================================\n")
        
        total = len(df)
        blue_oceans = 0
        
        for idx, row in df.iterrows():
            cluster_id = row['Cluster_ID']
            lat = row['LATITUD']
            lon = row['LONGITUD']
            camas_pot = row['Camas_Potenciales']
            
            # Pasamos el fichero abierto a la función
            num_comp = buscar_y_auditar(lat, lon, cluster_id, f)
            
            if num_comp == -1: num_comp = 0
            
            oferta = num_comp * CAMAS_POR_COMPETIDOR
            i_sat = oferta / camas_pot if camas_pot > 0 else 0
            oceano = clasificar_oceano(i_sat)
            
            if oceano == "Blue Ocean": blue_oceans += 1
            
            df.at[idx, 'Num_Competidores'] = num_comp
            df.at[idx, 'Oferta_Estimada_Camas'] = oferta
            df.at[idx, 'Indice_Saturacion'] = round(i_sat, 4)
            df.at[idx, 'Tipo_Oceano'] = oceano
            
            if (idx + 1) % 5 == 0:
                print(f"    [{idx + 1}/{total}] ID {int(cluster_id)}: {num_comp} sitios -> {oceano}")
            
            time.sleep(0.1)

    df.to_csv(OUTPUT_FILE, sep=';', index=False)
    print(f"\n✅ AUDITORÍA FINALIZADA.")
    print(f"👉 ABRE ESTE ARCHIVO PARA LEER LOS NOMBRES: {LOG_TXT}")

if __name__ == "__main__":
    ejecutar_auditoria()
