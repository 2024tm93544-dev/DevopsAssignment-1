pipeline {
    agent any
    parameters {
        string(
            name: 'IMAGE_VERSION',
            defaultValue: '',
            description: 'Docker image version tag. Leave blank to use the Jenkins build number.'
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
                    # Install dependencies if missing
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
        stage('Deploy to GCP VM') {
            steps {
                withCredentials([
                    sshUserPrivateKey(
                        credentialsId: 'gcp-vm-ssh-key',
                        keyFileVariable: 'SSH_KEY'
                    ),
                    string(credentialsId: 'GCP_VM_IP', variable: 'VM_IP'),
                    string(credentialsId: 'GCP_VM_USER', variable: 'VM_USER')
                ]) {
                    sh '''
                        chmod 600 $SSH_KEY
                        scp -i $SSH_KEY -o StrictHostKeyChecking=no k8s/deployment.yaml $VM_USER@$VM_IP:~/deployment.yaml
                        ssh -i $SSH_KEY -o StrictHostKeyChecking=no $VM_USER@$VM_IP "kubectl apply -f ~/deployment.yaml"
                    '''
                }
            }
        }
    }
    post {
        always {
            cleanWs()
        }
    }
}
