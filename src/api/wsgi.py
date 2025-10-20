# wsgi.py (en la RAIZ del proyecto)
import os
import sys

# Añadir el directorio actual al path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from app import app

if __name__ == "__main__":
    app.run()