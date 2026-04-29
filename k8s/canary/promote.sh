#!/bin/bash
set -e

CANARY_IMAGE=$(kubectl get deployment aceest-fitness-app -n canary \
    -o jsonpath='{.spec.template.spec.containers[0].image}')

echo "================================================"
echo "  PROMOTING CANARY TO STABLE"
echo "  Image: $CANARY_IMAGE"
echo "================================================"

kubectl set image deployment/aceest-fitness-app -n stable aceest-fitness-app="$CANARY_IMAGE"
kubectl rollout status deployment/aceest-fitness-app -n stable --timeout=120s

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
    "{\"data\":{\"status\":\"stable-only\",\"stable-image\":\"$CANARY_IMAGE\",\"canary-image\":\"none\",\"last-updated\":\"$(date -u)\"}}"

echo "================================================"
echo "  PROMOTION COMPLETE: 100% traffic on stable"
echo "  Stable image is now: $CANARY_IMAGE"
echo "================================================"
echo ""
echo "--- Stable pods ---"
kubectl get pods -n stable -l app=aceest-fitness-app
echo ""
echo "--- Router EndpointSlice ---"
kubectl get endpointslice aceest-fitness-app-router -n default -o wide
