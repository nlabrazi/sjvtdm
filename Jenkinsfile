@Library('nabster-ci') _

pipeline {
    agent {
        docker {
            image 'python:3.11'
        }
    }

    stages {
        stage('Notify start') {
            steps {
                notifyTelegram('started')
            }
        }

        stage('Install') {
            steps {
                sh 'python -m pip install --upgrade pip'
                sh 'python -m pip install -r requirements.txt'
            }
        }

        stage('Unit tests') {
            steps {
                sh 'python -m unittest discover -s tests -v'
            }
        }
    }

    post {
        success {
            notifyTelegram('success')
        }

        failure {
            notifyTelegram('failed')
        }
    }
}
