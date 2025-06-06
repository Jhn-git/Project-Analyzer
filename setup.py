#!/usr/bin/env python3
"""
Setup script for Project Analyzer
This script helps users get started quickly with Project Analyzer
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def check_python_version():
    """Check if Python version is 3.8 or higher"""
    if sys.version_info < (3, 8):
        print("❌ Error: Python 3.8 or higher is required")
        print(f"   Current version: {sys.version}")
        return False
    print(f"✅ Python {sys.version.split()[0]} detected")
    return True

def install_dependencies():
    """Install required dependencies"""
    print("\n📦 Installing dependencies...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError:
        print("❌ Failed to install dependencies")
        return False

def setup_env_file():
    """Set up the .env file"""
    env_file = Path(".env")
    env_example = Path(".env.example")
    
    if env_file.exists():
        print("✅ .env file already exists")
        return True
    
    if env_example.exists():
        shutil.copy(env_example, env_file)
        print("✅ Created .env file from template")
        print("📝 Please edit .env and add your Google API key")
        return True
    else:
        print("❌ .env.example not found")
        return False

def test_installation():
    """Test if the installation works"""
    print("\n🧪 Testing installation...")
    try:
        result = subprocess.run([sys.executable, "project_analyzer.py", "--help"], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Project Analyzer is working correctly")
            return True
        else:
            print("❌ Project Analyzer test failed")
            print(result.stderr)
            return False
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

def main():
    """Main setup function"""
    print("🔍 Project Analyzer Setup")
    print("=" * 30)
    
    if not check_python_version():
        sys.exit(1)
    
    if not install_dependencies():
        sys.exit(1)
    
    if not setup_env_file():
        print("⚠️  Warning: .env setup failed, AI features won't work without API key")
    
    if not test_installation():
        sys.exit(1)
    
    print("\n🎉 Setup completed successfully!")
    print("\n📖 Quick start:")
    print("   python project_analyzer.py")
    print("   python project_analyzer.py --markdown")
    print("   python project_analyzer.py --help")
    print("\n🔗 Don't forget to:")
    print("   1. Add your Google API key to .env for AI features")
    print("   2. Check out README.md for detailed usage")

if __name__ == "__main__":
    main()
