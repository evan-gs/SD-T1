# gerado com ChatGPT apos erro com a imagem

#!/bin/bash

echo "=== DEPLOY FINAL==="
echo "Usando porta 30080"

# 1. Limpar tudo
echo "1. Limpando ambiente anterior..."
kind delete cluster --name leilao-cluster 2>/dev/null || true
kubectl delete namespace leilao-ns 2>/dev/null || true

# 2. Construir imagem
echo "2. Construindo imagem Docker..."
docker build -t leilao-flask:latest ./app

# 3. Criar cluster Kind
echo "3. Criando cluster Kind..."
kind create cluster --name leilao-cluster --config kind-config.yaml

# 4. Carregar imagem NOVO MÉTODO
echo "4. Carregando imagem no cluster..."
echo "   Método 1: Usando kind load..."
kind load docker-image leilao-flask:latest --name leilao-cluster

# 5. Método alternativo se o primeiro falhar
echo "   Método 2: Verificando se imagem foi carregada..."
if ! docker exec leilao-cluster-control-plane crictl images | grep -q "leilao-flask"; then
    echo "   Imagem não encontrada, usando método alternativo..."
    docker save leilao-flask:latest -o leilao-flask.tar
    kind load image-archive leilao-flask.tar --name leilao-cluster
    rm -f leilao-flask.tar
fi

# 6. Aplicar configurações K8s
echo "5. Aplicando configurações Kubernetes..."
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/redis.yaml
kubectl apply -f k8s/flask.yaml

# 7. Aguardar pods iniciarem
echo "6. Aguardando inicialização dos pods..."
echo -n "   Aguardando"
for i in {1..30}; do
    echo -n "."
    sleep 1
done
echo ""

# 8. Verificar status
echo "7. Status dos pods:"
kubectl get pods -n leilao-ns -o wide

echo ""
echo "8. Verificando serviços:"
kubectl get svc -n leilao-ns

# 9. Verificar logs se houver problemas
echo ""
echo "9. Verificando logs dos pods..."
PODS=$(kubectl get pods -n leilao-ns -o jsonpath='{.items[*].metadata.name}' | tr ' ' '\n')
for POD in $PODS; do
    STATUS=$(kubectl get pod $POD -n leilao-ns -o jsonpath='{.status.phase}')
    if [ "$STATUS" != "Running" ]; then
        echo "=== Pod $POD não está Running ($STATUS) ==="
        kubectl describe pod $POD -n leilao-ns | grep -A 5 "Events:"
        echo "Logs:"
        kubectl logs $POD -n leilao-ns --tail=10 2>/dev/null || echo "  Não foi possível obter logs"
    fi
done

# 10. Testar conexão
echo ""
echo "10. Testando conexão com a aplicação..."
sleep 5
if curl -s http://localhost:30080/health >/dev/null 2>&1; then
    echo "✅ APLICAÇÃO FUNCIONANDO!"
    echo "   Acesse: http://localhost:30080"
    echo ""
    echo "Endpoints disponíveis:"
    echo "  POST   /criar-leilao"
    echo "  GET    /listar-leiloes"
    echo "  GET    /detalhes-leilao/<id>"
    echo "  POST   /fazer-lance"
    echo "  GET    /notificar-leiloes"
else
    echo "❌ Aplicação não responde na porta 30080"
    echo "   Verifique os logs acima ou tente:"
    echo "   kubectl logs -n leilao-ns deployment/flask-app"
fi

echo ""
echo "=== DEPLOY CONCLUÍDO ==="
