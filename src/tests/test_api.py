# src/test/api_code.py
"""
Script de prueba unitaria para verificar el acceso a la API de AniList.
Ejecuta una consulta GraphQL simple y valida que la respuesta sea correcta.

Uso:
    python src/test/api_code.py
"""

import requests
import json
import sys

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
      averageScore
    }
  }
}
"""

def test_anilist_api(page: int = 1, per_page: int = 3):
    """
    Realiza una petición a la API de AniList para comprobar:
      - Código HTTP 200
      - Estructura JSON válida
      - Presencia de campos esenciales
    """
    print("🔍 Probando conexión con la API de AniList...")
    try:
        response = requests.post(
            ANILIST_API,
            json={"query": QUERY, "variables": {"page": page, "perPage": per_page}},
            timeout=10,
        )

        print(f"🌐 Estado HTTP: {response.status_code}")
        if response.status_code != 200:
            print("❌ Error: respuesta no exitosa de la API.")
            print(response.text)
            sys.exit(1)

        data = response.json()
        # CORRECCIÓN: Usar la clave 'data'
        media = data.get("data", {}).get("Page", {}).get("media", []) 
        
        if not media:
            print("⚠️ Advertencia: No se devolvieron resultados en la consulta.")
            sys.exit(1)

        print(f"✅ Conexión exitosa. Se recibieron {len(media)} resultados.\n")

        # Mostrar los primeros resultados (id + título)
        for anime in media:
            title = (
                anime.get("title", {}).get("english")
                or anime.get("title", {}).get("romaji")
                or anime.get("title", {}).get("native")
                or "Sin título"
            )
            print(f"🎬 ID AniList: {anime.get('id')} | MAL ID: {anime.get('idMal')} | Título: {title}")

        print("\n✅ Test completado correctamente. La API responde como se esperaba.")

    except requests.exceptions.RequestException as e:
        print(f"❌ Error de conexión: {e}")
        sys.exit(1)
    except json.JSONDecodeError:
        print("❌ Error: La respuesta no contiene JSON válido.")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error inesperado durante el test de API: {e}")
        sys.exit(1)


if __name__ == "__main__":
    test_anilist_api()