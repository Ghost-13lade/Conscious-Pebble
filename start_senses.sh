#!/bin/bash
echo "👂👄 Starting Brook's Senses (MLX Native)..."
# Run on Port 8081
python -m uvicorn senses_service:app --host 0.0.0.0 --port 8081 --log-level info
