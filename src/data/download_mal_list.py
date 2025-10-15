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


def download_user_list(username):
    """
    Descarga la lista completa de anime de un usuario de MAL usando el endpoint JSON paginado.
    """
    username = username.strip()
    
    if not username:
        print("❌ Error: El nombre de usuario no puede estar vacío.")
        return False

    full_list = []
    offset = 0
    
    print(f"📡 Iniciando descarga de la lista de: {username}...")
    print(" (La lista debe ser pública para funcionar sin login.)")

    while True:
        url = ENDPOINT_BASE.format(user=username, offset=offset)
        
        try:
            time.sleep(0.5) 
            response = requests.get(url, headers={'User-Agent': 'MAL-List-Downloader-IA-App'})
            
            if response.status_code != 200:
                print(f"❌ Error HTTP {response.status_code} al solicitar offset {offset}. La descarga se detiene.")
                if response.status_code == 404:
                    print(f"💡 Consejo: Verifica el nombre de usuario '{username}' y que la lista sea pública.")
                return False

            data = response.json()
            
            if not data:
                break
            
            full_list.extend(data)
            
            print(f"✅ Bloque descargado. Total de entradas: {len(full_list)}", end='\r', flush=True)
            
            offset += len(data)

        except requests.exceptions.RequestException as e:
            print(f"\n❌ Error de conexión al descargar el bloque (offset: {offset}): {e}")
            return False
        except json.JSONDecodeError:
            print(f"\n❌ Error al decodificar JSON en el offset {offset}. Respuesta inválida.")
            return False

    if full_list:
        print(f"\n🎉 Descarga completa. Se encontraron {len(full_list)} entradas de anime.")
        
        # Guardar la lista completa como un único archivo JSON
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(USER_JSON_OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(full_list, f, indent=4)
        
        print(f"El archivo '{os.path.basename(USER_JSON_OUTPUT_FILE)}' se guardó en {os.path.abspath(DATA_DIR)}.")
        return True
    else:
        print("\n⚠️ No se encontraron entradas o la lista está vacía.")
        return False

def main():
    # Pedir el nombre de usuario por consola
    USERNAME = input("Por favor, introduce el nombre de usuario de MyAnimeList (MAL) para descargar la lista: ")
    
    if not download_user_list(USERNAME):
        # Si la descarga falla, el script termina con un código de error
        sys.exit(1)
        
    sys.exit(0) 

if __name__ == "__main__":
    main()