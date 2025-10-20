# src/services/preload_dataset.py
import subprocess
import sys
import os

# Configurar paths para Render
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT_DIR)

def preload_static_data():
    """Precarga los datos estáticos de AniList al desplegar"""
    print("📥 Precargando dataset base de AniList...")
    
    try:
        # Ejecutar fetch_datasets.py
        result = subprocess.run([
            sys.executable, 
            "src/data/fetch_datasets.py"
        ], capture_output=True, text=True, timeout=120, cwd=ROOT_DIR)
        
        print(f"📋 STDOUT: {result.stdout}")
        if result.stderr:
            print(f"📋 STDERR: {result.stderr}")
        
        if result.returncode == 0:
            print("✅ Dataset base precargado exitosamente")
            return True
        else:
            print(f"❌ Error en precarga: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ Timeout en precarga de datos")
        return False
    except Exception as e:
        print(f"❌ Error en precarga: {e}")
        return False

if __name__ == "__main__":
    success = preload_static_data()
    sys.exit(0 if success else 1)