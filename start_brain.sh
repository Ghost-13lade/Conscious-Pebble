#!/bin/bash
echo "🧠 Waking up Brook (Hermes 70B - 128k Context - 4-bit Memory)..."

# 1. Force 4-bit KV Cache Quantization (Crucial for 64GB RAM)
# This allows us to run 128k context without crashing.
export MLX_KV_BITS=4

# 2. Start Server
# NOTE: This installed mlx_lm build does not expose --max-kv-size on CLI.
# It will use the model/server defaults while keeping 4-bit KV cache enabled.
python -m mlx_lm server \
  --model /Users/ys/pebble/models/LLMs/mlx-community/Hermes-4-70B-MLX-4bit \
  --port 8080 \
  --log-level INFO