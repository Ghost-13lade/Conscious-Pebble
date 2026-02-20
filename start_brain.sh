#!/bin/bash
echo "🧠 Waking up Conscious Pebble Brain (MLX LM Server)..."

# Configuration via environment variables (with defaults)
# Set these in your environment or .env file:
#   MLX_MODEL_PATH - HuggingFace model ID or local path
#   MLX_KV_BITS - KV cache quantization (4 for memory efficiency)
#   MLX_PORT - Server port (default 8080)

MODEL_PATH="${MLX_MODEL_PATH:-mlx-community/Llama-3.2-3B-Instruct-4bit}"
KV_BITS="${MLX_KV_BITS:-4}"
PORT="${MLX_PORT:-8080}"

echo "   Model: $MODEL_PATH"
echo "   KV Bits: $KV_BITS"
echo "   Port: $PORT"

# Set KV cache quantization for memory efficiency
export MLX_KV_BITS=$KV_BITS

# Start the MLX LM server
python -m mlx_lm server \
  --model "$MODEL_PATH" \
  --port "$PORT" \
  --log-level INFO