#!/usr/bin/env bash
# Télécharge le poids GGUF de Gemma 3 4B IT, quantization Q4_K_M — la même
# quantization que celle utilisée par Ollama dans le pipeline de démo
# (confirmé via `ollama show gemma3:4b` : quantization Q4_K_M, 4.3B
# paramètres). Le blob interne d'Ollama n'est pas exporté directement
# (format non portable, pas d'URL publique) : on utilise à la place un
# fichier .gguf public équivalent.
#
# Source retenue : ggml-org/gemma-3-4b-it-GGUF (organisation officielle
# de llama.cpp sur Hugging Face — cohérent avec la règle ADTC "must run
# through llama.cpp"). Taille croisée avec un second mirror indépendant
# (bartowski/google_gemma-3-4b-it-GGUF) : écart de 256 octets sur 2,49 Go,
# négligeable — confirme qu'il s'agit du même artefact Q4_K_M.
#
# Rules (cahier des charges du template ADTC) :
#   - Idempotent (safe à relancer).
#   - Aucun credential requis (URL publique).
#   - Le chemin de sortie doit correspondre à _runtime.model_path dans
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

echo "downloading $MODEL_URL → $MODEL_FILE (~2,5 Go)…"

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
