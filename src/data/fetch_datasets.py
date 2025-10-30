# src/data/fetch_datasets.py
import os
import sys
import time
import requests
import pandas as pd
import subprocess
from tqdm import tqdm  # 💡 CORRECCIÓN CRÍTICA: Importar la clase tqdm directamente

# --- CONFIGURACIÓN DE RUTAS PORTABLE (3 NIVELES) ---\n# Sube tres niveles: src/data -> src -> anime_recommender (ROOT_DIR)
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# Construye la ruta a la carpeta 'data' en la raíz
DATA_DIR = os.path.join(ROOT_DIR, "data")
MERGED_PATH = os.path.join(DATA_DIR, "merged_anime.csv")

# PREPARE_SCRIPT_PATH no es necesario en este script
# PREPARE_SCRIPT_PATH = os.path.join(os.path.dirname(__file__), "prepare_data.py") 

ANILIST_API = "https://graphql.anilist.co"
QUERY = """
query ($page: Int, $perPage: Int) {
  Page(page: $page, perPage: $perPage) {
    media(type: ANIME, sort: POPULARITY_DESC) {
      id # AniList ID
      idMal # MyAnimeList ID (CRÍTICO para la fusión)
      title {
        romaji
        english
        native
      }
      description(asHtml: false)
      genres
      tags {
        name
      }
      averageScore
      episodes
      status
      type
      siteUrl
      studios(isMain: true) {
        nodes {
          name
        }
      }
    }
  }
}
"""

def fetch_page(page, per_page=50):
    """Obtiene una página de la API de AniList."""
    variables = {'page': page, 'perPage': per_page}
    
    try:
        response = requests.post(ANILIST_API, json={'query': QUERY, 'variables': variables})
        response.raise_for_status()
        data = response.json()
        
        # Verificar si hay datos en la página
        if data and 'data' in data and data['data']['Page']['media']:
            return data['data']['Page']['media']
        return None
    except requests.exceptions.RequestException as e:
        print(f"❌ Error de red al obtener la página {page}: {e}", file=sys.stderr)
        return None

def normalize(media_list):
    """Normaliza y limpia la lista de medios a un DataFrame de Pandas."""
    rows = []
    for m in media_list:
        title = m.get('title', {})
        mal_id = m.get('idMal')
        
        # Saltarse si no tiene MAL ID, ya que es la clave de fusión
        if mal_id is None:
            continue
            
        # Asegurar que los campos de lista sean listas
        tags = [t['name'] for t in m.get('tags', []) if isinstance(t, dict) and t.get('name')]
        genres = m.get('genres', [])
        
        # Normalizar la puntuación de 1-100 a 1-10.0
        score_100 = m.get('averageScore', 0)
        score_10 = round(score_100 / 10, 1) if score_100 else 0.0

        rows.append({
            "id": m.get("id"), # AniList ID
            "idMal": mal_id, # MAL ID
            "title": title.get('romaji') or title.get('english') or title.get('native') or "Título Desconocido",
            "description": m.get("description"),
            "genres": genres,
            "tags": tags,
            "averageScore": score_10, # Puntuación normalizada
            "episodes": m.get("episodes"),
            "status": m.get("status"),
            "type": m.get("type"),
            "siteUrl": m.get("siteUrl"),
            "studios": [
                n["name"]
                for n in (m.get("studios", {}).get("nodes", []) or [])
                if isinstance(n, dict) and n.get("name")
            ],
        })

    df = pd.DataFrame(rows)
    # CRÍTICO: Eliminar duplicados basándose en el ID de AniList
    df = df.drop_duplicates(subset=["id"]).reset_index(drop=True) 
    # CRÍTICO: Solo mantener animes que tengan un MalID para la fusión
    df = df[df["idMal"].notna()].copy() 

    return df

def fetch_all(max_pages=50):
    all_data = []
    
    # 💡 CORRECCIÓN CRÍTICA: Usar la clase tqdm para la barra de progreso
    with tqdm(total=max_pages * 50, desc="Descargando Animes", unit="item", dynamic_ncols=True, leave=True) as pbar:
        for page in range(1, max_pages + 1):
            try:
                media = fetch_page(page)
                if media is None:
                    break
                
                all_data.extend(media)
                pbar.update(len(media))
                
                time.sleep(1) # Respetar el límite de rate de la API de AniList
            except Exception as e:
                print(f"❌ Error inesperado en la página {page}: {e}", file=sys.stderr)
                break
            
    return normalize(all_data)

def main():
    df = fetch_all()
    if df.empty:
        print("❌ Fallo al descargar el dataset base.", file=sys.stderr)
        sys.exit(1)
        
    # Asegurarse de que el directorio 'data' exista en la raíz del proyecto
    os.makedirs(DATA_DIR, exist_ok=True) 
    df.to_csv(MERGED_PATH, index=False)
    
    print(f"🎉 Dataset base de {len(df)} animes guardado en: {MERGED_PATH}", file=sys.stderr)


if __name__ == '__main__':
    main()