# src/api/wsgi.py
import os
import sys

# Añadir el directorio src al path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app import app

if __name__ == "__main__":
    app.run()