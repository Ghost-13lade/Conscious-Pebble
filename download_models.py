#!/usr/bin/env python3
"""
Download ML models for Conscious Pebble voice services.
Downloads Whisper (STT) and Kokoro (TTS) models from HuggingFace.

Usage:
    python download_models.py [--models-dir MODELS_DIR]
"""
import argparse
import os
import sys
from pathlib import Path

try:
    from huggingface_hub import snapshot_download, login
    HF_HUB_AVAILABLE = True
except ImportError:
    HF_HUB_AVAILABLE = False
    print("ERROR: huggingface_hub not installed.")
    print("Please install it with: pip install huggingface_hub")
    sys.exit(1)


# Model specifications
MODELS = {
    "whisper": {
        "repo_id": "mlx-community/whisper-large-v3-turbo",
        "description": "Whisper Large V3 Turbo - Speech-to-Text",
        "size_approx": "~1.5 GB",
    },
    "kokoro": {
        "repo_id": "mlx-community/Kokoro-82M-bf16",
        "description": "Kokoro 82M BF16 - Text-to-Speech",
        "size_approx": "~100 MB",
    },
}


def download_model(repo_id: str, models_dir: Path, model_name: str) -> bool:
    """Download a model from HuggingFace."""
    model_path = models_dir / model_name
    
    print(f"\n{'='*60}")
    print(f"Downloading: {repo_id}")
    print(f"Target: {model_path}")
    print(f"{'='*60}")
    
    try:
        # Check if already downloaded
        if model_path.exists():
            print(f"✓ Model already exists at {model_path}")
            return True
        
        # Download the model
        print(f"Starting download...")
        local_path = snapshot_download(
            repo_id=repo_id,
            local_dir=str(model_path),
            local_dir_use_symlinks=False,
            resume_download=True,
        )
        print(f"✓ Downloaded to: {local_path}")
        return True
        
    except Exception as e:
        print(f"✗ Failed to download {repo_id}: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Download ML voice models for Conscious Pebble"
    )
    parser.add_argument(
        "--models-dir",
        type=str,
        default=None,
        help="Directory to store models (default: ./models)",
    )
    parser.add_argument(
        "--skip-whisper",
        action="store_true",
        help="Skip Whisper model download",
    )
    parser.add_argument(
        "--skip-kokoro",
        action="store_true",
        help="Skip Kokoro model download",
    )
    args = parser.parse_args()
    
    # Determine models directory
    script_dir = Path(__file__).parent
    if args.models_dir:
        models_dir = Path(args.models_dir)
    else:
        models_dir = script_dir / "models"
    
    print("=" * 60)
    print("Conscious Pebble - Model Downloader")
    print("=" * 60)
    print(f"Models directory: {models_dir}")
    
    # Create models directory
    models_dir.mkdir(parents=True, exist_ok=True)
    
    # Track results
    results = {}
    
    # Download Whisper
    if not args.skip_whisper:
        print(f"\n[1/2] Whisper (Speech-to-Text)")
        print(f"  Approximate size: {MODELS['whisper']['size_approx']}")
        results["whisper"] = download_model(
            MODELS["whisper"]["repo_id"],
            models_dir,
            "whisper-large-v3-turbo"
        )
    else:
        print("\n[1/2] Skipping Whisper (--skip-whisper)")
        results["whisper"] = True
    
    # Download Kokoro
    if not args.skip_kokoro:
        print(f"\n[2/2] Kokoro (Text-to-Speech)")
        print(f"  Approximate size: {MODELS['kokoro']['size_approx']}")
        results["kokoro"] = download_model(
            MODELS["kokoro"]["repo_id"],
            models_dir,
            "kokoro-82m-bf16"
        )
    else:
        print("\n[2/2] Skipping Kokoro (--skip-kokoro)")
        results["kokoro"] = True
    
    # Summary
    print("\n" + "=" * 60)
    print("Download Summary")
    print("=" * 60)
    
    for model, success in results.items():
        status = "✓ SUCCESS" if success else "✗ FAILED"
        print(f"  {model}: {status}")
    
    all_success = all(results.values())
    
    if all_success:
        print("\n✓ All models downloaded successfully!")
        print(f"  Models stored in: {models_dir}")
        return 0
    else:
        print("\n✗ Some models failed to download.")
        print("  Please check your internet connection and try again.")
        return 1


if __name__ == "__main__":
    sys.exit(main())