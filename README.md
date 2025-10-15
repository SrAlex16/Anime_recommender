
# 🤖 Anime Recommender (Content-Based)

Este proyecto implementa un sistema de recomendación de anime basado en contenido (**Content-Based Filtering**) utilizando datos del catálogo de **AniList** y la lista de visualización personal de un usuario (exportada vía Endopoint MyAnimeList JSON).

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
> [!Nota] 
> El archivo `requirements.txt` contendrá librerías como pandas, numpy, scikit-learn, etc.

4. **Configuración Inicial de Datos**
   El usuario debe tener su lista de MAL pública para descargarla sin login e indicar su username en el programa cuando se lo pida.

- **Usa tu XML:** Coloca animelist.xml en \anime_recommender\data.

5. **Ejecutar el Recomendador**
El script `train_model.py` se encargará automáticamente de descargar, limpiar y fusionar el catálogo de AniList con tu lista personal (si es la primera vez que se ejecuta o si los archivos de datos no existen).
```bash
python src/model/train_model.py
```
El programa te mostrará las estadísticas de tu lista y las 10 mejores recomendaciones.
## 🧪 Tests

Para garantizar que el aislamiento del motor de recomendación funciona correctamente sin depender de los datos de producción (evitando la "fuga de mocks"), puedes ejecutar los tests.

```bash
python -m pytest src/tests/run_tests.py
```
## 📄 Licencia

[Licencia de uso personal / Personal Use License](https://github.com/SrAlex16/Anime_recommender/blob/main/LICENSE.md#licencia-de-uso-personal--personal-use-license)


## 👨🏼‍💼Authors

- [@SrAlex16](https://github.com/SrAlex16)


## 🔗 Links
[![Portfolio](https://img.shields.io/badge/my_portfolio-1?style=for-the-badge&logo=ko-fi&logoColor=black)](https://www.aletm.com)

[![LinkedIn](https://img.shields.io/badge/linkedIn-1DA1F2?style=for-the-badge&logo=linkedin&logoColor=white)](https://linkedin.com/)

