#!/usr/bin/env bash
# Forces 100% CPU inference (no GPU offload) to approximate the "no
# dedicated GPU" consumer laptop targeted by the contest (specification §1).
#
# Why this script exists: on a dev machine with a GPU, Ollama automatically
# uses the GPU, which gives non-representative RAM/latency figures
# (measured: ~4.4 GB with GPU vs. ~4.0 GB announced by Ollama itself
# in pure CPU mode for gemma3:4b — the two don't compare
# directly, the GPU offloads part of the weights to VRAM).
#
# NB — abandoned attempt: capping RAM via a systemd cgroup
# (MemoryMax) to simulate an 8 GB laptop DOES NOT WORK with Ollama:
# it does its own admission control by reading /proc/meminfo (real
# system memory), not the cgroup limit. So there is no reliable
# simulation of "8 GB" without a VM or the real target machine — only
# CPU forcing (this script) is reliable to do from this dev machine.
#
# Usage: ./scripts/profile_cpu_only.sh
# Requires: enough REALLY free RAM on the machine (this script cannot
# simulate that) — close other apps before running if model loading
# fails with "model requires more system memory".

set -uo pipefail
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PORT=11501

echo "=== Starting an isolated Ollama server, GPU hidden (CUDA_VISIBLE_DEVICES=-1) ==="
CUDA_VISIBLE_DEVICES=-1 OLLAMA_HOST=127.0.0.1:$PORT OLLAMA_MODELS=/usr/share/ollama/.ollama/models \
  nohup ollama serve > /tmp/ollama_cpu_only.log 2>&1 &
SERVER_PID=$!
trap 'kill $SERVER_PID 2>/dev/null' EXIT

for i in $(seq 1 30); do
  curl -s http://127.0.0.1:$PORT/api/tags >/dev/null 2>&1 && break
  sleep 0.5
done

if ! grep -q "library=cpu" /tmp/ollama_cpu_only.log; then
  echo "WARNING: the GPU may not have been hidden, check /tmp/ollama_cpu_only.log"
fi

cd "$REPO_DIR" && source .venv/bin/activate
OLLAMA_HOST=http://127.0.0.1:$PORT python -m src.profiling
