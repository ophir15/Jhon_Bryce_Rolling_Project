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