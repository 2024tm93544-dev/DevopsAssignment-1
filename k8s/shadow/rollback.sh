#!/bin/bash
set -e

PROD_IP=$(kubectl get svc aceest-fitness-app -n prod -o jsonpath='{.spec.clusterIP}')

kubectl apply -f - <<EOF
apiVersion: discovery.k8s.io/v1
kind: EndpointSlice
metadata:
  name: aceest-fitness-app-router
  namespace: default
  labels:
    kubernetes.io/service-name: aceest-fitness-app-router
addressType: IPv4
endpoints:
  - addresses:
      - "${PROD_IP}"
ports:
  - port: 5000
    protocol: TCP
EOF

kubectl scale deployment aceest-nginx-proxy -n default --replicas=0 || true

echo "================================================"
echo "  SHADOW ROLLBACK: traffic direct to prod"
echo "  Prod --> $PROD_IP (shadow proxy bypassed)"
echo "================================================"
echo ""
echo "--- Prod pods ---"
kubectl get pods -n prod -l app=aceest-fitness-app
echo ""
echo "--- Router EndpointSlice ---"
kubectl get endpointslice aceest-fitness-app-router -n default -o wide
