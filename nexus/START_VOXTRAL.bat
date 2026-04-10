@echo off
echo ====================================
echo  Starting Voxtral TTS Server
echo  Port: 8200
echo  Model: mistralai/Voxtral-4B-TTS-2603
echo ====================================
echo.
echo First run will download ~8GB model from HuggingFace.
echo Server will be ready when you see "Uvicorn running on..."
echo.
echo Press Ctrl+C to stop.
echo.
python -m vllm_omni.entrypoints.openai.api_server ^
  --model mistralai/Voxtral-4B-TTS-2603 ^
  --host 0.0.0.0 ^
  --port 8200 ^
  --max-model-len 4096
pause
