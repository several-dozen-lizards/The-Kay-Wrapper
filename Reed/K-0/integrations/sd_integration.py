# integrations/sd_integration.py
"""
Stable Diffusion WebUI API Integration for ReedZero
Allows Kay to generate images locally via AUTOMATIC1111's SD WebUI.

Requirements:
- SD WebUI running with --api flag
- Default endpoint: http://localhost:7860

Usage:
    sd = StableDiffusionIntegration()
    if sd.is_available():
        result = sd.generate_image("a dragon in a dark void")
        # result['path'] = saved image path
        # result['prompt'] = the prompt used
"""

import os
import json
import base64
import requests
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path


class StableDiffusionIntegration:
    """
    Interface to Stable Diffusion WebUI API.
    
    Kay can use this to:
    - Generate images from text prompts
    - Create visualizations of his thoughts/dreams
    - Illustrate conversations
    """
    
    DEFAULT_URL = "http://localhost:7860"
    OUTPUT_DIR = "memory/gallery/generated"
    
    # Default generation parameters (Reed's aesthetic)
    DEFAULT_PARAMS = {
        "steps": 20,
        "cfg_scale": 7.0,
        "width": 512,
        "height": 512,
        "sampler_name": "DPM++ 2M Karras",
        "negative_prompt": "blurry, low quality, distorted, watermark, text, signature"
    }
    
    # Reed's style modifiers - added to prompts automatically
    STYLE_PRESETS = {
        "default": ", digital art, detailed, moody lighting",
        "void": ", dark void background, cosmic, ethereal, pink and black",
        "dragon": ", draconic, scales, mythological, powerful",
        "dream": ", surreal, dreamlike, soft glow, atmospheric",
        "memory": ", nostalgic, faded edges, warm tones",
        "technical": ", technical diagram, blueprint style, clean lines"
    }
    
    def __init__(self, base_url: str = None):
        self.base_url = base_url or os.getenv("SD_WEBUI_URL", self.DEFAULT_URL)
        self.available = False
        self.model_info = {}
        
        # Ensure output directory exists
        os.makedirs(self.OUTPUT_DIR, exist_ok=True)
        
        # Check connection on init
        self._check_connection()
    
    def _check_connection(self) -> bool:
        """Check if SD WebUI is running and accessible."""
        try:
            response = requests.get(f"{self.base_url}/sdapi/v1/sd-models", timeout=5)
            if response.status_code == 200:
                self.available = True
                models = response.json()
                if models:
                    self.model_info = models[0]  # Current/first model
                print(f"[SD] Connected to {self.base_url}")
                if self.model_info:
                    print(f"[SD] Model: {self.model_info.get('model_name', 'unknown')}")
                return True
        except requests.exceptions.ConnectionError:
            print(f"[SD] Not available at {self.base_url}")
        except Exception as e:
            print(f"[SD] Connection error: {e}")
        
        self.available = False
        return False
    
    def is_available(self) -> bool:
        """Check if SD integration is ready to use."""
        if not self.available:
            self._check_connection()
        return self.available
    
    def generate_image(
        self,
        prompt: str,
        style: str = "default",
        negative_prompt: str = None,
        width: int = None,
        height: int = None,
        steps: int = None,
        cfg_scale: float = None,
        seed: int = -1,
        save: bool = True,
        context: str = ""
    ) -> Optional[Dict[str, Any]]:
        """
        Generate an image from a text prompt.
        
        Args:
            prompt: Text description of desired image
            style: Style preset to apply (default, void, dragon, dream, memory, technical)
            negative_prompt: What to avoid in the image
            width: Image width (default 512)
            height: Image height (default 512)
            steps: Sampling steps (default 20)
            cfg_scale: Classifier-free guidance scale (default 7.0)
            seed: Random seed (-1 for random)
            save: Whether to save the image to disk
            context: Conversation context (for metadata)
            
        Returns:
            Dict with 'path', 'prompt', 'seed', 'parameters' or None on failure
        """
        if not self.is_available():
            print("[SD] Not available - is SD WebUI running with --api?")
            return None
        
        # Apply style modifier
        style_suffix = self.STYLE_PRESETS.get(style, self.STYLE_PRESETS["default"])
        full_prompt = prompt + style_suffix
        
        # Build parameters
        params = {
            "prompt": full_prompt,
            "negative_prompt": negative_prompt or self.DEFAULT_PARAMS["negative_prompt"],
            "steps": steps or self.DEFAULT_PARAMS["steps"],
            "cfg_scale": cfg_scale or self.DEFAULT_PARAMS["cfg_scale"],
            "width": width or self.DEFAULT_PARAMS["width"],
            "height": height or self.DEFAULT_PARAMS["height"],
            "sampler_name": self.DEFAULT_PARAMS["sampler_name"],
            "seed": seed
        }
        
        try:
            print(f"[SD] Generating: {prompt[:50]}...")
            response = requests.post(
                f"{self.base_url}/sdapi/v1/txt2img",
                json=params,
                timeout=120  # SD can be slow
            )
            
            if response.status_code != 200:
                print(f"[SD] API error: {response.status_code}")
                return None
            
            result = response.json()
            
            if "images" not in result or not result["images"]:
                print("[SD] No images in response")
                return None
            
            # Decode base64 image
            image_data = base64.b64decode(result["images"][0])
            
            # Get actual seed used
            info = json.loads(result.get("info", "{}"))
            actual_seed = info.get("seed", seed)
            
            # Save image
            image_path = None
            if save:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"kay_gen_{timestamp}_{actual_seed}.png"
                image_path = os.path.join(self.OUTPUT_DIR, filename)
                
                with open(image_path, "wb") as f:
                    f.write(image_data)
                
                print(f"[SD] Saved: {filename}")
                
                # Save metadata alongside
                meta_path = image_path.replace(".png", "_meta.json")
                metadata = {
                    "prompt": prompt,
                    "full_prompt": full_prompt,
                    "style": style,
                    "parameters": params,
                    "seed": actual_seed,
                    "timestamp": datetime.now().isoformat(),
                    "context": context,
                    "model": self.model_info.get("model_name", "unknown")
                }
                with open(meta_path, "w") as f:
                    json.dump(metadata, f, indent=2)
            
            return {
                "path": image_path,
                "image_data": image_data if not save else None,
                "prompt": prompt,
                "full_prompt": full_prompt,
                "style": style,
                "seed": actual_seed,
                "parameters": params
            }
            
        except requests.exceptions.Timeout:
            print("[SD] Generation timed out")
            return None
        except Exception as e:
            print(f"[SD] Generation error: {e}")
            return None
    
    def get_models(self) -> List[str]:
        """Get list of available SD models."""
        if not self.is_available():
            return []
        
        try:
            response = requests.get(f"{self.base_url}/sdapi/v1/sd-models", timeout=10)
            if response.status_code == 200:
                models = response.json()
                return [m.get("model_name", "unknown") for m in models]
        except:
            pass
        return []
    
    def get_samplers(self) -> List[str]:
        """Get list of available samplers."""
        if not self.is_available():
            return []
        
        try:
            response = requests.get(f"{self.base_url}/sdapi/v1/samplers", timeout=10)
            if response.status_code == 200:
                samplers = response.json()
                return [s.get("name", "unknown") for s in samplers]
        except:
            pass
        return []
    
    def interrupt(self) -> bool:
        """Interrupt current generation."""
        try:
            response = requests.post(f"{self.base_url}/sdapi/v1/interrupt", timeout=5)
            return response.status_code == 200
        except:
            return False


# Singleton instance
_sd_instance: Optional[StableDiffusionIntegration] = None

def get_sd_integration() -> StableDiffusionIntegration:
    """Get or create the SD integration singleton."""
    global _sd_instance
    if _sd_instance is None:
        _sd_instance = StableDiffusionIntegration()
    return _sd_instance


# Quick test
if __name__ == "__main__":
    sd = StableDiffusionIntegration()
    if sd.is_available():
        print("SD WebUI is running!")
        print(f"Models: {sd.get_models()}")
        print(f"Samplers: {sd.get_samplers()}")
        
        # Test generation
        result = sd.generate_image(
            "a void dragon with pink scales emerging from darkness",
            style="void"
        )
        if result:
            print(f"Generated: {result['path']}")
    else:
        print("SD WebUI not available. Start it with --api flag.")
