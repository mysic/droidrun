#!/usr/bin/env python3
"""Test script to verify Aliyun Bailian LLM configuration."""

import sys
import os
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent))

from droidrun.config_manager.loader import ConfigLoader

def test_config():
    """Test loading config and checking LLM settings."""
    print("Loading configuration...")
    
    # 使用项目目录下的配置文件
    config_path = Path(__file__).parent / "droidrun" / "config.yaml"
    print(f"Config file: {config_path}")
    print(f"Exists: {config_path.exists()}\n")
    
    config = ConfigLoader.load(str(config_path))
    
    print("LLM Profiles:")
    for name, profile in config.llm_profiles.items():
        print(f"  {name}:")
        print(f"    Provider: {profile.provider}")
        print(f"    Model: {profile.model}")
        print(f"    Base URL: {profile.base_url}")
        print(f"    Temperature: {profile.temperature}")
        if profile.kwargs.get('api_key'):
            print(f"    API Key: {'*' * 8} (set)")
        else:
            print(f"    API Key: Not set in kwargs")
        print()
    
    # 检查是否配置正确
    manager_profile = config.llm_profiles.get('manager')
    if manager_profile:
        if manager_profile.provider == 'OpenAILike':
            print("✓ Configuration is correct! Using OpenAILike provider.")
            if 'qwen' in manager_profile.model.lower():
                print("✓ Using Qwen model from Aliyun Bailian.")
            if manager_profile.base_url and 'aliyuncs.com' in manager_profile.base_url:
                print("✓ Base URL points to Aliyun Bailian.")
            return True
        else:
            print(f"✗ Still using {manager_profile.provider}, not configured for Aliyun Bailian.")
            return False
    
    return False

if __name__ == "__main__":
    success = test_config()
    sys.exit(0 if success else 1)
