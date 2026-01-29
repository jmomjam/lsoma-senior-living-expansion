import os
import requests
import time

# --- CONFIGURACIÓN ---
# Años a intentar descargar (Orden cronológico)
ANIOS_OBJETIVO = [2016, 2017, 2018, 2019, 2020]

# Ruta base donde guardar los archivos (Se crearán subcarpetas)
# Ajusta esto si quieres que vaya directo a tu carpeta de proyecto
DIRECTORIO_BASE = "/Users/cosotos/proyectos/akademia/casoprácticoIA/datos/padron_raw"

# Patrón de la URL detectado (El {0} es año, {1} es código provincia)
# Nota: La parte 'p07' podría cambiar en años muy antiguos, el script avisará si falla.
URL_TEMPLATE = "https://www.ine.es/jaxi/files/_px/es/csv_bd/t20/e245/p07/a{0}/l0/{1}01.csv_bd?nocab=1"

# Diccionario de códigos de provincia (01 a 52)
# Generamos la lista del 01 al 52 (incluyendo Ceuta 51 y Melilla 52)
CODIGOS_PROVINCIA = [f"{i:02d}" for i in range(1, 53)]

def descargar_padron_historico():
    print("--- INICIANDO BOT DE DESCARGA MASIVA INE ---")
    
    if not os.path.exists(DIRECTORIO_BASE):
        os.makedirs(DIRECTORIO_BASE)
        
    for anio in ANIOS_OBJETIVO:
        print(f"\n>>> PROCESANDO AÑO {anio}...")
        
        # Crear carpeta para el año
        carpeta_anio = os.path.join(DIRECTORIO_BASE, f"padron_{anio}")
        if not os.path.exists(carpeta_anio):
            os.makedirs(carpeta_anio)
            
        errores_anio = 0
        exitos_anio = 0
        
        for cod_prov in CODIGOS_PROVINCIA:
            # Construir URL
            url = URL_TEMPLATE.format(anio, cod_prov)
            
            # Nombre de archivo local
            nombre_archivo = f"provincia_{cod_prov}_{anio}.csv"
            ruta_guardado = os.path.join(carpeta_anio, nombre_archivo)
            
            # Si ya existe, saltamos (para poder re-ejecutar sin duplicar tráfico)
            if os.path.exists(ruta_guardado):
                # print(f"   [Saltando] {nombre_archivo} ya existe.")
                exitos_anio += 1
                continue
            
            try:
                # Petición HTTP
                # IMPORTANTE: Usamos un User-Agent para no parecer un bot malicioso
                headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) PythonBot/1.0'}
                r = requests.get(url, headers=headers, stream=True, timeout=10)
                
                if r.status_code == 200:
                    with open(ruta_guardado, 'wb') as f:
                        for chunk in r.iter_content(chunk_size=8192):
                            f.write(chunk)
                    print(f"   ✅ Descargado: Prov {cod_prov}")
                    exitos_anio += 1
                else:
                    print(f"   ❌ Error {r.status_code} en Prov {cod_prov} (Posible cambio de URL en este año)")
                    errores_anio += 1
                    
            except Exception as e:
                print(f"   ⚠️ Excepción en Prov {cod_prov}: {e}")
                errores_anio += 1
            
            # PAUSA DE CORTESÍA (Ethical Scraping)
            # Esperamos 0.5 segundos entre peticiones para no saturar al INE y que nos bloqueen la IP
            time.sleep(0.5)
            
        print(f"--- Fin Año {anio}: {exitos_anio} éxitos, {errores_anio} fallos ---")
        
        # Si un año falla completamente (52 errores), es probable que la estructura URL fuera distinta
        if exitos_anio == 0:
            print(f"⚠️ ALERTA: Parece que el año {anio} tiene una estructura URL distinta o no está disponible en esta ruta.")

    print("\n--- PROCESO COMPLETADO ---")
    print(f"Archivos guardados en: {os.path.abspath(DIRECTORIO_BASE)}")

if __name__ == "__main__":
    descargar_padron_historico()
