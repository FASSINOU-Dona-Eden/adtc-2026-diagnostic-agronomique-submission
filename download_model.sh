#!/usr/bin/env bash
# Downloads the GGUF weight file for Gemma 3 4B IT, Q4_K_M quantization — the
# same quantization used by Ollama in the demo pipeline
# (confirmed via `ollama show gemma3:4b`: quantization Q4_K_M, 4.3B
# parameters). Ollama's internal blob is not exported directly
# (non-portable format, no public URL): a public equivalent .gguf
# file is used instead.
#
# Source chosen: ggml-org/gemma-3-4b-it-GGUF (llama.cpp's official
# organization on Hugging Face — consistent with the ADTC "must run
# through llama.cpp" rule). Size cross-checked against a second, independent
# mirror (bartowski/google_gemma-3-4b-it-GGUF): a 256-byte gap out of 2.49 GB,
# negligible — confirms it is the same Q4_K_M artifact.
#
# Rules (ADTC template specification):
#   - Idempotent (safe to rerun).
#   - No credential required (public URL).
#   - The output path must match _runtime.model_path in
#     metadata.json.

set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODEL_DIR="$HERE/model"
MODEL_FILE="$MODEL_DIR/gemma-3-4b-it-Q4_K_M.gguf"

MODEL_URL="https://huggingface.co/ggml-org/gemma-3-4b-it-GGUF/resolve/main/gemma-3-4b-it-Q4_K_M.gguf"

mkdir -p "$MODEL_DIR"

if [[ -f "$MODEL_FILE" ]]; then
  echo "model already present at $MODEL_FILE — skipping download"
  exit 0
fi

echo "downloading $MODEL_URL → $MODEL_FILE (~2.5 GB)…"

if command -v curl > /dev/null 2>&1; then
  curl -L --fail --progress-bar -o "$MODEL_FILE.partial" "$MODEL_URL"
elif command -v wget > /dev/null 2>&1; then
  wget --show-progress -O "$MODEL_FILE.partial" "$MODEL_URL"
else
  echo "error: neither curl nor wget found" >&2
  exit 1
fi

mv "$MODEL_FILE.partial" "$MODEL_FILE"
echo "done: $MODEL_FILE"
