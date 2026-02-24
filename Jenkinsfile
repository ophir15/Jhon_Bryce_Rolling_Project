# Jenkins Pipeline for CI/CD Integration

def appImage

pipeline {
   agent any
   
  environment {
      IMAGE_NAME = 'flask-aws-monitor'
      DOCKER_REPO = 'ophir15/rolling_project'
      DOCKER_REGISTRY = 'https://index.docker.io/v1/'
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
                      sh 'python -m pip install --upgrade flake8'
                      sh 'flake8 py'
                      sh 'SHELLCHECK_FILES=$(git ls-files "*.sh"); if [ -n "$SHELLCHECK_FILES" ]; then docker run --rm -v "$PWD:/work" -w /work koalaman/shellcheck:stable $SHELLCHECK_FILES; else echo "No shell scripts to lint"; fi'
                      sh 'docker run --rm -i hadolint/hadolint < Dockerfile'
                  }
              }
              stage('Security Scan') {
                  steps {
                      sh 'python -m pip install --upgrade bandit'
                      sh 'bandit -r py'
                      sh 'docker run --rm -v "$PWD:/work" -w /work aquasec/trivy:latest fs --scanners vuln,secret,config .'
                  }
              }
          }
      }
       
       stage('Build Docker Image') {
           steps {
              script {
                  appImage = docker.build("${env.DOCKER_REPO}:${env.BUILD_NUMBER}")
                  appImage.tag('latest')
              }
           }
       }
       
       stage('Push to Docker Hub') {
           steps {
              script {
                  docker.withRegistry("${env.DOCKER_REGISTRY}", 'dockerhub') {
                      appImage.push("${env.BUILD_NUMBER}")
                      appImage.push('latest')
                  }
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