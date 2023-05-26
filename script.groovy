def buildJar() {
    echo "building the application..."
    sh 'pwd'
} 

def buildImage() {
    echo "building the docker image..."
    withCredentials([usernamePassword(credentialsId: 'DockerHub', passwordVariable: 'PASSWORD', usernameVariable: 'USERNAME')]) {
        sh 'docker build -t djangoreactdev/wow-effecting:1.0 ./front-next'
        sh 'echo $PASSWORD | docker login -u $USERNAME --password-stdin'
        sh 'docker push djangoreactdev/wow-effecting:1.0'
    }
} 

def deployApp() {
    echo 'deploying the application...'
    sh 'docker pull djangoreactdev/wow-effecting:1.0'
    sh 'docker stop wow-effecting || true'
    sh 'docker rm wow-effecting || true'
    sh 'docker rmi wow-effecting || true'
    sh 'docker pull djangoreactdev/wow-effecting:1.0'
    sh 'docker run -d --name wow-effecting -p 81:3000 djangoreactdev/wow-effecting:1.0'
} 

return this
