
# 🤖 Anime Recommender (Content-Based)

`Este proyecto` implementa un sistema de recomendación de anime basado en contenido (Content-Based Filtering) utilizando datos del catálogo de AniList y la lista de visualización personal de un usuario (exportada vía MyAnimeList/AniList XML).

El sistema analiza los géneros, temas y descripciones de los animes que el usuario ha visto y puntuado, y luego utiliza una matriz de similitud (TF-IDF y SVD) para sugerir títulos similares de alto score que el usuario aún no ha explorado.



## ✨ Características Principales
- **Content-Based Filtering:** Utiliza la descripción, géneros y tags para crear un perfil de contenido.
- **Dimensionalidad Reducida (SVD):** Emplea SVD (Singular Value Decomposition) sobre la matriz TF-IDF para manejar grandes volúmenes de características de texto.
- **Filtrado Híbrido:** Excluye automáticamente animes ya vistos y utiliza una combinación de la similitud del contenido con el score de la comunidad (AniList) para priorizar las recomendaciones.
- **Blacklist:** Permite al usuario excluir manualmente animes que no desea que se le recomienden en el futuro.
## 🚀 Instalación y Uso

**Requisitos**

Necesitas tener *Python 3.9+* y *pip* instalados.

1. **Clonar el Repositorio**

```bash
git clone https://github.com/SrAlex16/Anime_recommender
cd anime_recommender
```

2. **Crear y Activar el Entorno Virtual**
```bash
python3 -m venv venv
source venv/bin/activate
```

3. **Instalar Dependencias**
```bash
pip install -r requirements.txt
```
> [!NOTE] 
> El archivo requirements.txt contendrá librerías como pandas, numpy,          scikit-learn, etc.

4. **Configuración Inicial de Datos**
El motor necesita un archivo XML de tu lista personal (AniList o MAL) para comenzar. Coloca tu archivo XML en el directorio raíz.

- **Usa tu XML:** Coloca animelist.xml en \anime_recommender\data.
