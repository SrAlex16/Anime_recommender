# wsgi.py (opcional - solo si lo necesitas)
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from api.app import create_app

app = create_app()