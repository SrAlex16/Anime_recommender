import os
import subprocess
import sys
import time
import requests

# --- CONFIGURACIÓN DE RUTAS ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR)) 
LOG_DIR = os.path.join(PROJECT_ROOT, "logs")
LOG_FILE = os.path.join(LOG_DIR, "tests.log")

# Configuración de la API
API_HOST = "localhost"
API_PORT = 5000
BASE_URL = f"http://{API_HOST}:{API_PORT}"

def wait_for_server(timeout=10):
    """Espera a que el servidor de la API esté disponible"""
    print("⏳ Esperando a que el servidor de la API esté listo...")
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            response = requests.get(f"{BASE_URL}/health", timeout=2)
            if response.status_code == 200:
                print("✅ Servidor de API detectado y funcionando")
                return True
        except requests.exceptions.RequestException:
            pass
        
        time.sleep(1)
    
    print("❌ Timeout: No se pudo conectar al servidor de API")
    return False

def start_api_server():
    """Inicia el servidor de la API en segundo plano"""
    api_dir = os.path.join(PROJECT_ROOT, "src", "api")
    api_script = os.path.join(api_dir, "app.py")
    
    if not os.path.exists(api_script):
        print("❌ No se encontró el script de la API: app.py")
        return None
    
    print("🚀 Iniciando servidor de API...")
    
    try:
        # Iniciar el servidor en segundo plano
        process = subprocess.Popen(
            [sys.executable, api_script],
            cwd=api_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Dar tiempo para que el servidor se inicie
        time.sleep(3)
        
        if wait_for_server():
            print("✅ Servidor de API iniciado correctamente")
            return process
        else:
            print("❌ No se pudo iniciar el servidor de API")
            process.terminate()
            return None
            
    except Exception as e:
        print(f"❌ Error al iniciar el servidor de API: {e}")
        return None

def stop_api_server(process):
    """Detiene el servidor de la API"""
    if process:
        print("🛑 Deteniendo servidor de API...")
        process.terminate()
        try:
            process.wait(timeout=5)
            print("✅ Servidor de API detenido")
        except subprocess.TimeoutExpired:
            process.kill()
            print("⚠️  Servidor de API forzado a detenerse")

def run_api_tests():
    """Ejecuta tests específicos de la API"""
    print("\n--- 🧪 Ejecutando Tests de API ---")
    
    # Importar y ejecutar los tests de API
    test_api_path = os.path.join(SCRIPT_DIR, "test_api.py")
    
    if not os.path.exists(test_api_path):
        print("❌ No se encontró test_api.py")
        return False
    
    try:
        # Ejecutar tests de API específicamente
        result = subprocess.run(
            [sys.executable, test_api_path],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True
        )
        
        print("Salida de tests de API:")
        print(result.stdout)
        if result.stderr:
            print("Errores:")
            print(result.stderr)
            
        return result.returncode == 0
        
    except Exception as e:
        print(f"❌ Error ejecutando tests de API: {e}")
        return False

def run_pytest_tests():
    """Ejecuta todos los tests con Pytest"""
    print("\n--- 🧪 Ejecutando Todos los Tests con Pytest ---")
    
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "-v",
        "-s",
    ]

    try:
        with open(LOG_FILE, "w", encoding="utf-8") as log_file:
            result = subprocess.run(
                cmd,
                cwd=PROJECT_ROOT,
                stdout=log_file,
                stderr=subprocess.STDOUT,
                check=False
            )
            
        print("✅ Tests finalizados. Salida completa guardada en el log.")
        
        # Mostrar resumen
        print("\n--- Resumen de Resultados ---")
        try:
            with open(LOG_FILE, "r", encoding="utf-8") as log_file:
                lines = log_file.readlines()
                for line in lines[-15:]:  # Mostrar últimas 15 líneas
                    print(line.strip())
        except Exception:
            print(f"No se pudo leer el resumen del log: {LOG_FILE}")
        
        print("---------------------------\n")
        
        return result.returncode == 0
        
    except FileNotFoundError:
        print("❌ Error: Python o Pytest no encontrados")
        return False

def run_tests_and_log():
    """Ejecuta todos los tests incluyendo la API"""
    
    # Crear directorio de logs
    os.makedirs(LOG_DIR, exist_ok=True)
    
    print("--- 🛠️  Ejecutando Suite Completa de Tests ---")
    
    # Iniciar servidor de API
    api_process = start_api_server()
    
    success = True
    
    try:
        # 1. Ejecutar tests de API específicos
        if api_process:
            api_success = run_api_tests()
            if not api_success:
                success = False
                print("❌ Tests de API fallaron")
        else:
            success = False
            print("❌ No se pudo ejecutar tests de API - servidor no disponible")
        
        # 2. Ejecutar todos los tests con Pytest (incluyendo API nuevamente)
        pytest_success = run_pytest_tests()
        if not pytest_success:
            success = False
            print("❌ Algunos tests de Pytest fallaron")
        
        # Resultado final
        if success:
            print("🎉 ¡Todos los tests pasaron exitosamente!")
        else:
            print("💥 Algunos tests fallaron. Revisa el log para más detalles.")
            
    finally:
        # Siempre detener el servidor
        stop_api_server(api_process)

if __name__ == "__main__":
    run_tests_and_log()