# src/data/fetch_datasets.py - VERSIÓN OPTIMIZADA
import os
import sys
import time
import requests
import pandas as pd
from tqdm import tqdm

# --- CONFIGURACIÓN DE RUTAS PORTABLE (3 NIVELES) ---
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(ROOT_DIR, "data")
MERGED_PATH = os.path.join(DATA_DIR, "merged_anime.csv")

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

def fetch_page(page, per_page=50):
    """🔥 OPTIMIZADO: 50 items por página en lugar de 20"""
    r = requests.post(ANILIST_API, json={"query": QUERY, "variables": {"page": page, "perPage": per_page}})
    r.raise_for_status()
    data = r.json()
    return data.get("data", {}).get("Page", {}).get("media", [])

def normalize(media_list):
    rows = []
    for m in media_list:
        score = m.get("averageScore")
        if score is None:
            score = 0

        rows.append({
            "AniListID": m.get("id"),
            "MalID": m.get("idMal"),
            "title": m.get("title", {}).get("english") or m.get("title", {}).get("romaji"),
            "description": m.get("description"),
            "genres": m.get("genres") or [],
            "tags": [t["name"] for t in m.get("tags", []) if isinstance(t, dict) and t.get("name")],
            "score": score,
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

def fetch_all(max_pages=25):
    """
    🔥 OPTIMIZADO: Reducido a 25 páginas (1250 animes) en lugar de 50 (2500)
    
    Esto es suficiente porque:
    - Los animes están ordenados por popularidad
    - Los usuarios raramente tienen en su lista animes fuera del top 1250
    - Reduce el tiempo de descarga a la mitad
    """
    all_data = []
    
    with tqdm(total=max_pages * 50, desc="Descargando Animes", unit="item", dynamic_ncols=True, leave=True) as pbar:
        for page in range(1, max_pages + 1):
            try:
                media = fetch_page(page, per_page=50)
                if not media:
                    break
                
                all_data.extend(media)
                pbar.update(len(media))
                
                time.sleep(0.6)  # Rate limiting
            except Exception as e:
                print(f"\n❌ Error en página {page}: {e}")
                break
            
    return normalize(all_data)

def main():
    print("🚀 Iniciando descarga de dataset de AniList (versión optimizada)...")
    df = fetch_all()
    os.makedirs(DATA_DIR, exist_ok=True)
    df.to_csv(MERGED_PATH, index=False, encoding="utf-8")
    print(f"\n✅ merged_anime.csv generado en {os.path.abspath(MERGED_PATH)} ({len(df)} filas).")

if __name__ == "__main__":
    main()