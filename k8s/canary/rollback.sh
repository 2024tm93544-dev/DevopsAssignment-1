#!/bin/bash
set -e

STABLE_IP=$(kubectl get svc aceest-fitness-app -n stable -o jsonpath='{.spec.clusterIP}')

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
      - "${STABLE_IP}"
ports:
  - port: 5000
    protocol: TCP
EOF

kubectl patch configmap canary-state -n default -p \
    "{\"data\":{\"status\":\"stable-only\",\"last-updated\":\"$(date -u)\"}}"

echo "================================================"
echo "  CANARY ROLLBACK: 100% traffic on stable"
echo "  Stable --> $STABLE_IP"
echo "================================================"
echo ""
echo "--- Router EndpointSlice ---"
kubectl get endpointslice aceest-fitness-app-router -n default -o wide
echo ""
echo "--- Canary State ---"
kubectl get configmap canary-state -n default -o jsonpath='{.data}' | tr ',' '\n'
echo ""
