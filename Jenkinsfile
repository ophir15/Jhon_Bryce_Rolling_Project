// Jenkins Pipeline for CI/CD Integration

pipeline {
   agent any
   
   environment {
       IMAGE_NAME = 'ophir15/rolling_project'
       IMAGE_TAG = "${env.BUILD_NUMBER}"
   }
   
   stages {
       stage('Clone Repository') {
           steps {
               checkout scm
           }
       }
       
       stage('Parallel Checks') {
           parallel {
               stage('Linting') {
                   steps {
                       sh '''
                           set +e
                           echo "Running linting..."
                           if command -v flake8 >/dev/null 2>&1; then
                             flake8 py
                           else
                             echo "flake8 not installed, skipping."
                           fi
                           if command -v shellcheck >/dev/null 2>&1; then
                             SHELL_FILES=$(find . -name "*.sh" -type f 2>/dev/null)
                             if [ -n "$SHELL_FILES" ]; then
                               shellcheck $SHELL_FILES
                             else
                               echo "No shell scripts found, skipping."
                             fi
                           else
                             echo "shellcheck not installed, skipping."
                           fi
                           if command -v hadolint >/dev/null 2>&1; then
                             hadolint Dockerfile
                           else
                             echo "hadolint not installed, skipping."
                           fi
                           set -e
                       '''
                   }
               }
               stage('Security Scanning') {
                   steps {
                       sh '''
                           set +e
                           echo "Running security scans..."
                           if command -v bandit >/dev/null 2>&1; then
                             bandit -r py -q
                           else
                             echo "bandit not installed, skipping."
                           fi
                           if command -v trivy >/dev/null 2>&1; then
                             trivy fs --no-progress --exit-code 0 .
                           else
                             echo "trivy not installed, skipping."
                           fi
                           set -e
                       '''
                   }
               }
           }
       }
       
       stage('Build Docker Image') {
           steps {
               script {
                   def hasDocker = sh(script: 'command -v docker >/dev/null 2>&1', returnStatus: true) == 0
                   if (!hasDocker) {
                       echo 'Docker CLI not available on this agent. Skipping image build.'
                       return
                   }
               }
               withCredentials([usernamePassword(credentialsId: 'dockerhub-credentials', usernameVariable: 'DOCKERHUB_USERNAME', passwordVariable: 'DOCKERHUB_PASSWORD')]) {
                   sh '''
                       set -e
                       echo "${DOCKERHUB_PASSWORD}" | docker login -u "${DOCKERHUB_USERNAME}" --password-stdin || {
                         echo "Docker login failed. Check Jenkins credentials and token scopes."
                         exit 1
                       }
                       docker build -t ${IMAGE_NAME}:${IMAGE_TAG} .
                   '''
               }
           }
       }
       
      stage('Push to Docker Hub') {
          steps {
              script {
                  def hasDocker = sh(script: 'command -v docker >/dev/null 2>&1', returnStatus: true) == 0
                  if (!hasDocker) {
                      echo 'Docker CLI not available on this agent. Skipping Docker Hub push.'
                      return
                  }
              }
              withCredentials([usernamePassword(credentialsId: 'dockerhub-credentials', usernameVariable: 'DOCKERHUB_USERNAME', passwordVariable: 'DOCKERHUB_PASSWORD')]) {
                  sh '''
                      set -e
                      echo "${DOCKERHUB_PASSWORD}" | docker login -u "${DOCKERHUB_USERNAME}" --password-stdin || {
                        echo "Docker login failed. Check Jenkins credentials and token scopes."
                        exit 1
                      }
                      docker push ${IMAGE_NAME}:${IMAGE_TAG} || {
                        echo "Docker push failed. Token likely lacks write scope."
                        exit 1
                      }
                  '''
              }
          }
      }
   }
   
   post {
       success {
           echo 'Pipeline completed successfully!'
       }
       failure {
           echo 'Pipeline failed! Check logs for details.'
       }
   }
}