#!/usr/bin/env python
"""
Simple script to start API server
"""
import sys
import os
from pathlib import Path

# Add current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

# Ensure we're using the virtual environment
venv_path = Path(__file__).parent / "venv"
if venv_path.exists():
    # Add venv site-packages to path
    site_packages = venv_path / "lib" / "python3.13" / "site-packages"
    if site_packages.exists():
        sys.path.insert(0, str(site_packages))
    
    # Set environment variables for virtual environment
    os.environ["VIRTUAL_ENV"] = str(venv_path)
    os.environ["PATH"] = str(venv_path / "bin") + os.pathsep + os.environ.get("PATH", "")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.server:app", host="0.0.0.0", port=8000, reload=False)

