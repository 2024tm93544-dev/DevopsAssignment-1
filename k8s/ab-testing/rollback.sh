#!/bin/bash
set -e

A_IP=$(kubectl get svc aceest-fitness-app -n a-site -o jsonpath='{.spec.clusterIP}')

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
      - "${A_IP}"
ports:
  - port: 5000
    protocol: TCP
EOF

kubectl scale deployment aceest-nginx-proxy -n default --replicas=0 || true

echo "================================================"
echo "  A/B ROLLBACK: 100% traffic on variant A"
echo "  Variant A --> $A_IP (nginx proxy bypassed)"
echo "================================================"
echo ""
echo "--- Variant A pods ---"
kubectl get pods -n a-site -l app=aceest-fitness-app
echo ""
echo "--- Router EndpointSlice ---"
kubectl get endpointslice aceest-fitness-app-router -n default -o wide
