<#!
.SYNOPSIS
Set up Shunt in the repository's .venv on Windows with an NVIDIA CUDA GPU.
#>
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$root = Split-Path -Parent $PSScriptRoot
Push-Location $root
try {
    if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
        throw 'uv is required. Install uv and rerun this script.'
    }
    if (-not (Test-Path '.venv/Scripts/python.exe')) {
        & uv venv --python 3.11 .venv
        if ($LASTEXITCODE -ne 0) { throw 'Could not create the Python environment.' }
    } else {
        Write-Host 'Using the existing .venv; its installed packages may be changed.'
    }
    $python = Join-Path $root '.venv/Scripts/python.exe'
    & uv pip install --python $python -r requirements.txt --torch-backend cu128
    if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }

    & $python -c "import torch; assert torch.cuda.is_available(), 'A working NVIDIA CUDA GPU is required'; print('CUDA device:', torch.cuda.get_device_name(0))"
    if ($LASTEXITCODE -ne 0) { throw 'CUDA check failed; install a compatible NVIDIA driver and check the GPU.' }
    $env:PYTHONPATH = $root

    if (-not (Test-Path 'models/Qwen3.5-0.8B/config.json')) {
        Write-Host 'Downloading the pinned base model...'
        & $python scripts/download.py
        if ($LASTEXITCODE -ne 0) { throw 'Base model download failed.' }
    } else {
        Write-Host 'Using the existing base model.'
    }
    foreach ($file in @('config.json', 'tokenizer.json', 'tokenizer_config.json', 'chat_template.jinja',
                        'vocab.json', 'merges.txt', 'preprocessor_config.json', 'video_preprocessor_config.json',
                        'model.safetensors.index.json', 'model.safetensors-00001-of-00001.safetensors')) {
        if (-not (Test-Path "models/Qwen3.5-0.8B/$file")) {
            throw "The base model is incomplete: $file is missing. Move models/Qwen3.5-0.8B aside (for example to models/Qwen3.5-0.8B-incomplete), then rerun setup to download it again."
        }
    }

    $adapter = 'artifacts/shunt-lora'
    if (-not (Test-Path "$adapter/adapter_config.json")) {
        if (Test-Path $adapter) {
            throw 'The adapter directory is incomplete. Move artifacts/shunt-lora aside (for example to artifacts/shunt-lora-incomplete), then rerun setup to train again.'
        }
        if (-not (Test-Path 'data/train.jsonl')) {
            if (Test-Path 'data/validation.jsonl') {
                throw 'Training data is missing but validation data exists; refusing to overwrite it.'
            }
            & $python scripts/make_data.py
            if ($LASTEXITCODE -ne 0) { throw 'Training data generation failed.' }
        }
        Write-Host 'Training the local adapter; first-run time depends on your GPU...'
        & $python scripts/train.py --epochs 3 --batch-size 4
        if ($LASTEXITCODE -ne 0) { throw 'Adapter training failed. Inspect artifacts/shunt-lora before retrying.' }
    } else {
        if (-not (Test-Path "$adapter/adapter_model.safetensors")) {
            throw 'The adapter is incomplete: adapter_model.safetensors is missing. Move artifacts/shunt-lora aside, then rerun setup to train again.'
        }
        Write-Host 'Using the existing adapter.'
    }
    Write-Host 'Setup complete. Start Shunt with: .venv/Scripts/python.exe -m shunt.server --cuda-graph'
} finally {
    Pop-Location
}
