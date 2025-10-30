# src/data/download_mal_list.py

import requests
import json
import os
import time
import sys

# --- CONFIGURACIÓN DE RUTAS ---
# Sube tres niveles (consistente con el resto del proyecto)
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(ROOT_DIR, "data") 
# El archivo JSON de salida que luego leerá parse_xml.py
USER_JSON_OUTPUT_FILE = os.path.join(DATA_DIR, "user_mal_list.json")
# -----------------------------

PAGE_SIZE = 300 
ENDPOINT_BASE = "https://myanimelist.net/animelist/{user}/load.json?status=7&offset={offset}"

def debug_log(message):
    print(f"🔍 [DOWNLOAD_DEBUG] {message}", file=sys.stderr, flush=True)

def download_user_list(username):
    """
    Descarga la lista completa de anime de un usuario de MAL usando el endpoint JSON paginado.
    """
    username = username.strip()
    
    if not username:
        debug_log("❌ Error: El nombre de usuario no puede estar vacío.")
        return False

    full_list = []
    offset = 0
    
    debug_log(f"📡 Iniciando descarga de la lista de: {username}...")
    debug_log(" (La lista debe ser pública para funcionar sin login.)")
    
    # Asegurarse de crear el directorio antes de escribir
    os.makedirs(DATA_DIR, exist_ok=True)

    while True:
        url = ENDPOINT_BASE.format(user=username, offset=offset)
        
        try:
            time.sleep(0.5) 
            response = requests.get(url, headers={'User-Agent': 'MAL-List-Downloader-V2.0'})
            response.raise_for_status() # Lanza HTTPError para códigos de error (4xx o 5xx)
            
            # Si el JSON es vacío (solo "[]\n"), significa que no hay más datos.
            if not response.text.strip() or response.text.strip() == '[]':
                break
            
            data = response.json()
            
            if not isinstance(data, list):
                debug_log(f"\n❌ Error: La respuesta de la API no es una lista en el offset {offset}.")
                return False
                
            if not data:
                break # Lista vacía, finaliza el bucle
            
            full_list.extend(data)
            
            debug_log(f"✅ Bloque descargado. Total de entradas: {len(full_list)}")
            
            offset += len(data)

        except requests.exceptions.RequestException as e:
            debug_log(f"\n❌ Error de conexión al descargar el bloque (offset: {offset}): {e}")
            return False
        except json.JSONDecodeError:
            debug_log(f"\n❌ Error al decodificar JSON en el offset {offset}. Respuesta inválida.")
            return False

    if full_list:
        debug_log(f"\n🎉 Descarga completa. Se encontraron {len(full_list)} entradas de anime.")
        
        # Guardar la lista completa como un único archivo JSON
        with open(USER_JSON_OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(full_list, f, indent=4)
        
        debug_log(f"El archivo '{os.path.basename(USER_JSON_OUTPUT_FILE)}' se guardó en {os.path.abspath(DATA_DIR)}.")
        return True
    else:
        debug_log("\n⚠️ No se encontraron entradas o la lista está vacía.")
        return False

def main():
    # Este bloque solo se ejecuta cuando se llama directamente, no desde el orquestador
    if len(sys.argv) > 1:
        USERNAME = sys.argv[1]
    else:
        USERNAME = input("Por favor, introduce el nombre de usuario de MyAnimeList (MAL) para descargar la lista: ")
    
    if not download_user_list(USERNAME):
        sys.exit(1)

if __name__ == '__main__':
    main()