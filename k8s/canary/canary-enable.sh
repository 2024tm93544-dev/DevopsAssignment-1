#!/bin/bash
set -e

STABLE_IP=$(kubectl get svc aceest-fitness-app -n stable -o jsonpath='{.spec.clusterIP}')
CANARY_IP=$(kubectl get svc aceest-fitness-app -n canary -o jsonpath='{.spec.clusterIP}')

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
  - addresses:
      - "${CANARY_IP}"
ports:
  - port: 5000
    protocol: TCP
EOF

kubectl patch configmap canary-state -n default -p \
    "{\"data\":{\"status\":\"canary-active\",\"last-updated\":\"$(date -u)\"}}"

echo "================================================"
echo "  CANARY ENABLED: 50% stable | 50% canary"
echo "  Stable  --> $STABLE_IP (namespace: stable)"
echo "  Canary  --> $CANARY_IP (namespace: canary)"
echo "================================================"
echo ""
echo "--- Pods in stable ---"
kubectl get pods -n stable -l app=aceest-fitness-app
echo ""
echo "--- Pods in canary ---"
kubectl get pods -n canary -l app=aceest-fitness-app
echo ""
echo "--- Router EndpointSlice ---"
kubectl get endpointslice aceest-fitness-app-router -n default -o wide
echo ""
echo "--- Canary State ---"
kubectl get configmap canary-state -n default -o jsonpath='{.data}' | tr ',' '\n'
echo ""
