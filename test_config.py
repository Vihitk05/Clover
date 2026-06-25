#!/usr/bin/env python
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.settings import config

def test_config():
    """Test the configuration"""
    print("Testing configuration...")
    
    # Display current config
    config.display()
    
    # Validate config
    if config.validate():
        print("\n✅ Configuration is valid!")
        
        # Test database URL construction
        print(f"\nDatabase URL: {config.DATABASE_URL}")
        print(f"Redis URL: {config.REDIS_URL}")
        
        return True
    else:
        print("\n❌ Configuration validation failed!")
        return False

if __name__ == "__main__":
    success = test_config()
    sys.exit(0 if success else 1)