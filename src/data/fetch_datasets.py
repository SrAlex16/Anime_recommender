# src/data/fetch_datasets.py
import os
import sys
import time
import requests
import pandas as pd
import subprocess
from tqdm import tqdm  # 💡 CORRECCIÓN CRÍTICA: Importar la clase tqdm directamente

# --- CONFIGURACIÓN DE RUTAS PORTABLE (3 NIVELES) ---
# Sube tres niveles: src/data -> src -> anime_recommender (ROOT_DIR)
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
      id
      idMal
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

def fetch_page(page, per_page=20):
    # Aquí puedes añadir un manejo de errores más robusto si lo deseas
    r = requests.post(ANILIST_API, json={"query": QUERY, "variables": {"page": page, "perPage": per_page}})
    r.raise_for_status()
    data = r.json()
    return data.get("data", {}).get("Page", {}).get("media", [])

def normalize(media_list):
    rows = []
    for m in media_list:
        rows.append({
            "AniListID": m.get("id"),
            "MalID": m.get("idMal"),
            "title": m.get("title", {}).get("english") or m.get("title", {}).get("romaji"),
            "description": m.get("description"),
            "genres": m.get("genres") or [],
            "tags": [t["name"] for t in m.get("tags", []) if isinstance(t, dict) and t.get("name")],
            "score": m.get("averageScore"),
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
    df = df.drop_duplicates(subset=["AniListID"]).reset_index(drop=True)
    df = df[df["MalID"].notna()].copy()

    return df

def fetch_all(max_pages=50):
    all_data = []
    
    # 💡 CORRECCIÓN CRÍTICA: Usar la clase tqdm para la barra de progreso
    with tqdm(total=max_pages * 50, desc="Descargando Animes", unit="item", dynamic_ncols=True, leave=True) as pbar:
        for page in range(1, max_pages + 1):
            try:
                media = fetch_page(page)
                if not media:
                    break
                
                all_data.extend(media)
                pbar.update(len(media))
                
                time.sleep(1) 
            except Exception:
                # El error se maneja en el subprocess en prepare_data.py
                break
            
    return normalize(all_data)

def main():
    df = fetch_all()
    # Asegurarse de que el directorio 'data' exista en la raíz del proyecto
    os.makedirs(DATA_DIR, exist_ok=True) 
    df.to_csv(MERGED_PATH, index=False, encoding="utf-8")
    # Imprime la ruta final para confirmación
    print(f"\n✅ merged_anime.csv generado en {os.path.abspath(MERGED_PATH)} ({len(df)} filas).")

if __name__ == "__main__":
    main()