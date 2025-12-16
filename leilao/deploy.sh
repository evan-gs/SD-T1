#!/bin/bash

echo "1. Limpando namespace..."
kubectl delete namespace leilao-ns 2>/dev/null || true

echo "2. Aplicando Kubernetes..."
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/redis.yaml
kubectl apply -f k8s/flask.yaml

echo "3. Aguardando pods..."
kubectl wait --for=condition=Ready pod --all -n leilao-ns --timeout=120s

echo "4. Status:"
kubectl get pods -n leilao-ns -o wide
kubectl get svc -n leilao-ns

echo "5. Testando app..."
curl http://localhost:30080 || echo "❌ Falhou"
