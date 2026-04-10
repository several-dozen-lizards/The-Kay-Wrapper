"""
Voxtral TTS Setup Helper

Checks system readiness for running Voxtral-4B-TTS locally.
Run: python voxtral_setup.py
"""
import subprocess
import sys
import os

def check_gpu():
    """Check GPU VRAM availability."""
    print("=" * 60)
    print("GPU CHECK")
    print("=" * 60)
    try:
        import torch
        if torch.cuda.is_available():
            for i in range(torch.cuda.device_count()):
                name = torch.cuda.get_device_name(i)
                total = torch.cuda.get_device_properties(i).total_mem / 1024**3
                print(f"  GPU {i}: {name}")
                print(f"    Total VRAM: {total:.1f} GB")
            # Check what's currently using VRAM
            allocated = torch.cuda.memory_allocated(i) / 1024**3
            print(f"    Currently allocated: {allocated:.1f} GB")
            print(f"    Available: {total - allocated:.1f} GB")
            print()
            if total >= 16:
                print(f"    ✅ Enough VRAM for Voxtral BF16 (~8GB)")
            elif total >= 8:
                print(f"    ⚠️  Tight — may need quantization or to pause Ollama")
            else:
                print(f"    ❌ Need >=8GB VRAM for Voxtral")
        else:
            print("  ❌ No CUDA GPU detected")
    except ImportError:
        print("  ⚠️  torch not installed — run: pip install torch")
    print()

def check_ollama():
    """Check if Ollama is running and what it's using."""
    print("=" * 60)
    print("OLLAMA CHECK")
    print("=" * 60)
    try:
        import httpx
        resp = httpx.get("http://localhost:11434/api/tags", timeout=3.0)
        if resp.status_code == 200:
            models = resp.json().get("models", [])
            print(f"  ✅ Ollama running with {len(models)} models loaded")
            for m in models[:5]:
                print(f"    - {m.get('name', '?')}")
        else:
            print(f"  ⚠️  Ollama responded with {resp.status_code}")
    except Exception:
        print("  ℹ️  Ollama not running (that's fine)")
    print()

def check_vllm():
    """Check if vllm/vllm-omni are installed."""
    print("=" * 60)
    print("VLLM CHECK")
    print("=" * 60)
    try:
        import vllm
        print(f"  ✅ vllm installed: {vllm.__version__}")
    except ImportError:
        print("  ❌ vllm not installed")
        print("     Run: pip install vllm")
    
    try:
        import vllm_omni
        print(f"  ✅ vllm-omni installed")
    except ImportError:
        print("  ❌ vllm-omni not installed")
        print("     Run: pip install git+https://github.com/vllm-project/vllm-omni.git")
    print()

def check_voxtral_server():
    """Check if Voxtral server is already running."""
    print("=" * 60)
    print("VOXTRAL SERVER CHECK")
    print("=" * 60)
    try:
        import httpx
        resp = httpx.get("http://localhost:8200/health", timeout=3.0)
        if resp.status_code == 200:
            print("  ✅ Voxtral server running on port 8200!")
        else:
            print(f"  ⚠️  Server responded with {resp.status_code}")
    except Exception:
        print("  ℹ️  Voxtral server not running yet")
        print("     To start:")
        print("     python -m vllm_omni.entrypoints.openai.api_server \\")
        print("       --model mistralai/Voxtral-4B-TTS-2603 \\")
        print("       --host 0.0.0.0 --port 8200 \\")
        print("       --max-model-len 4096")
    print()

def print_summary():
    print("=" * 60)
    print("NEXT STEPS")
    print("=" * 60)
    print("""
1. Install vllm + vllm-omni:
   pip install vllm
   pip install git+https://github.com/vllm-project/vllm-omni.git

2. Start the Voxtral server:
   python -m vllm_omni.entrypoints.openai.api_server \\
     --model mistralai/Voxtral-4B-TTS-2603 \\
     --host 0.0.0.0 --port 8200 \\
     --max-model-len 4096
   (First run downloads ~8GB model from HuggingFace)

3. Optional: Add Kay's voice reference
   Place a 3-10 second WAV clip at:
   D:\\Wrappers\\nexus\\voice_references\\kay_ref.wav

4. Start the Nexus — Voxtral auto-detected!
   The VoiceService checks for Voxtral at startup.
   If running, it becomes the primary TTS backend.
   If not running, falls back to ElevenLabs/Edge/Piper.

5. Test with: python voxtral_test.py
""")

if __name__ == "__main__":
    print()
    print("  🐉 Voxtral TTS Setup Check for Nexus")
    print()
    check_gpu()
    check_ollama()
    check_vllm()
    check_voxtral_server()
    print_summary()
