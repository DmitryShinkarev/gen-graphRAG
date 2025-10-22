#!/usr/bin/env python3
"""
Direct test of Langfuse integration
"""
import os
import sys
sys.path.insert(0, "python")

# Load .env file
from dotenv import load_dotenv
load_dotenv()

# Set environment variables explicitly
print("Setting up Langfuse environment...")
print(f"LANGFUSE_PUBLIC_KEY: {os.getenv('LANGFUSE_PUBLIC_KEY', 'NOT SET')[:20]}...")
print(f"LANGFUSE_SECRET_KEY: {os.getenv('LANGFUSE_SECRET_KEY', 'NOT SET')[:20]}...")
print(f"LANGFUSE_HOST: {os.getenv('LANGFUSE_HOST', 'NOT SET')}")
print()

# Test Langfuse import
try:
    from langfuse.openai import AsyncOpenAI as LangfuseAsyncOpenAI
    print("✅ Langfuse package imported successfully")
except ImportError as e:
    print(f"❌ Failed to import Langfuse: {e}")
    sys.exit(1)

# Test creating client
print("\nCreating Langfuse OpenAI client...")
try:
    client = LangfuseAsyncOpenAI()
    print("✅ Langfuse client created successfully")
    print(f"   Client type: {type(client)}")
    print(f"   Has langfuse attr: {hasattr(client, 'langfuse')}")
except Exception as e:
    print(f"❌ Failed to create client: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test making a call
print("\nMaking test LLM call...")
import asyncio

async def test_call():
    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Say 'Langfuse test successful!' in one short sentence."}
            ],
            max_tokens=50,
            name="langfuse_direct_test",  # Trace name
            metadata={"test": "direct_langfuse_test"}  # Metadata
        )
        
        print("✅ LLM call successful!")
        print(f"   Response: {response.choices[0].message.content}")
        print()
        print("═" * 70)
        print("🎉 SUCCESS! Check Langfuse UI:")
        print("   1. Open: https://cloud.langfuse.com")
        print("   2. Select your project")
        print("   3. Go to 'Traces' tab")
        print("   4. Look for trace: 'langfuse_direct_test'")
        print("   ⏰ Wait 10-30 seconds for trace to appear")
        print("═" * 70)
        
    except Exception as e:
        print(f"❌ LLM call failed: {e}")
        import traceback
        traceback.print_exc()

asyncio.run(test_call())
