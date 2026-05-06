#!/usr/bin/env python3
"""Test script to verify config loading and SSL settings."""

import sys
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent))

from droidrun.config_manager.loader import ConfigLoader

def test_config():
    """Test loading config and checking settings."""
    print("=" * 60)
    print("Testing Configuration Loading")
    print("=" * 60)
    
    # Load config
    print("\n1. Loading configuration...")
    config = ConfigLoader.load()
    print("✓ Configuration loaded successfully")
    
    # Check which config file was loaded
    project_config = ConfigLoader.get_project_config_path()
    user_config = ConfigLoader.get_user_config_path()
    
    print(f"\n2. Config file paths:")
    print(f"   Project config: {project_config}")
    print(f"   User config: {user_config}")
    print(f"   Project config exists: {project_config.exists()}")
    print(f"   User config exists: {user_config.exists()}")
    
    # Check LLM profiles
    print(f"\n3. LLM Profiles:")
    for name, profile in config.llm_profiles.items():
        print(f"   {name}:")
        print(f"     Provider: {profile.provider}")
        print(f"     Model: {profile.model}")
        print(f"     Base URL: {profile.base_url}")
        
        # Check if API key is set
        api_key = profile.kwargs.get('api_key', '')
        if api_key:
            print(f"     API Key: {'*' * 8} (set)")
        else:
            print(f"     API Key: Not set")
        
        # Check SSL verification
        http_opts = profile.kwargs.get('http_client_options', {})
        verify = http_opts.get('verify', True) if isinstance(http_opts, dict) else True
        print(f"     SSL Verify: {verify}")
        
    # Check agent mode
    print(f"\n4. Agent Settings:")
    print(f"   Reasoning mode: {config.agent.reasoning}")
    if config.agent.reasoning:
        print(f"   → Using Manager + Executor agents")
    else:
        print(f"   → Using FastAgent")
    
    print("\n" + "=" * 60)
    print("Configuration test completed!")
    print("=" * 60)
    
    return True

if __name__ == "__main__":
    try:
        success = test_config()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
