# Advanced Jenkins Pipelines with Maven, Tomcat, and Docker

이 실습은 Jenkins 실행마다 Maven WAR를 빌드하고 보관한 뒤, 선택한 대상에 배포한다. 기본값은 빌드와 검증까지이며, Tomcat 또는 Docker 배포를 선택하면 해당 단계와 HTTP 확인이 이어진다. Jenkins, Maven, Tomcat, Docker 엔진은 [02번 Docker Compose 실습](02_jenkins_ci_cd_with_git_maven_tomcat_and_docker.md)의 구성을 사용한다. [Jenkins Declarative Pipeline Syntax](https://www.jenkins.io/doc/book/pipeline/syntax/)

## 1. Delivery Pipeline View에서 배포 흐름 읽기

Delivery Pipeline 플러그인은 여러 Job의 연결 관계나 하나의 Jenkinsfile에 정의된 단계들을 화면에 보여 준다. 이 실습에서는 `sample-war-ci`의 최근 실행을 한 화면에 모아 빌드 성공, 조건으로 건너뛴 배포, 실패한 단계를 구분한다. [Delivery Pipeline Plugin](https://plugins.jenkins.io/delivery-pipeline-plugin/)

02번 실습 디렉터리의 `jenkins/Dockerfile`에서 플러그인 설치 명령을 다음과 같이 바꾼 뒤 `docker compose up -d --build jenkins`로 적용한다. Delivery Pipeline의 아래 버전은 Jenkins 2.555.3 이상과 Java 21을 사용한다. [Delivery Pipeline Plugin Requirements](https://plugins.jenkins.io/delivery-pipeline-plugin/#requirements)

```dockerfile
RUN jenkins-plugin-cli --jenkins-update-center-download-url https://archives.jenkins.io/plugins \
    --plugins workflow-aggregator pipeline-model-definition git delivery-pipeline-plugin:1131.v20dd664f6ddd
```

Jenkins 대시보드에서 뷰 탭 옆의 `+`를 눌러 **Delivery Pipeline View**를 만든다. 뷰의 **Pipelines**에 컴포넌트를 추가하고 초기 Job으로 `sample-war-ci`를 입력한다. 실행 상태는 뷰에서 비교하고, 개별 단계의 오류나 테스트 결과는 해당 실행의 Console Output에서 확인한다. [Configuring a Delivery Pipeline View](https://plugins.jenkins.io/delivery-pipeline-plugin/#configuring-a-view)

## 2. Pipeline 스크립트와 Pipeline Syntax

새 Pipeline Item에서 **Pipeline script**를 선택하면 Jenkins 화면에서 스크립트를 입력할 수 있다. 저장소에 있는 Jenkinsfile을 사용할 때는 **Pipeline script from SCM**을 선택하고 Git URL, 브랜치, 스크립트 경로를 지정한다. 이 실습의 `checkout scm`은 02번에서 설정한 SCM을 참조한다. [Getting Started with Jenkins Pipeline](https://www.jenkins.io/doc/book/pipeline/getting-started/)

| 도구 또는 문법 | 사용하는 곳 |
| --- | --- |
| Declarative Pipeline | `pipeline`, `stages`, `steps`로 실행 구조를 작성한다. |
| `script` 블록 | 조건에 맞게 URL을 고르는 등 단계 내부에 Groovy 로직을 넣는다. |
| Snippet Generator | **Pipeline Syntax**에서 Step의 인자를 입력하고 현재 Jenkins에 설치된 플러그인에 맞는 코드를 생성한다. |
| Declarative Directive Generator | `when`, `parameters` 같은 Declarative 지시어를 구성한다. |

Snippet Generator에서 `archiveArtifacts: Archive the artifacts`를 골라 파일 패턴을 `target/sample.war`로 지정하고 지문 기록을 선택한다. 생성된 Step을 Jenkinsfile의 빌드 단계에 붙인다. 지문을 기록하면 Jenkins에서 아티팩트를 식별할 수 있다. [Pipeline Syntax Tools](https://www.jenkins.io/doc/book/pipeline/getting-started/#built-in-documentation) · [archiveArtifacts](https://www.jenkins.io/doc/pipeline/steps/core/#archiveartifacts-archive-the-artifacts)

## 3. Maven 빌드와 조건부 배포

02번 실습의 `sample-war/Jenkinsfile`을 아래 내용으로 교체한다. Jenkins Item은 기존 `sample-war-ci`를 사용한다.

| `DEPLOY_TARGET` | 실행 결과 |
| --- | --- |
| `build-only` | Git 체크아웃, Maven 검증과 WAR 보관까지 실행한다. Poll SCM의 기본 동작이다. |
| `tomcat` | 같은 WAR를 실행 중인 Tomcat에 배포하고 `18083`번 포트에서 확인한다. |
| `docker` | 같은 WAR를 담은 이미지를 빌드하고 기존 실습 컨테이너를 교체한다. `18084`번 포트에서 확인한다. |

```groovy
pipeline {
    agent any

    options {
        skipDefaultCheckout()
        disableConcurrentBuilds()
    }

    parameters {
        choice(
            name: 'DEPLOY_TARGET',
            choices: ['build-only', 'tomcat', 'docker'],
            description: 'Choose what to deploy after building the WAR'
        )
    }

    triggers {
        pollSCM('H/2 * * * *')
    }

    stages {
        stage('Checkout') {
            steps {
                deleteDir()
                checkout scm
            }
        }
        stage('Maven Verify') {
            steps {
                sh 'mvn -B -ntp clean verify'
                sh 'jar tf target/sample.war | grep -Fx index.html'
                archiveArtifacts artifacts: 'target/sample.war', fingerprint: true
            }
        }
        stage('Deploy to Tomcat') {
            when {
                expression { params.DEPLOY_TARGET == 'tomcat' }
            }
            steps {
                sh '''
                    set -eu
                    cp target/sample.war "/war-deploy/.sample.war.$BUILD_NUMBER"
                    mv "/war-deploy/.sample.war.$BUILD_NUMBER" /war-deploy/sample.war
                '''
            }
        }
        stage('Deploy to Docker') {
            when {
                expression { params.DEPLOY_TARGET == 'docker' }
            }
            steps {
                sh '''
                    set -eu
                    image="jenkins-lab-sample:$BUILD_NUMBER"
                    mkdir -p target/docker-context
                    cp Dockerfile target/docker-context/Dockerfile
                    cp target/sample.war target/docker-context/sample.war
                    docker build -t "$image" target/docker-context
                    if docker container inspect jenkins-lab-sample >/dev/null 2>&1; then
                        docker container rm -f jenkins-lab-sample
                    fi
                    docker run -d --name jenkins-lab-sample -p 8080:8080 "$image"
                '''
            }
        }
        stage('Verify Deployment') {
            when {
                expression { params.DEPLOY_TARGET in ['tomcat', 'docker'] }
            }
            steps {
                script {
                    def host = params.DEPLOY_TARGET == 'tomcat' ? 'tomcat' : 'docker-engine'
                    withEnv(["SMOKE_URL=http://${host}:8080/sample/index.html"]) {
                        timeout(time: 90, unit: 'SECONDS') {
                            waitUntil(initialRecurrencePeriod: 1000, quiet: true) {
                                sh(returnStatus: true, script: '''
                                    curl -fsS --max-time 2 "$SMOKE_URL" -o target/live-index.html &&
                                      cmp -s src/main/webapp/index.html target/live-index.html
                                ''') == 0
                            }
                        }
                    }
                }
            }
        }
    }

    post {
        always {
            echo "Build result: ${currentBuild.currentResult}"
        }
    }
}
```

Tomcat 배포는 WAR를 임시 이름으로 복사한 뒤 최종 이름으로 바꾼다. Docker 배포는 동일한 WAR가 들어간 새 이미지로 컨테이너를 교체한다. 검증 단계는 HTTP 응답 내용이 체크아웃한 페이지와 일치할 때까지 기다리고, 제한 시간을 넘기면 실패한다. `disableConcurrentBuilds()`는 같은 Job의 여러 실행이 공유 배포 대상에 동시에 쓰는 일을 막는다. [Jenkins Pipeline Parameters and When](https://www.jenkins.io/doc/book/pipeline/syntax/) · [Pipeline waitUntil and timeout](https://www.jenkins.io/doc/pipeline/steps/workflow-basic-steps/)

02번의 Git 저장소를 이미 초기화했다면 컨테이너에 마운트된 새 Jenkinsfile을 작성용 저장소로 복사한 뒤 푸시한다. [Git update-server-info](https://git-scm.com/docs/git-update-server-info)

```sh
docker compose exec -T jenkins sh -eu <<'SH'
cd "$JENKINS_HOME/lab-source"
cp /seed/Jenkinsfile Jenkinsfile
git add Jenkinsfile
git commit -m 'Add parameterized deployment pipeline'
git push origin main
git --git-dir=/git-export/sample-war.git update-server-info
SH
```

## 4. 실행별 결과 확인

1. 새 Jenkinsfile을 처음 읽는 실행에서 기본값으로 Maven 빌드와 WAR 보관을 확인한다. 파라미터가 등록되면 Job 메뉴에 **Build with Parameters**가 표시된다.
2. **Build with Parameters**에서 `tomcat`을 골라 배포한다. Docker 배포 단계가 건너뛰어지고, 빌드 완료 후 `http://127.0.0.1:18083/sample/`에서 페이지가 열리는지 확인한다.
3. `docker`를 골라 실행한다. Tomcat 배포 단계가 건너뛰어지고 `http://127.0.0.1:18084/sample/`에서 같은 페이지가 열리는지 확인한다.
4. 각 실행의 **Console Output**에서 `Finished: SUCCESS`를, 아티팩트 목록에서 `target/sample.war`를 확인한다. **Delivery Pipeline View**에서 세 실행의 단계 상태를 비교한다.

한 Jenkins 실행에서 보관과 배포에 쓰는 WAR는 같은 파일이다. 02번의 Compose 서비스와 데이터 볼륨을 이어 쓰므로 이전 배포가 이미 있다면, 배포 대상을 선택하지 않아 건너뛴 경우에도 그 서비스는 기존 페이지를 계속 응답할 수 있다. 어느 실행이 배포를 수행했는지는 해당 실행의 단계 로그로 확인한다.
