# src/tests/run_tests.py

import os
import subprocess
import sys

# --- CONFIGURACIÓN DE RUTAS ---
# SCRIPT_DIR: ~/anime_recommender/src/tests/
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# PROJECT_ROOT: ~/anime_recommender/ (Subir dos niveles desde src/tests)
PROJECT_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR)) 

# LOG_DIR: ~/anime_recommender/logs/
LOG_DIR = os.path.join(PROJECT_ROOT, "logs")
# LOG_FILE: ~/anime_recommender/logs/tests.log
LOG_FILE = os.path.join(LOG_DIR, "tests.log")

def run_tests_and_log():
    """Ejecuta Pytest con -s y redirige toda la salida a tests.log."""
    
    # 1. Crear el directorio de logs si no existe
    os.makedirs(LOG_DIR, exist_ok=True)
    
    # El comando Pytest
    # '-s' es CRÍTICO: Deshabilita la captura de stdout, forzando los 'print()' al log.
    # El comando se ejecutará desde la raíz del proyecto para resolver rutas fácilmente.
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "-v",
        "-s",
        # No especificamos ruta de tests, Pytest buscará automáticamente desde la raíz.
    ]

    print(f"--- 🛠️  Ejecutando tests y guardando salida en {LOG_FILE} ---")
    
    try:
        # 2. Abrir el archivo de log para escribir
        with open(LOG_FILE, "w", encoding="utf-8") as log_file:
            # 3. Ejecutar Pytest
            # Redirigimos la salida estándar (stdout) y de error (stderr) al archivo.
            result = subprocess.run(
                cmd,
                cwd=PROJECT_ROOT, # Ejecutar desde la raíz para el contexto de pytest
                stdout=log_file,
                stderr=subprocess.STDOUT, # Redirige stderr a stdout (al log_file)
                check=False # Permite que el script termine aunque haya tests fallidos
            )
            
        print("✅ Tests finalizados. La salida completa se ha guardado automáticamente en el log.")
        
        # 4. Mostrar el resumen de los resultados de forma amigable desde el log
        print("\n--- Resumen de Resultados ---")
        try:
            with open(LOG_FILE, "r", encoding="utf-8") as log_file:
                # Muestra las últimas 10 líneas (donde está el resumen de Pytest)
                lines = log_file.readlines()
                for line in lines[-10:]:
                    print(line.strip())
        except Exception:
             print(f"No se pudo leer el resumen del log: {LOG_FILE}")
        
        print("---------------------------\n")

    except FileNotFoundError:
        print(f"❌ Error Crítico: El ejecutable de Python o el módulo Pytest no se encontró. Asegúrate de que tu entorno virtual esté activado.")

if __name__ == "__main__":
    run_tests_and_log()