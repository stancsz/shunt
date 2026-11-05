#!/bin/sh
set -eu
cd /app

python -c "import torch; assert torch.cuda.is_available(), 'NVIDIA CUDA GPU is not available in this container'; print('CUDA device:', torch.cuda.get_device_name(0), flush=True)"

model_complete() {
    for file in config.json tokenizer.json tokenizer_config.json chat_template.jinja vocab.json merges.txt preprocessor_config.json video_preprocessor_config.json model.safetensors.index.json model.safetensors-00001-of-00001.safetensors; do
        [ -s "models/Qwen3.5-0.8B/$file" ] || return 1
    done
}

if [ ! -f models/.shunt-model-ready ] || ! model_complete; then
    echo 'Downloading the pinned base model...'
    python scripts/download.py
    model_complete || { echo 'Model download is incomplete.' >&2; exit 1; }
    touch models/.shunt-model-ready
fi

if [ ! -f artifacts/.shunt-adapter-ready ]; then
    if [ -d artifacts/shunt-lora ]; then
        echo 'Incomplete adapter directory; follow the Docker recovery instructions in README.md.' >&2
        exit 1
    fi
    echo 'Generating training data and training the local adapter...'
    python scripts/make_data.py
    python scripts/train.py --epochs 3 --batch-size 4
    test -f artifacts/shunt-lora/adapter_config.json
    test -f artifacts/shunt-lora/adapter_model.safetensors
    touch artifacts/.shunt-adapter-ready
fi
if [ ! -f artifacts/shunt-lora/adapter_model.safetensors ]; then
    echo 'Incomplete adapter weights; inspect the artifacts volume before retrying.' >&2
    exit 1
fi
echo 'Starting Shunt...'
exec python -m shunt.server --host 0.0.0.0 --port 18765 --cuda-graph
