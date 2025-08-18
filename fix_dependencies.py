#!/usr/bin/env python3
"""
Fix script for dependency issues in the AI Coach project
"""
import subprocess
import sys
import os

def run_command(command, description):
    """Run a command and handle errors"""
    print(f"\n🔧 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e}")
        print(f"Error output: {e.stderr}")
        return False

def main():
    """Main fix function"""
    print("🚀 Starting dependency fix for AI Coach project...")
    
    # Change to backend directory
    if os.path.exists('backend'):
        os.chdir('backend')
        print("📁 Changed to backend directory")
    
    # Fix protobuf version conflict
    commands = [
        ("pip uninstall -y protobuf", "Uninstalling existing protobuf"),
        ("pip install protobuf==3.20.3", "Installing compatible protobuf version"),
        ("pip install --upgrade tensorflow", "Upgrading TensorFlow"),
        ("pip install --upgrade mediapipe", "Upgrading MediaPipe"),
        ("pip install librosa soundfile", "Installing audio processing libraries"),
    ]
    
    success_count = 0
    for command, description in commands:
        if run_command(command, description):
            success_count += 1
    
    print(f"\n📊 Completed {success_count}/{len(commands)} fixes")
    
    # Test imports
    print("\n🧪 Testing imports...")
    test_imports = [
        "import numpy",
        "import librosa", 
        "import soundfile",
        "import mediapipe",
        "from app.services.tone_analysis_service import ToneAnalyzer"
    ]
    
    for test_import in test_imports:
        try:
            exec(test_import)
            print(f"✅ {test_import}")
        except Exception as e:
            print(f"❌ {test_import}: {e}")
    
    print("\n🎉 Dependency fix completed!")
    print("\nNext steps:")
    print("1. Try starting your backend: uvicorn main:app --reload")
    print("2. If issues persist, try: pip install -r requirements.txt --force-reinstall")
    print("3. For protobuf issues, set environment variable: PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python")

if __name__ == "__main__":
    main()