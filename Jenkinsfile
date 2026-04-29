pipeline {
    agent any
    parameters {
        string(
            name: 'IMAGE_VERSION',
            defaultValue: '',
            description: 'Docker image version tag. Leave blank to use the Jenkins build number.'
        )
        choice(
            name: 'DEPLOY_STRATEGY',
            choices: ['blue-green', 'rolling', 'canary', 'shadow', 'ab-testing'],
            description: 'Deployment strategy to use.'
        )
    }
    environment {
        IMAGE_TAG = "${params.IMAGE_VERSION ?: env.BUILD_ID}"
        DOCKER_IMAGE = "aceest-fitness-app:${IMAGE_TAG}"
        DOCKERHUB_IMAGE = "naveen3521/aceest-fitness-app"
    }
    stages {
        stage('Env Setup & Test') {
            steps {
                sh '''
                    apt-get update && apt-get install -y docker.io python3-venv python3-pip

                    python3 -m venv venv
                    . venv/bin/activate
                    pip install -r requirements.txt

                    export PYTHONPATH=$PYTHONPATH:.
                    pytest tests/ -v --cov=. --cov-report=xml
                '''
            }
        }
        stage('SonarQube Analysis') {
            steps {
                withSonarQubeEnv('SonarCloud') {
                    withEnv(["PATH+SONAR=${tool 'SonarScanner'}/bin"]) {
                        sh '''
                            sonar-scanner \
                                -Dsonar.projectKey=2024tm93544-dev_DevopsAssignment-1 \
                                -Dsonar.projectName="2024tm93544-dev_DevopsAssignment-1" \
                                -Dsonar.sources=. \
                                -Dsonar.exclusions=**/venv/**,**/__pycache__/**,**/*.pyc,**/tests/** \
                                -Dsonar.tests=tests \
                                -Dsonar.python.version=3.11 \
                                -Dsonar.python.coverage.reportPaths=coverage.xml \
                                -Dsonar.host.url=https://sonarcloud.io
                        '''
                    }
                }
            }
        }
        stage('Build & Push to DockerHub') {
            steps {
                withCredentials([usernamePassword(
                    credentialsId: 'dockerhub-credentials',
                    usernameVariable: 'DOCKER_USER',
                    passwordVariable: 'DOCKER_PASS'
                )]) {
                    sh '''
                        echo "$DOCKER_PASS" | docker login -u "$DOCKER_USER" --password-stdin
                        docker buildx build --progress=plain --push \
                            -t $DOCKERHUB_IMAGE:${IMAGE_TAG} \
                            -t $DOCKERHUB_IMAGE:latest \
                            .
                        docker logout
                    '''
                }
            }
        }
        stage('Deploy') {
            steps {
                script {
                    withCredentials([
                        sshUserPrivateKey(
                            credentialsId: 'gcp-vm-ssh-key',
                            keyFileVariable: 'SSH_KEY'
                        ),
                        string(credentialsId: 'GCP_VM_IP', variable: 'VM_IP'),
                        string(credentialsId: 'GCP_VM_USER', variable: 'VM_USER')
                    ]) {
                        if (params.DEPLOY_STRATEGY == 'blue-green') {
                            sh '''
                                chmod 600 $SSH_KEY
                                ssh -i $SSH_KEY -o StrictHostKeyChecking=no $VM_USER@$VM_IP "mkdir -p ~/blue-green"
                                scp -i $SSH_KEY -o StrictHostKeyChecking=no \
                                    k8s/blue-green/blue-deployment.yaml \
                                    k8s/blue-green/green-deployment.yaml \
                                    k8s/blue-green/blue-service.yaml \
                                    k8s/blue-green/green-service.yaml \
                                    k8s/blue-green/router-service.yaml \
                                    k8s/blue-green/state-configmap.yaml \
                                    k8s/blue-green/switch-traffic.sh \
                                    k8s/blue-green/rollback.sh \
                                    $VM_USER@$VM_IP:~/blue-green/
                                ssh -i $SSH_KEY -o StrictHostKeyChecking=no $VM_USER@$VM_IP "
                                    set -e
                                    chmod +x ~/blue-green/switch-traffic.sh ~/blue-green/rollback.sh

                                    kubectl get namespace blue &>/dev/null || kubectl create namespace blue
                                    kubectl get namespace green &>/dev/null || kubectl create namespace green
                                    kubectl get configmap blue-green-state -n default &>/dev/null || kubectl apply -f ~/blue-green/state-configmap.yaml
                                    kubectl get svc aceest-fitness-app-router -n default &>/dev/null || kubectl apply -f ~/blue-green/router-service.yaml
                                    kubectl get svc aceest-fitness-app -n blue &>/dev/null || kubectl apply -f ~/blue-green/blue-service.yaml
                                    kubectl get svc aceest-fitness-app -n green &>/dev/null || kubectl apply -f ~/blue-green/green-service.yaml

                                    ACTIVE=\\$(kubectl get configmap blue-green-state -n default -o jsonpath='{.data.active-color}')
                                    if [ \\\"\\$ACTIVE\\\" = \\\"blue\\\" ]; then TARGET=\\\"green\\\"; else TARGET=\\\"blue\\\"; fi

                                    echo '================================================'
                                    echo \\\"  BLUE-GREEN DEPLOY: \\$ACTIVE --> \\$TARGET\\\"
                                    echo '================================================'

                                    kubectl apply -f ~/blue-green/\\${TARGET}-deployment.yaml
                                    kubectl set image deployment/aceest-fitness-app -n \\$TARGET aceest-fitness-app=${DOCKERHUB_IMAGE}:${IMAGE_TAG}
                                    kubectl rollout status deployment/aceest-fitness-app -n \\$TARGET --timeout=120s

                                    echo '--- Pre-switch: pods in blue namespace ---'
                                    kubectl get pods -n blue -l app=aceest-fitness-app
                                    echo '--- Pre-switch: pods in green namespace ---'
                                    kubectl get pods -n green -l app=aceest-fitness-app
                                    echo '--- Router endpointslice (current) ---'
                                    kubectl get endpointslice aceest-fitness-app-router -n default --ignore-not-found

                                    ~/blue-green/switch-traffic.sh \\$TARGET

                                    echo '--- Final router endpointslice ---'
                                    kubectl get endpointslice aceest-fitness-app-router -n default
                                    kubectl get configmap blue-green-state -n default -o yaml
                                "
                            '''
                        } else if (params.DEPLOY_STRATEGY == 'canary') {
                            sh '''
                                chmod 600 $SSH_KEY
                                ssh -i $SSH_KEY -o StrictHostKeyChecking=no $VM_USER@$VM_IP "mkdir -p ~/canary"
                                scp -i $SSH_KEY -o StrictHostKeyChecking=no \
                                    k8s/canary/stable-deployment.yaml \
                                    k8s/canary/canary-deployment.yaml \
                                    k8s/canary/stable-service.yaml \
                                    k8s/canary/canary-service.yaml \
                                    k8s/canary/state-configmap.yaml \
                                    k8s/canary/canary-enable.sh \
                                    k8s/canary/promote.sh \
                                    k8s/canary/rollback.sh \
                                    $VM_USER@$VM_IP:~/canary/
                                ssh -i $SSH_KEY -o StrictHostKeyChecking=no $VM_USER@$VM_IP "
                                    set -e
                                    chmod +x ~/canary/canary-enable.sh ~/canary/promote.sh ~/canary/rollback.sh

                                    kubectl get namespace stable &>/dev/null || kubectl create namespace stable
                                    kubectl get namespace canary &>/dev/null || kubectl create namespace canary
                                    kubectl get configmap canary-state -n default &>/dev/null || kubectl apply -f ~/canary/state-configmap.yaml
                                    kubectl get svc aceest-fitness-app-router -n default &>/dev/null || kubectl apply -f ~/blue-green/router-service.yaml
                                    kubectl get svc aceest-fitness-app -n stable &>/dev/null || kubectl apply -f ~/canary/stable-service.yaml
                                    kubectl get svc aceest-fitness-app -n canary &>/dev/null || kubectl apply -f ~/canary/canary-service.yaml

                                    echo '================================================'
                                    echo '  CANARY DEPLOY'
                                    echo '  Deploying ${DOCKERHUB_IMAGE}:${IMAGE_TAG} to canary'
                                    echo '================================================'

                                    kubectl apply -f ~/canary/stable-deployment.yaml
                                    kubectl apply -f ~/canary/canary-deployment.yaml
                                    kubectl set image deployment/aceest-fitness-app -n canary aceest-fitness-app=${DOCKERHUB_IMAGE}:${IMAGE_TAG}
                                    kubectl rollout status deployment/aceest-fitness-app -n canary --timeout=120s

                                    echo '--- Pre-enable: pods in stable ---'
                                    kubectl get pods -n stable -l app=aceest-fitness-app
                                    echo '--- Pre-enable: pods in canary ---'
                                    kubectl get pods -n canary -l app=aceest-fitness-app

                                    ~/canary/canary-enable.sh

                                    echo '--- Canary state ---'
                                    kubectl get configmap canary-state -n default -o yaml
                                "
                            '''
                        } else if (params.DEPLOY_STRATEGY == 'rolling') {
                            sh '''
                                chmod 600 $SSH_KEY
                                scp -i $SSH_KEY -o StrictHostKeyChecking=no \
                                    k8s/deployment.yaml \
                                    $VM_USER@$VM_IP:~/deployment.yaml
                                ssh -i $SSH_KEY -o StrictHostKeyChecking=no $VM_USER@$VM_IP "
                                    set -e

                                    echo '================================================'
                                    echo '  ROLLING UPDATE'
                                    echo '  Deploying ${DOCKERHUB_IMAGE}:${IMAGE_TAG}'
                                    echo '================================================'

                                    kubectl apply -f ~/deployment.yaml
                                    kubectl set image deployment/aceest-fitness-app aceest-fitness-app=${DOCKERHUB_IMAGE}:${IMAGE_TAG} -n default
                                    kubectl rollout status deployment/aceest-fitness-app -n default --timeout=120s

                                    echo '--- Rolling update history ---'
                                    kubectl rollout history deployment/aceest-fitness-app -n default

                                    echo '--- Pod state after rollout ---'
                                    kubectl get pods -n default -l app=aceest-fitness-app -o wide

                                    echo '--- Deployment image ---'
                                    kubectl get deployment aceest-fitness-app -n default \
                                        -o jsonpath='{.spec.template.spec.containers[0].image}'
                                    echo ''
                                "
                            '''
                        } else if (params.DEPLOY_STRATEGY == 'shadow') {
                            sh '''
                                chmod 600 $SSH_KEY
                                ssh -i $SSH_KEY -o StrictHostKeyChecking=no $VM_USER@$VM_IP "mkdir -p ~/shadow"
                                scp -i $SSH_KEY -o StrictHostKeyChecking=no \
                                    k8s/shadow/prod-deployment.yaml \
                                    k8s/shadow/shadow-deployment.yaml \
                                    k8s/shadow/prod-service.yaml \
                                    k8s/shadow/shadow-service.yaml \
                                    k8s/shadow/nginx-configmap.yaml \
                                    k8s/shadow/nginx-deployment.yaml \
                                    k8s/shadow/nginx-service.yaml \
                                    k8s/shadow/rollback.sh \
                                    $VM_USER@$VM_IP:~/shadow/
                                ssh -i $SSH_KEY -o StrictHostKeyChecking=no $VM_USER@$VM_IP "
                                    set -e
                                    chmod +x ~/shadow/rollback.sh

                                    kubectl get namespace prod &>/dev/null || kubectl create namespace prod
                                    kubectl get namespace shadow &>/dev/null || kubectl create namespace shadow
                                    kubectl get svc aceest-fitness-app-router -n default &>/dev/null || kubectl apply -f ~/blue-green/router-service.yaml
                                    kubectl get svc aceest-fitness-app -n prod &>/dev/null || kubectl apply -f ~/shadow/prod-service.yaml
                                    kubectl get svc aceest-fitness-app -n shadow &>/dev/null || kubectl apply -f ~/shadow/shadow-service.yaml

                                    echo '================================================'
                                    echo '  SHADOW DEPLOY'
                                    echo '  Prod: ${DOCKERHUB_IMAGE}:latest'
                                    echo '  Shadow: ${DOCKERHUB_IMAGE}:${IMAGE_TAG} (new version under test)'
                                    echo '================================================'

                                    kubectl apply -f ~/shadow/prod-deployment.yaml
                                    kubectl apply -f ~/shadow/shadow-deployment.yaml
                                    kubectl set image deployment/aceest-fitness-app -n shadow aceest-fitness-app=${DOCKERHUB_IMAGE}:${IMAGE_TAG}
                                    kubectl rollout status deployment/aceest-fitness-app -n prod --timeout=120s
                                    kubectl rollout status deployment/aceest-fitness-app -n shadow --timeout=120s

                                    kubectl apply -f ~/shadow/nginx-configmap.yaml
                                    kubectl apply -f ~/shadow/nginx-deployment.yaml
                                    kubectl apply -f ~/shadow/nginx-service.yaml
                                    kubectl rollout status deployment/aceest-nginx-proxy -n default --timeout=60s

                                    NGINX_IP=\\$(kubectl get svc aceest-nginx-proxy -n default -o jsonpath='{.spec.clusterIP}')
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
      - \\\"\\$NGINX_IP\\\"
ports:
  - port: 5000
    protocol: TCP
EOF

                                    echo '--- Prod pods ---'
                                    kubectl get pods -n prod -l app=aceest-fitness-app
                                    echo '--- Shadow pods (mirrored traffic, responses dropped) ---'
                                    kubectl get pods -n shadow -l app=aceest-fitness-app
                                    echo '--- nginx mirror proxy ---'
                                    kubectl get pods -n default -l app=aceest-nginx-proxy
                                    echo '--- Router EndpointSlice --> nginx proxy ---'
                                    kubectl get endpointslice aceest-fitness-app-router -n default -o wide
                                "
                            '''
                        } else if (params.DEPLOY_STRATEGY == 'ab-testing') {
                            sh '''
                                chmod 600 $SSH_KEY
                                ssh -i $SSH_KEY -o StrictHostKeyChecking=no $VM_USER@$VM_IP "mkdir -p ~/ab-testing"
                                scp -i $SSH_KEY -o StrictHostKeyChecking=no \
                                    k8s/ab-testing/a-deployment.yaml \
                                    k8s/ab-testing/b-deployment.yaml \
                                    k8s/ab-testing/a-service.yaml \
                                    k8s/ab-testing/b-service.yaml \
                                    k8s/ab-testing/nginx-configmap.yaml \
                                    k8s/ab-testing/nginx-deployment.yaml \
                                    k8s/ab-testing/nginx-service.yaml \
                                    k8s/ab-testing/rollback.sh \
                                    $VM_USER@$VM_IP:~/ab-testing/
                                ssh -i $SSH_KEY -o StrictHostKeyChecking=no $VM_USER@$VM_IP "
                                    set -e
                                    chmod +x ~/ab-testing/rollback.sh

                                    kubectl get namespace a-site &>/dev/null || kubectl create namespace a-site
                                    kubectl get namespace b-site &>/dev/null || kubectl create namespace b-site
                                    kubectl get svc aceest-fitness-app-router -n default &>/dev/null || kubectl apply -f ~/blue-green/router-service.yaml
                                    kubectl get svc aceest-fitness-app -n a-site &>/dev/null || kubectl apply -f ~/ab-testing/a-service.yaml
                                    kubectl get svc aceest-fitness-app -n b-site &>/dev/null || kubectl apply -f ~/ab-testing/b-service.yaml

                                    echo '================================================'
                                    echo '  A/B TESTING DEPLOY'
                                    echo '  Variant A: ${DOCKERHUB_IMAGE}:latest  (default)'
                                    echo '  Variant B: ${DOCKERHUB_IMAGE}:${IMAGE_TAG}  (new)'
                                    echo '  Route to B: cookie ab_variant=b  or  header X-AB-Variant: b'
                                    echo '================================================'

                                    kubectl apply -f ~/ab-testing/a-deployment.yaml
                                    kubectl apply -f ~/ab-testing/b-deployment.yaml
                                    kubectl set image deployment/aceest-fitness-app -n b-site aceest-fitness-app=${DOCKERHUB_IMAGE}:${IMAGE_TAG}
                                    kubectl rollout status deployment/aceest-fitness-app -n a-site --timeout=120s
                                    kubectl rollout status deployment/aceest-fitness-app -n b-site --timeout=120s

                                    kubectl apply -f ~/ab-testing/nginx-configmap.yaml
                                    kubectl apply -f ~/ab-testing/nginx-deployment.yaml
                                    kubectl apply -f ~/ab-testing/nginx-service.yaml
                                    kubectl rollout status deployment/aceest-nginx-proxy -n default --timeout=60s

                                    NGINX_IP=\\$(kubectl get svc aceest-nginx-proxy -n default -o jsonpath='{.spec.clusterIP}')
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
      - \\\"\\$NGINX_IP\\\"
ports:
  - port: 5000
    protocol: TCP
EOF

                                    echo '--- Variant A pods (a-site) ---'
                                    kubectl get pods -n a-site -l app=aceest-fitness-app
                                    echo '--- Variant B pods (b-site) ---'
                                    kubectl get pods -n b-site -l app=aceest-fitness-app
                                    echo '--- nginx A/B proxy ---'
                                    kubectl get pods -n default -l app=aceest-nginx-proxy
                                    echo '--- Router EndpointSlice --> nginx proxy ---'
                                    kubectl get endpointslice aceest-fitness-app-router -n default -o wide
                                "
                            '''
                        }
                    }
                }
            }
        }
    }
    post {
        failure {
            script {
                if (params.DEPLOY_STRATEGY == 'blue-green') {
                    withCredentials([
                        sshUserPrivateKey(credentialsId: 'gcp-vm-ssh-key', keyFileVariable: 'SSH_KEY'),
                        string(credentialsId: 'GCP_VM_IP', variable: 'VM_IP'),
                        string(credentialsId: 'GCP_VM_USER', variable: 'VM_USER')
                    ]) {
                        sh '''
                            chmod 600 $SSH_KEY
                            ssh -i $SSH_KEY -o StrictHostKeyChecking=no $VM_USER@$VM_IP "
                                chmod +x ~/blue-green/rollback.sh
                                ~/blue-green/rollback.sh || true
                                echo '--- Rollback: pods in blue ---'
                                kubectl get pods -n blue -l app=aceest-fitness-app --ignore-not-found
                                echo '--- Rollback: pods in green ---'
                                kubectl get pods -n green -l app=aceest-fitness-app --ignore-not-found
                                echo '--- Rollback: router endpointslice ---'
                                kubectl get endpointslice aceest-fitness-app-router -n default --ignore-not-found
                            "
                        '''
                    }
                } else if (params.DEPLOY_STRATEGY == 'canary') {
                    withCredentials([
                        sshUserPrivateKey(credentialsId: 'gcp-vm-ssh-key', keyFileVariable: 'SSH_KEY'),
                        string(credentialsId: 'GCP_VM_IP', variable: 'VM_IP'),
                        string(credentialsId: 'GCP_VM_USER', variable: 'VM_USER')
                    ]) {
                        sh '''
                            chmod 600 $SSH_KEY
                            ssh -i $SSH_KEY -o StrictHostKeyChecking=no $VM_USER@$VM_IP "
                                chmod +x ~/canary/rollback.sh
                                ~/canary/rollback.sh || true
                                echo '--- Rollback: pods in stable ---'
                                kubectl get pods -n stable -l app=aceest-fitness-app --ignore-not-found
                                echo '--- Rollback: router endpointslice ---'
                                kubectl get endpointslice aceest-fitness-app-router -n default --ignore-not-found
                            "
                        '''
                    }
                } else if (params.DEPLOY_STRATEGY == 'rolling') {
                    withCredentials([
                        sshUserPrivateKey(credentialsId: 'gcp-vm-ssh-key', keyFileVariable: 'SSH_KEY'),
                        string(credentialsId: 'GCP_VM_IP', variable: 'VM_IP'),
                        string(credentialsId: 'GCP_VM_USER', variable: 'VM_USER')
                    ]) {
                        sh '''
                            chmod 600 $SSH_KEY
                            ssh -i $SSH_KEY -o StrictHostKeyChecking=no $VM_USER@$VM_IP "
                                kubectl rollout undo deployment/aceest-fitness-app -n default || true
                                echo '--- Rollback: pod state ---'
                                kubectl get pods -n default -l app=aceest-fitness-app --ignore-not-found
                                echo '--- Rollback: current image ---'
                                kubectl get deployment aceest-fitness-app -n default \
                                    -o jsonpath='{.spec.template.spec.containers[0].image}' || true
                                echo ''
                            "
                        '''
                    }
                } else if (params.DEPLOY_STRATEGY == 'shadow') {
                    withCredentials([
                        sshUserPrivateKey(credentialsId: 'gcp-vm-ssh-key', keyFileVariable: 'SSH_KEY'),
                        string(credentialsId: 'GCP_VM_IP', variable: 'VM_IP'),
                        string(credentialsId: 'GCP_VM_USER', variable: 'VM_USER')
                    ]) {
                        sh '''
                            chmod 600 $SSH_KEY
                            ssh -i $SSH_KEY -o StrictHostKeyChecking=no $VM_USER@$VM_IP "
                                chmod +x ~/shadow/rollback.sh
                                ~/shadow/rollback.sh || true
                            "
                        '''
                    }
                } else if (params.DEPLOY_STRATEGY == 'ab-testing') {
                    withCredentials([
                        sshUserPrivateKey(credentialsId: 'gcp-vm-ssh-key', keyFileVariable: 'SSH_KEY'),
                        string(credentialsId: 'GCP_VM_IP', variable: 'VM_IP'),
                        string(credentialsId: 'GCP_VM_USER', variable: 'VM_USER')
                    ]) {
                        sh '''
                            chmod 600 $SSH_KEY
                            ssh -i $SSH_KEY -o StrictHostKeyChecking=no $VM_USER@$VM_IP "
                                chmod +x ~/ab-testing/rollback.sh
                                ~/ab-testing/rollback.sh || true
                            "
                        '''
                    }
                }
            }
        }
        always {
            cleanWs()
        }
    }
}
