pipeline {
    agent any
    environment {
        DOCKER_IMAGE = "aceest-fitness-app:${env.BUILD_ID}"
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
                    pytest tests/ -v
                '''
            }
        }
        stage('Docker Phase') {
            steps {
                sh '''
                    docker build -t $DOCKER_IMAGE .
                    docker run --rm -e PYTHONPATH=. $DOCKER_IMAGE pytest tests/ -v
                '''
            }
        }
    }
    post {
        always {
            cleanWs()
        }
    }
}