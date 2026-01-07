
# 🤖 Anime Recommender 
Sistema de recomendación de anime que utiliza Content-Based Filtering con ML, combinando Python/Flask (backend) + Flutter (app móvil).


## ✨ Características Principales
- **Filtrado híbrido (similitud + score de comunidad):** Utiliza la descripción, géneros y tags para crear un perfil de contenido.
- **Backend API REST:** Desplegado en Render
- Content-Based Filtering con TF-IDF y SVD
- **Filtrado Híbrido:** Excluye automáticamente animes ya vistos y utiliza una combinación de la similitud del contenido con el score de la comunidad (AniList) para priorizar las recomendaciones.
- **Blacklist:** Permite al usuario excluir manualmente animes que no desea que se le recomienden en el futuro.
- Caché inteligente y soporte multiidioma
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
> El archivo `requirements.txt` contendrá librerías como pandas, numpy,          scikit-learn, etc.

4. **Configuración Inicial de Datos**
La API extrae los datos registrados en la cuenta de MyAnimeList del usuario.
> [!Nota] 
> Es necesario que el usuario tenga cuenta pública de MyAnimeList.
## 🧪 Tests

Para garantizar que el aislamiento del motor de recomendación funciona correctamente sin depender de los datos de producción (evitando la "fuga de mocks"), puedes ejecutar los tests.

**Back-End**
```bash
python -m pytest src/tests/run_tests.py
```

**Front-End**
```bash
flutter test
```
## 🐛 Troubleshooting

| Problema | Solución                |
| :-------- | :-|
| `"No se pudo descargar lista"` | Lista MAL debe ser públic |
| `"Timeout en API"` | Primera ejecución tarda ~5 min |
| `"No hay recomendaciones"` | Mínimo 5 animes puntuados |



## 📄 Licencia

[Licencia de uso personal / Personal Use License](https://github.com/SrAlex16/Anime_recommender/blob/main/LICENSE.md#licencia-de-uso-personal--personal-use-license)


## 👨🏼‍💼Authors

- [@SrAlex16](https://github.com/SrAlex16)


## 🔗 Links
[![Portfolio](https://img.shields.io/badge/my_portfolio-1?style=for-the-badge&logo=ko-fi&logoColor=black)](https://www.aletm.com)

[![LinkedIn](https://img.shields.io/badge/linkedIn-1DA1F2?style=for-the-badge&logo=linkedin&logoColor=white)](https://linkedin.com/)

