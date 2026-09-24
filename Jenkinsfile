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
                sh 'python -m venv .venv'
                sh '.venv/bin/python -m pip install -r requirements-dev.txt'
            }
        }

        stage('Unit tests') {
            steps {
                sh '.venv/bin/python -m coverage run -m unittest discover -s tests -v'
            }
            post {
                always {
                    sh '''
                        .venv/bin/python -m coverage report
                        .venv/bin/python -m coverage xml
                        .venv/bin/python -m coverage html
                    '''
                    archiveArtifacts artifacts: 'coverage.xml,htmlcov/**', allowEmptyArchive: true
                }
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
