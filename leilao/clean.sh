
#!/bin/bash

echo "=== LIMPANDO TUDO ==="

echo "1. Parando containers Docker..."
docker stop $(docker ps -q) 2>/dev/null || true
docker rm $(docker ps -aq) 2>/dev/null || true

echo "2. Deletando cluster Kind..."
kind delete cluster 2>/dev/null || true

echo "3. Liberando porta 30080..."
sudo fuser -k 30080/tcp 2>/dev/null || true
sudo fuser -k 30081/tcp 2>/dev/null || true

echo "4. Removendo imagens antigas..."
docker rmi leilao-flask:latest 2>/dev/null || true

echo "5. Limpando dados do Kubernetes..."
kubectl delete namespace leilao-ns 2>/dev/null || true

echo "=== LIMPEZA CONCLUÍDA ==="
echo ""
echo "Agora execute: ./deploy.sh"

