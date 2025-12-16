#!/bin/bash
set -e

NAMESPACE=default
APP_LABEL=ai-agent-worker

echo "1. Aplicando secrets..."
kubectl apply -f secrets.yaml

echo "2. Aplicando agent..."
kubectl apply -f agent.yaml

echo "3. Aguardando pods ficarem prontos..."
kubectl wait --for=condition=Ready pod -l app=$APP_LABEL -n $NAMESPACE --timeout=120s || true

echo "4. Pods:"
kubectl get pods -l app=$APP_LABEL -n $NAMESPACE -o wide

POD=$(kubectl get pod -l app=$APP_LABEL -n $NAMESPACE -o jsonpath='{.items[0].metadata.name}')

echo "6. Logs:"
kubectl logs -f $POD -n $NAMESPACE
