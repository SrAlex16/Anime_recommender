# test_pipeline.py
import subprocess
import sys
import os

def test_pipeline():
    username = "SrAlex16"
    
    # Ejecutar el script directamente
    result = subprocess.run([
        sys.executable, 
        "src/services/get_recommendations_for_user.py", 
        username
    ], capture_output=True, text=True, cwd=os.getcwd())
    
    print(f"Return code: {result.returncode}")
    print(f"STDOUT: {result.stdout}")
    print(f"STDERR: {result.stderr}")

if __name__ == "__main__":
    test_pipeline()