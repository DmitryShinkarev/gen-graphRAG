#!/usr/bin/env python3
"""
Quick test to verify Langfuse is receiving data.
Run this AFTER starting the API server.
"""

import asyncio
import sys
from pathlib import Path

# Add python directory to path
sys.path.insert(0, str(Path(__file__).parent / "python"))

from agents.base import BaseJavaAgent, AgentState
from config import get_settings

async def test_langfuse_integration():
    """Test that Langfuse is receiving LLM traces"""
    
    print("╔══════════════════════════════════════════════════════════════════╗")
    print("║          🧪 Testing Langfuse Integration (Live Test)            ║")
    print("╚══════════════════════════════════════════════════════════════════╝")
    print()
    
    settings = get_settings()
    
    # Check configuration
    print("1. Checking configuration...")
    
    if not settings.llm.openai_api_key or settings.llm.openai_api_key.startswith("sk-your-"):
        print("   ❌ OpenAI API key not configured")
        return False
    
    print("   ✅ OpenAI API key configured")
    
    langfuse_configured = (
        settings.monitoring.langfuse_public_key and
        settings.monitoring.langfuse_secret_key and
        not settings.monitoring.langfuse_public_key.startswith("pk-lf-your-")
    )
    
    if langfuse_configured:
        print("   ✅ Langfuse keys configured")
    else:
        print("   ⚠️  Langfuse keys not configured (tracing disabled)")
    
    print()
    
    # Create a simple test agent
    print("2. Creating test agent...")
    
    class TestAgent(BaseJavaAgent):
        def __init__(self):
            super().__init__(
                name="TestAgent",
                role="Testing Langfuse integration",
                tools=[]
            )
        
        async def execute(self, state: AgentState) -> AgentState:
            return state
    
    try:
        agent = TestAgent()
        print("   ✅ Agent created successfully")
        
        # Check if Langfuse is enabled
        if hasattr(agent.llm, 'public_key'):
            print("   ✅ Langfuse tracing is ENABLED!")
        else:
            print("   ⚠️  Langfuse tracing is DISABLED (using regular OpenAI client)")
            if not langfuse_configured:
                print("      Reason: Langfuse keys not configured")
        
        print()
        
    except Exception as e:
        print(f"   ❌ Error creating agent: {e}")
        return False
    
    # Make a test LLM call
    print("3. Making test LLM call...")
    
    try:
        test_messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Say 'Hello from Langfuse test!' in one sentence."}
        ]
        
        response = await agent.call_llm(test_messages, max_tokens=50)
        print(f"   ✅ LLM call successful!")
        print(f"   📝 Response: {response[:100]}...")
        print()
        
    except Exception as e:
        print(f"   ❌ Error making LLM call: {e}")
        return False
    
    # Final instructions
    print("═══════════════════════════════════════════════════════════════════")
    print()
    
    if langfuse_configured:
        print("✅ TEST COMPLETED!")
        print()
        print("📊 Next steps:")
        print("   1. Open https://cloud.langfuse.com")
        print("   2. Select your project")
        print("   3. Go to 'Traces' tab")
        print("   4. Look for trace: 'TestAgent_llm_call'")
        print()
        print("   ⏰ Note: There may be a 10-30 second delay before traces appear")
        print()
        print("   If you see the trace, Langfuse is working correctly! 🎉")
    else:
        print("⚠️  TEST COMPLETED (without Langfuse)")
        print()
        print("LLM call worked, but Langfuse tracing is disabled.")
        print("To enable Langfuse:")
        print("   1. Add Langfuse keys to .env file")
        print("   2. Restart the API server")
        print("   3. Run this test again")
    
    print()
    print("═══════════════════════════════════════════════════════════════════")
    
    return True

if __name__ == "__main__":
    try:
        result = asyncio.run(test_langfuse_integration())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

