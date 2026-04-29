#!/bin/bash
set -e

TARGET_COLOR=$1

if [ -z "$TARGET_COLOR" ]; then
    echo "Usage: switch-traffic.sh <blue|green>"
    exit 1
fi

if [ "$TARGET_COLOR" != "blue" ] && [ "$TARGET_COLOR" != "green" ]; then
    echo "Error: color must be 'blue' or 'green', got '$TARGET_COLOR'"
    exit 1
fi

PREVIOUS_COLOR=$(kubectl get configmap blue-green-state -n default -o jsonpath='{.data.active-color}')

TARGET_IP=$(kubectl get svc aceest-fitness-app -n "$TARGET_COLOR" -o jsonpath='{.spec.clusterIP}')

if [ -z "$TARGET_IP" ]; then
    echo "Error: could not resolve ClusterIP for service aceest-fitness-app in namespace $TARGET_COLOR"
    exit 1
fi

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
      - "${TARGET_IP}"
ports:
  - port: 5000
    protocol: TCP
EOF

kubectl annotate service aceest-fitness-app-router -n default \
    deployment/active-color="$TARGET_COLOR" \
    deployment/previous-color="$PREVIOUS_COLOR" \
    --overwrite

kubectl patch configmap blue-green-state -n default -p \
    "{\"data\":{\"active-color\":\"$TARGET_COLOR\",\"previous-color\":\"$PREVIOUS_COLOR\",\"last-switched\":\"$(date -u)\"}}"

echo "================================================"
echo "  TRAFFIC SWITCHED: $PREVIOUS_COLOR --> $TARGET_COLOR"
echo "  Router --> $TARGET_IP (namespace: $TARGET_COLOR)"
echo "================================================"
echo ""
echo "--- Pods in blue namespace ---"
kubectl get pods -n blue -l app=aceest-fitness-app
echo ""
echo "--- Pods in green namespace ---"
kubectl get pods -n green -l app=aceest-fitness-app
echo ""
echo "--- Router EndpointSlice ---"
kubectl get endpointslice aceest-fitness-app-router -n default
echo ""
echo "--- Deployment State ---"
kubectl get configmap blue-green-state -n default -o jsonpath='{.data}' | tr ',' '\n'
echo ""
