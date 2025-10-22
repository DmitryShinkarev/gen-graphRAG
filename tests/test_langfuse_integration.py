#!/usr/bin/env python3
"""
Test script to verify Langfuse integration.
This script simulates an agent making an LLM call with Langfuse tracing.
"""

import asyncio
import sys
from pathlib import Path

# Add python directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "python"))

async def test_langfuse_integration():
    """Test Langfuse integration with a simple agent"""
    print("=" * 70)
    print("🧪 Testing Langfuse Integration")
    print("=" * 70)
    print()
    
    try:
        from config import get_settings
        from agents.base import BaseJavaAgent, AgentState, BaseTool
        
        settings = get_settings()
        print("✅ Settings loaded successfully")
        print()
        
        # Check Langfuse configuration
        if settings.monitoring.langfuse_public_key and settings.monitoring.langfuse_secret_key:
            print("✅ Langfuse keys are configured")
            print(f"   Host: {settings.monitoring.langfuse_host}")
        else:
            print("⚠️  Langfuse keys not configured")
            print("   The test will run but traces won't be sent to Langfuse")
        print()
        
        # Create a test agent
        class TestTool(BaseTool):
            name = "test_tool"
            description = "A test tool for demonstration"
            
            async def execute(self, **kwargs):
                return {"result": "Tool executed successfully"}
        
        class TestAgent(BaseJavaAgent):
            async def execute(self, state: AgentState) -> AgentState:
                """Execute a test LLM call"""
                messages = [
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": "Say hello in one sentence."}
                ]
                
                print("📤 Sending test message to LLM...")
                response = await self.call_llm(messages, max_tokens=50)
                print(f"📥 Received response: {response}")
                print()
                
                state.steps_completed.append("Test LLM call completed")
                return state
        
        # Create and run test agent
        print("🤖 Creating test agent...")
        agent = TestAgent(
            name="TestAgent",
            role="Testing Langfuse integration",
            tools=[TestTool()],
            temperature=0.7
        )
        print()
        
        print("🚀 Executing test agent...")
        print("-" * 70)
        state = AgentState()
        result_state = await agent.execute(state)
        print("-" * 70)
        print()
        
        print("✅ Test completed successfully!")
        print()
        
        if settings.monitoring.langfuse_public_key and settings.monitoring.langfuse_secret_key:
            print("📊 Check your Langfuse dashboard:")
            print(f"   👉 {settings.monitoring.langfuse_host}")
            print()
            print("   You should see a trace named: 'TestAgent_llm_call'")
            print("   With metadata:")
            print("   - agent_name: TestAgent")
            print("   - agent_role: Testing Langfuse integration")
        else:
            print("⚠️  To see traces in Langfuse:")
            print("   1. Get keys from: https://cloud.langfuse.com")
            print("   2. Add them to .env file")
            print("   3. Run this test again")
        
        print()
        print("=" * 70)
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print()
        print("Make sure you have:")
        print("1. Activated virtual environment: source python/venv/bin/activate")
        print("2. Installed dependencies: pip install -r python/requirements.txt")
        sys.exit(1)
        
    except ValueError as e:
        print(f"❌ Configuration error: {e}")
        print()
        print("Please configure your .env file with:")
        print("1. OPENAI_API_KEY=sk-...")
        print("2. LANGFUSE_PUBLIC_KEY=pk-lf-... (optional)")
        print("3. LANGFUSE_SECRET_KEY=sk-lf-... (optional)")
        sys.exit(1)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

def main():
    """Main entry point"""
    try:
        asyncio.run(test_langfuse_integration())
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(0)

if __name__ == "__main__":
    main()

