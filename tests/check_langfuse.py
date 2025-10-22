#!/usr/bin/env python3
"""
Quick script to check Langfuse configuration status.
"""

import os
from pathlib import Path

def check_env_file():
    """Check if .env file exists and contains Langfuse keys"""
    env_path = Path(__file__).parent / ".env"
    
    if not env_path.exists():
        print("❌ .env file not found")
        print("   Run: cp .env.example .env")
        return False
    
    print("✅ .env file exists")
    
    # Read .env file
    with open(env_path) as f:
        env_content = f.read()
    
    # Check for keys
    has_public = "LANGFUSE_PUBLIC_KEY=" in env_content
    has_secret = "LANGFUSE_SECRET_KEY=" in env_content
    
    public_set = False
    secret_set = False
    
    for line in env_content.split('\n'):
        line = line.strip()
        if line.startswith('LANGFUSE_PUBLIC_KEY=') and not line.startswith('#'):
            value = line.split('=', 1)[1].strip()
            public_set = bool(value and value != '')
        elif line.startswith('LANGFUSE_SECRET_KEY=') and not line.startswith('#'):
            value = line.split('=', 1)[1].strip()
            secret_set = bool(value and value != '')
    
    if public_set and secret_set:
        print("✅ Langfuse keys are configured")
        return True
    elif not public_set and not secret_set:
        print("⚠️  Langfuse keys are not configured")
        print("   Get keys from: https://cloud.langfuse.com")
        print("   Add them to .env file:")
        print("   - LANGFUSE_PUBLIC_KEY=pk-lf-...")
        print("   - LANGFUSE_SECRET_KEY=sk-lf-...")
        return False
    else:
        print("⚠️  Langfuse keys are partially configured")
        if not public_set:
            print("   Missing: LANGFUSE_PUBLIC_KEY")
        if not secret_set:
            print("   Missing: LANGFUSE_SECRET_KEY")
        return False

def check_langfuse_package():
    """Check if langfuse package is installed"""
    try:
        import langfuse
        print(f"✅ Langfuse package installed (version {langfuse.__version__})")
        return True
    except ImportError:
        print("❌ Langfuse package not installed")
        print("   Run: pip install langfuse==2.50.2")
        return False

def check_openai_key():
    """Check if OpenAI key is configured"""
    env_path = Path(__file__).parent / ".env"
    
    if not env_path.exists():
        return False
    
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line.startswith('OPENAI_API_KEY=') and not line.startswith('#'):
                value = line.split('=', 1)[1].strip()
                if value and value != '' and not value.startswith('sk-your-'):
                    print("✅ OpenAI API key is configured")
                    return True
    
    print("⚠️  OpenAI API key not configured")
    print("   Add it to .env file:")
    print("   OPENAI_API_KEY=sk-...")
    return False

def main():
    print("=" * 60)
    print("🔍 Langfuse Configuration Check")
    print("=" * 60)
    print()
    
    # Check package
    package_ok = check_langfuse_package()
    print()
    
    # Check .env file
    env_ok = check_env_file()
    print()
    
    # Check OpenAI key
    openai_ok = check_openai_key()
    print()
    
    print("=" * 60)
    
    if package_ok and env_ok and openai_ok:
        print("✅ Langfuse is fully configured and ready to use!")
        print()
        print("Next steps:")
        print("1. Start the API server: cd python && source venv/bin/activate && python api/server.py")
        print("2. Check logs for: 'Initializing ... with Langfuse tracing enabled'")
        print("3. View traces at: https://cloud.langfuse.com")
    else:
        print("⚠️  Configuration incomplete")
        print()
        print("Next steps:")
        if not package_ok:
            print("1. Install Langfuse: pip install langfuse==2.50.2")
        if not env_ok:
            print("2. Add Langfuse keys to .env file")
            print("   Get keys from: https://cloud.langfuse.com")
        if not openai_ok:
            print("3. Add OpenAI API key to .env file")
        print()
        print("📖 Full guide: docs/LANGFUSE_SETUP.md")
    
    print("=" * 60)

if __name__ == "__main__":
    main()

