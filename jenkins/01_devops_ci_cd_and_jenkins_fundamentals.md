# DevOps, CI/CD, and Jenkins Fundamentals

DevOps는 개발과 운영이 변경의 배포와 운영 결과에 함께 책임을 지고, 검증과 피드백을 빠르게 돌리는 방식이다. CI/CD는 그중 코드 통합, 빌드, 테스트, 릴리스 흐름을 자동화하는 데 쓰인다. 이 문서는 Jenkins를 Docker로 실행하고 첫 Pipeline에서 파일을 만들고 검증하는 과정까지 다룬다. [DORA Continuous Integration](https://dora.dev/capabilities/continuous-integration/) · [DORA Continuous Delivery](https://dora.dev/capabilities/continuous-delivery/)

## 1. Waterfall과 Agile의 피드백 주기

| 관점 | Waterfall | Agile |
| --- | --- | --- |
| 진행 방식 | 요구 분석, 설계, 구현, 검증을 단계별로 진행한다. | 작고 사용 가능한 변경을 짧은 주기로 계획하고 구현하고 검증한다. |
| 피드백 | 단계가 끝날 때 산출물을 검토하고 변경 사항을 다음 계획에 반영한다. | 동작하는 소프트웨어와 사용자 피드백을 다음 반복에 반영한다. |
| 자동화와의 관계 | 빌드와 테스트를 자동화하면 각 단계의 반복 작업을 줄일 수 있다. | 변경을 자주 통합하므로 자동 검증을 통해 피드백을 앞당길 수 있다. |

[Managing the Development of Large Software Systems](https://doi.org/10.7551/mitpress/12274.003.0035) · [Principles behind the Agile Manifesto](https://agilemanifesto.org/principles.html)

## 2. 클라우드 네이티브 애플리케이션의 구성

| 구성 | 역할 |
| --- | --- |
| 실행 아티팩트 | 컨테이너 이미지 등 버전이 있는 형식으로 애플리케이션과 실행 의존성을 패키징한다. |
| 실행 환경과 선언적 설정 | 컨테이너를 실행할 자원과 원하는 상태를 정의한다. 필요에 따라 오케스트레이터가 상태를 조정한다. |
| 서비스 간 계약 | API나 메시지 스키마를 정의하고, 서비스로 나눈 경우 변경과 배포가 다른 서비스에 미치는 영향을 관리한다. |
| 관측 가능성 | 로그, 메트릭, 트레이스로 배포 전후의 오류와 지연을 비교하고 운영 상태를 확인한다. |
| 자동화 | 같은 절차로 변경을 검증하고, 버전이 추적되는 아티팩트를 대상 환경으로 승격한다. |

[CNCF Cloud Native Definition](https://github.com/cncf/toc/blob/main/DEFINITION.md) · [CNCF Observability Glossary](https://glossary.cncf.io/observability/)

## 3. CI/CD 자동화 도구와 워크플로

**Continuous Integration**에서는 개발자가 변경을 자주 통합하고 빌드와 자동화된 테스트로 검증한다. **Continuous Delivery**는 검증된 변경을 배포 가능한 상태로 유지하며 운영 반영에 승인 단계를 둘 수 있다. **Continuous Deployment**는 정해진 검사와 정책을 통과한 변경을 운영 환경까지 자동으로 반영한다. [DORA Continuous Integration](https://dora.dev/capabilities/continuous-integration/) · [DORA Continuous Delivery](https://dora.dev/capabilities/continuous-delivery/) · [DORA Deployment Automation](https://dora.dev/capabilities/deployment-automation/)

| 흐름 | 자동화가 하는 일 |
| --- | --- |
| 변경 감지 | Git의 변경이나 Pull Request로 작업을 시작하고, 실행을 커밋과 연결한다. |
| 빌드와 검사 | 컴파일과 테스트를 실행하고 결과를 기록한다. |
| 패키징과 보관 | 검증한 JAR나 이미지를 버전과 함께 저장한다. |
| 배포와 확인 | 보관한 아티팩트를 대상 환경에 배포하고 스모크 테스트와 운영 지표를 확인한다. |

Jenkins 같은 자동화 서버는 도구를 호출할 순서와 실패 시 동작을 관리한다. Gradle은 애플리케이션을 빌드할 수 있고, Docker는 컨테이너 이미지 패키징이나 실행을 맡을 수 있다. Jenkins Pipeline은 이 작업을 단계로 묶고 각 실행의 로그와 결과를 보관한다. [Jenkins Pipeline](https://www.jenkins.io/doc/book/pipeline/)

## 4. Docker에서 Jenkins 시작하기

Jenkins의 **controller**는 작업 설정과 대기열을 관리하고, **agent**는 배정된 명령을 실행한다. 이 실습에는 하나의 Jenkins 컨테이너가 있으며, 내장 실행 노드로 첫 작업을 실행한다. 실제 CI에서는 빌드 권한과 부하를 분리하기 위해 별도 agent에 실행을 배정한다. [Jenkins Managing Nodes](https://www.jenkins.io/doc/book/managing/nodes/) · [Jenkins Docker Image](https://github.com/jenkinsci/docker)

Docker와 Docker Compose를 사용할 수 있는 환경에서 실습 디렉터리를 만들고 다음 내용을 `compose.yaml`로 저장한다.

```yaml
services:
  jenkins:
    image: jenkins/jenkins:lts-jdk21
    ports:
      - "127.0.0.1:18080:8080"
    volumes:
      - jenkins_home:/var/jenkins_home

volumes:
  jenkins_home:
```

```sh
docker compose up -d
docker compose ps
```

1. 브라우저에서 `http://127.0.0.1:18080`에 접속해 **Unlock Jenkins**가 나타날 때까지 기다린다. 시작 상태는 `docker compose logs jenkins`에서 확인할 수 있다.
2. `docker compose exec -T jenkins cat /var/jenkins_home/secrets/initialAdminPassword`로 초기 관리자 비밀번호를 조회해 잠금을 해제한다. **Install suggested plugins**를 선택한다. 첫 실습에는 **Pipeline** 플러그인이 필요하다.
3. 관리자 계정을 만들고 Jenkins URL을 확인한 뒤 대시보드로 이동한다.

Jenkins 설정과 플러그인, 작업 데이터는 `jenkins_home` 볼륨에 저장된다. `docker compose down`으로 실습을 종료하면 볼륨이 남아 다음 실행에서 설정을 이어 쓸 수 있다. [Jenkins Docker Installation](https://www.jenkins.io/doc/book/installing/docker/) · [Docker Compose Down](https://docs.docker.com/reference/cli/docker/compose/down/)

## 5. 첫 번째 Item과 Pipeline

대시보드에서 **New Item**을 고르고 이름에 `first-ci`를 입력한 뒤 **Pipeline** 유형을 선택한다. 설정의 **Pipeline** 항목에서 **Pipeline script**를 선택하고 아래 스크립트를 저장한다. 이 예제는 빌드 단계에서 파일을 만들고, 테스트 단계에서 기대한 내용과 일치하는지 확인한다. [Getting Started with Jenkins Pipeline](https://www.jenkins.io/doc/book/pipeline/getting-started/)

```groovy
pipeline {
    agent any

    stages {
        stage('Build') {
            steps {
                sh 'mkdir -p build && echo "hello from Jenkins" > build/message.txt'
            }
        }
        stage('Test') {
            steps {
                sh 'grep -Fx "hello from Jenkins" build/message.txt'
            }
        }
    }

    post {
        success {
            archiveArtifacts artifacts: 'build/message.txt'
        }
    }
}
```

**Build Now**를 눌러 실행하고 **Console Output**에서 `Build`, `Test`, 마지막의 `Finished: SUCCESS`를 확인한다. 같은 실행의 아티팩트 목록에서 `message.txt`를 열 수 있다. 팀에서 이 구성을 관리할 때는 Pipeline을 저장소의 `Jenkinsfile`로 옮겨 애플리케이션 변경과 함께 리뷰할 수 있다. [Declarative Pipeline Syntax](https://www.jenkins.io/doc/book/pipeline/syntax/) · [Jenkins Pipeline Build Artifacts](https://www.jenkins.io/doc/pipeline/steps/core/#archiveartifacts-archive-the-artifacts)
