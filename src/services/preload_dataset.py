# Preload_dataset.py

import subprocess
import sys

sys.path.append('src')

try:
    from data.fetch_datasets import main as fetch_main
    print("📥 Precargando dataset de AniList...")
    fetch_main()
    print("✅ Precarga completada exitosamente")
except Exception as e:
    print(f"⚠️ Precarga falló: {e}. Se intentará en el primer request.")

def preload_static_data():
    """Precarga los datos estáticos de AniList al desplegar"""
    print("📥 Precargando dataset base de AniList...")
    
    try:
        # Ejecutar solo fetch_datasets.py una vez
        result = subprocess.run([
            sys.executable, 
            "src/data/fetch_datasets.py"
        ], capture_output=True, text=True, timeout=120)
        
        if result.returncode == 0:
            print("✅ Dataset base precargado exitosamente")
            return True
        else:
            print(f"❌ Error: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Error en precarga: {e}")
        return False

if __name__ == "__main__":
    preload_static_data()