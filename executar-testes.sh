#!/usr/bin/env bash
# Roda os testes de cada serviço, cada um no seu ambiente. Uso: ./executar-testes.sh
set -e
for dir in servicos/usuarios servicos/inventario servicos/chamados servicos/notificacoes gateway; do
  echo "=== $dir"
  (cd "$dir" && python -m pytest -q)
done
