#!/usr/bin/env python3
"""Test script to verify LLM connection with SSL disabled."""

import sys
import asyncio
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent))

from droidrun.config_manager.loader import ConfigLoader
from droidrun.agent.utils.llm_loader import load_agent_llms

async def test_llm_connection():
    """Test loading and connecting to LLM."""
    print("=" * 60)
    print("Testing LLM Connection")
    print("=" * 60)
    
    # Load config
    print("\n1. Loading configuration...")
    config = ConfigLoader.load()
    print("✓ Configuration loaded")
    
    # Load LLMs
    print("\n2. Loading LLMs...")
    try:
        llms = load_agent_llms(config)
        print(f"✓ Loaded {len(llms)} LLMs:")
        for name, llm in llms.items():
            print(f"   - {name}: {type(llm).__name__}")
    except Exception as e:
        print(f"✗ Failed to load LLMs: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test a simple chat
    print("\n3. Testing LLM connection with simple chat...")
    try:
        from llama_index.core.base.llms.types import ChatMessage
        
        manager_llm = llms.get('manager')
        if not manager_llm:
            print("✗ Manager LLM not found")
            return False
        
        messages = [
            ChatMessage(role="system", content="You are a helpful assistant."),
            ChatMessage(role="user", content="Say hello in one word.")
        ]
        
        print("   Sending request to Aliyun Bailian...")
        response = await manager_llm.achat(messages=messages)
        print(f"✓ Response received: {response.message.content}")
        return True
        
    except Exception as e:
        print(f"✗ LLM connection failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    try:
        success = asyncio.run(test_llm_connection())
        print("\n" + "=" * 60)
        if success:
            print("✅ LLM connection test PASSED!")
        else:
            print("❌ LLM connection test FAILED!")
        print("=" * 60)
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
