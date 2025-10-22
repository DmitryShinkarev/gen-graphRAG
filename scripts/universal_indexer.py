#!/usr/bin/env python3
"""
Universal Java Project Indexer
Works with any Java project by creating a .continueignore to prevent ByteString errors
"""
import os
import sys
import json
from pathlib import Path

# Try to import requests, if not available, show helpful message
try:
    import requests
except ImportError:
    print("❌ requests module not found!")
    print("💡 Install it with: pip install requests")
    print("💡 Or use the virtual environment:")
    print("   cd /Users/dsh/continue-unit-test-java/python")
    print("   source venv/bin/activate")
    print("   python ../universal_indexer.py")
    sys.exit(1)

API_BASE = "http://localhost:8000"

def create_universal_continueignore(project_path):
    """Create a universal .continueignore file for any Java project"""
    
    continueignore_content = """# Universal Continue.dev ignore file
# Prevents ByteString errors in any Java project

# Binary and compiled files
*.class
*.jar
*.war
*.ear
*.aar
*.apk
*.dex
*.pyc
*.pyo
*.pyd
*.so
*.dll
*.exe
*.o
*.obj
*.bin
*.dat
*.db
*.sqlite
*.sqlite3

# Archives
*.zip
*.rar
*.7z
*.tar
*.tar.gz
*.tar.bz2
*.gz
*.bz2

# Build directories
**/target/
**/build/
**/out/
**/bin/
**/obj/
**/classes/
**/generated/

# Cache directories
**/__pycache__/
**/node_modules/
**/.git/
**/.svn/
**/.idea/
**/.vscode/
**/venv/
**/env/

# Logs and temporary files
**/*.log
**/logs/
**/tmp/
**/temp/
**/*.tmp
**/*.swp
**/*.swo
**/*~
**/.DS_Store
**/Thumbs.db

# Large files
**/*.pdf
**/*.doc
**/*.docx
**/*.jpg
**/*.png
**/*.mp3
**/*.mp4

# Lock files
**/package-lock.json
**/yarn.lock
**/Pipfile.lock
**/composer.lock

# Test reports
**/coverage/
**/test-results/
**/junit.xml
**/surefire-reports/

# Docker files
**/Dockerfile*
**/docker-compose*

# Environment files
**/.env
**/.env.*
**/secrets/
**/*.key
**/*.pem

# OS specific
**/.directory
**/Icon
**/._*
**/$RECYCLE.BIN/
"""
    
    ignore_path = Path(project_path) / ".continueignore"
    
    try:
        with open(ignore_path, 'w', encoding='utf-8') as f:
            f.write(continueignore_content)
        print(f"✅ Created .continueignore at: {ignore_path}")
        return True
    except Exception as e:
        print(f"❌ Failed to create .continueignore: {e}")
        return False

def check_api_health():
    """Check if the Java Test Agent API is running"""
    try:
        response = requests.get(f"{API_BASE}/health", timeout=5)
        response.raise_for_status()
        
        health = response.json()
        print(f"✅ API is healthy: {health['status']}")
        print(f"📊 Components: graph={health['components']['graph']}, embedder={health['components']['embedder']}")
        return True
        
    except requests.exceptions.ConnectionError:
        print(f"❌ Cannot connect to API at {API_BASE}")
        print("💡 Start the API first:")
        print("   cd /Users/dsh/continue-unit-test-java/python")
        print("   source venv/bin/activate")
        print("   python start_server.py")
        return False
        
    except Exception as e:
        print(f"❌ API health check failed: {e}")
        return False

def index_project(project_path):
    """Index a Java project"""
    abs_path = str(Path(project_path).absolute())
    url = f"{API_BASE}/index"
    
    params = {"project_path": abs_path}
    
    print(f"🔍 Indexing: {abs_path}")
    print(f"📡 API: {url}")
    
    try:
        response = requests.get(url, params=params, timeout=60)
        response.raise_for_status()
        
        result = response.json()
        print("\n✅ Indexing successful!")
        print(f"📊 Indexed files: {result.get('indexed_files', 0)}")
        print(f"🏗️  Parsed classes: {result.get('parsed_classes', 0)}")
        print(f"⚙️  Methods: {result.get('methods_count', 0)}")
        print(f"⏱️  Duration: {result.get('duration', 0):.2f}s")
        
        return result
        
    except requests.exceptions.ConnectionError:
        print(f"\n❌ Cannot connect to {url}")
        return None
        
    except requests.exceptions.Timeout:
        print("\n❌ Request timeout - project is large")
        return None
        
    except requests.exceptions.HTTPError as e:
        print(f"\n❌ HTTP Error: {e}")
        try:
            error = response.json()
            print(json.dumps(error, indent=2))
        except:
            print(response.text)
        return None

def get_stats():
    """Get indexing statistics"""
    url = f"{API_BASE}/api/stats"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        stats = response.json()
        print("\n📈 Statistics:")
        print(json.dumps(stats, indent=2))
        return stats
        
    except Exception as e:
        print(f"❌ Error getting stats: {e}")
        return None

def main():
    """Main function"""
    print("=" * 70)
    print("🚀 Universal Java Project Indexer")
    print("   Works with any Java project!")
    print("=" * 70)
    
    # Get project path
    if len(sys.argv) > 1:
        project_path = sys.argv[1]
    else:
        project_path = input("\n📁 Enter Java project path: ").strip()
    
    if not project_path:
        print("❌ No path provided")
        return
    
    project_path = os.path.expanduser(project_path)
    
    if not os.path.exists(project_path):
        print(f"❌ Path does not exist: {project_path}")
        return
    
    if not os.path.isdir(project_path):
        print(f"❌ Path is not a directory: {project_path}")
        return
    
    print(f"\n📂 Project: {project_path}")
    
    # Step 1: Create .continueignore
    print("\n" + "=" * 50)
    print("📝 Step 1: Creating .continueignore")
    print("=" * 50)
    
    if not create_universal_continueignore(project_path):
        return
    
    # Step 2: Check API health
    print("\n" + "=" * 50)
    print("🏥 Step 2: Checking API health")
    print("=" * 50)
    
    if not check_api_health():
        return
    
    # Step 3: Index project
    print("\n" + "=" * 50)
    print("🔍 Step 3: Indexing project")
    print("=" * 50)
    
    result = index_project(project_path)
    
    if result:
        # Step 4: Show stats
        print("\n" + "=" * 50)
        print("📊 Step 4: Getting statistics")
        print("=" * 50)
        
        get_stats()
        
        # Step 5: Instructions
        print("\n" + "=" * 50)
        print("🎯 Next Steps")
        print("=" * 50)
        
        print("\n✅ Project indexed successfully!")
        print("\n🚀 Now you can:")
        print("   1. Open VS Code: code " + project_path)
        print("   2. Open any Java file")
        print("   3. Select a method")
        print("   4. Open Continue chat (Cmd+L)")
        print("   5. Ask: 'Generate JUnit test for this method'")
        
        print("\n💡 The .continueignore file will prevent ByteString errors!")
        print("   Continue.dev will skip binary files and focus on Java source code.")
        
    else:
        print("\n❌ Indexing failed. Check the errors above.")

if __name__ == "__main__":
    main()
