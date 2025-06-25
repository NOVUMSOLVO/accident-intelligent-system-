#!/usr/bin/env python3
"""
Quick start script for the accident detection system
"""

import subprocess
import sys
import time
from pathlib import Path

def main():
    project_root = Path(__file__).parent
    
    print("Starting Accident Detection System...")
    
    # Check if Docker services are running
    try:
        result = subprocess.run(['docker-compose', 'ps'], 
                              cwd=project_root, capture_output=True, text=True)
        if 'Up' not in result.stdout:
            print("Starting Docker services...")
            subprocess.run(['docker-compose', 'up', '-d'], cwd=project_root, check=True)
            print("Waiting for services to start...")
            time.sleep(30)
    except subprocess.CalledProcessError:
        print("Failed to start Docker services")
        return
    
    # Run the main application
    try:
        if sys.platform == 'win32':
            python_exe = project_root / "venv" / "Scripts" / "python.exe"
        else:
            python_exe = project_root / "venv" / "bin" / "python"
        
        subprocess.run([str(python_exe), "main.py"], cwd=project_root)
    except KeyboardInterrupt:
        print("
Shutting down...")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
