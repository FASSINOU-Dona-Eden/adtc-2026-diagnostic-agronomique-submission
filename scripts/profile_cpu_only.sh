#!/usr/bin/env bash
# Force une inférence 100% CPU (sans offload GPU) pour approximer le laptop
# grand public "sans GPU dédié" ciblé par le concours (cahier des charges §1).
#
# Pourquoi ce script existe : sur une machine de dev avec GPU, Ollama utilise
# le GPU automatiquement, ce qui donne des chiffres de RAM/latence non
# représentatifs (mesuré : ~4,4 Go avec GPU vs ~4,0 Go annoncé par Ollama
# lui-même en CPU pur pour gemma3:4b — les deux ne se comparent pas
# directement, le GPU déporte une partie du poids en VRAM).
#
# NB — tentative abandonnée : limiter la RAM via un cgroup systemd
# (MemoryMax) pour simuler un laptop 8 Go NE FONCTIONNE PAS avec Ollama :
# il fait son propre contrôle d'admission en lisant /proc/meminfo (mémoire
# système réelle), pas la limite du cgroup. Donc pas de simulation fiable
# de "8 Go" sans VM ou machine cible réelle — seul le forçage CPU (ce
# script) est fiable à faire depuis ce poste de dev.
#
# Usage : ./scripts/profile_cpu_only.sh
# Nécessite : assez de RAM RÉELLEMENT libre sur la machine (ce script ne
# peut rien simuler ici) — fermer les autres applis avant de lancer si le
# chargement du modèle échoue avec "model requires more system memory".

set -uo pipefail
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PORT=11501

echo "=== Lancement d'un serveur Ollama isolé, GPU masqué (CUDA_VISIBLE_DEVICES=-1) ==="
CUDA_VISIBLE_DEVICES=-1 OLLAMA_HOST=127.0.0.1:$PORT OLLAMA_MODELS=/usr/share/ollama/.ollama/models \
  nohup ollama serve > /tmp/ollama_cpu_only.log 2>&1 &
SERVER_PID=$!
trap 'kill $SERVER_PID 2>/dev/null' EXIT

for i in $(seq 1 30); do
  curl -s http://127.0.0.1:$PORT/api/tags >/dev/null 2>&1 && break
  sleep 0.5
done

if ! grep -q "library=cpu" /tmp/ollama_cpu_only.log; then
  echo "ATTENTION : le GPU n'a peut-être pas été masqué, vérifier /tmp/ollama_cpu_only.log"
fi

cd "$REPO_DIR" && source .venv/bin/activate
OLLAMA_HOST=http://127.0.0.1:$PORT python -m src.profiling
