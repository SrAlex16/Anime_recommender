import sys
import os

# Añadir el directorio src al path para los imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from api.app import app

if __name__ == "__main__":
    app.run()