# Infrastructure as Code with Jenkins and Ansible

Infrastructure as Code(IaC)는 배포 환경의 구성을 코드로 기록해 변경을 검토하고 같은 절차로 다시 적용하는 방식이다. Jenkins는 검증과 배포를 단계별로 실행하고, Ansible은 인벤토리와 플레이북을 읽어 대상의 상태를 지정한 구성에 맞춘다. 이 실습은 Docker Compose 위에서 Ansible로 Nginx 이미지를 가져오고 컨테이너를 실행한다. [Ansible Getting Started](https://docs.ansible.com/ansible/latest/getting_started/get_started_ansible.html) · [Jenkins Pipeline](https://www.jenkins.io/doc/book/pipeline/)

## 1. 인벤토리에서 실제 실행까지

| 요소 | 역할 | 실습에서 사용하는 값 |
| --- | --- | --- |
| 컨트롤 노드 | Ansible 명령을 실행한다. | Jenkins 컨테이너 |
| 인벤토리 | 실행 대상과 접속 방법을 정의한다. | `deploy` 그룹의 `localhost`, 로컬 연결 |
| 모듈 | 하나의 작업을 수행한다. | Docker 이미지 풀, 컨테이너 실행, HTTP 확인 |
| 플레이북 | 대상 그룹과 적용할 작업의 순서를 정의한다. | `deploy.yml` |

Ansible은 인벤토리에서 대상을 선택하고 연결 방식에 따라 모듈을 실행한다. 이 실습에서는 모듈이 Jenkins 컨테이너 안에서 실행되고, 같은 Compose 네트워크의 Docker API에 TLS로 요청을 보낸다. 모듈이 현재 상태를 비교할 수 있도록 원하는 상태를 지정하면, 동일한 플레이북을 다시 실행해도 이미 충족된 작업은 보통 변경하지 않는다. [Ansible Inventory Guide](https://docs.ansible.com/ansible/latest/inventory_guide/intro_inventory.html) · [Ansible Playbooks](https://docs.ansible.com/ansible/latest/playbook_guide/playbooks_intro.html)

## 2. Docker에서 Jenkins와 Ansible 실행

새 실습 디렉터리의 `jenkins/Dockerfile`에 다음 내용을 저장한다. Ansible 실행 환경과 Docker 모듈을 Jenkins 이미지에 포함한다. [Jenkins Docker Installation](https://www.jenkins.io/doc/book/installing/docker/) · [Installing Collections](https://docs.ansible.com/ansible/latest/collections_guide/collections_installing.html)

```dockerfile
FROM jenkins/jenkins:lts-jdk21

USER root
RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 python3-venv \
    && rm -rf /var/lib/apt/lists/*

ENV PATH="/opt/ansible/bin:${PATH}" \
    ANSIBLE_COLLECTIONS_PATH=/opt/ansible-collections
RUN python3 -m venv /opt/ansible \
    && pip install --no-cache-dir ansible-core==2.19.10 requests==2.32.5 \
    && ansible-galaxy collection install community.docker:==4.8.1 -p /opt/ansible-collections

USER jenkins
RUN jenkins-plugin-cli --jenkins-update-center-download-url https://archives.jenkins.io/plugins \
    --plugins workflow-aggregator pipeline-model-definition
```

아래 내용을 실습 디렉터리의 `compose.yaml`에 둔다. 전용 Docker 엔진이 인증서를 생성하고, Jenkins에서 읽기 전용으로 사용한다. Jenkins 웹 UI는 호스트의 `18085`번으로, 배포된 서비스는 `18086`번으로 연결한다. [Jenkins Docker Installation](https://www.jenkins.io/doc/book/installing/docker/) · [Docker Daemon TLS](https://docs.docker.com/engine/security/protect-access/)

```yaml
services:
  jenkins:
    build: ./jenkins
    depends_on:
      docker-engine:
        condition: service_healthy
    environment:
      DOCKER_HOST: tcp://docker:2376
      DOCKER_TLS_VERIFY: "1"
      DOCKER_CERT_PATH: /certs/client
    ports:
      - "127.0.0.1:18085:8080"
    volumes:
      - jenkins_home:/var/jenkins_home
      - docker_certs:/certs/client:ro
      - ./lab:/lab:ro

  docker-engine:
    image: docker:28-dind
    privileged: true
    environment:
      DOCKER_TLS_CERTDIR: /certs
    networks:
      default:
        aliases:
          - docker
    healthcheck:
      test: ["CMD", "docker", "-H", "unix:///var/run/docker.sock", "info"]
      interval: 2s
      timeout: 3s
      retries: 30
    ports:
      - "127.0.0.1:18086:8080"
    volumes:
      - docker_certs:/certs/client
      - docker_data:/var/lib/docker

volumes:
  jenkins_home:
  docker_certs:
  docker_data:
```

## 3. Ansible 설정과 기본 명령

`lab/ansible.cfg`는 인벤토리 파일의 위치를 지정한다. 이어서 `lab/inventory.ini`에 `deploy` 그룹을 만들고 모듈이 가상 환경의 Python을 사용하도록 설정한다. [Ansible Configuration Settings](https://docs.ansible.com/ansible/latest/reference_appendices/config.html) · [Ansible Connection Details](https://docs.ansible.com/ansible/latest/inventory_guide/connection_details.html)

`lab/ansible.cfg`

```ini
[defaults]
inventory = ./inventory.ini
```

`lab/inventory.ini`

```ini
[deploy]
localhost ansible_connection=local ansible_python_interpreter=/opt/ansible/bin/python
```

아래 명령을 실행해 컨테이너에서 설정과 모듈을 확인한다. `ansible.builtin.ping`은 모듈이 대상에서 실행되는지 확인하고 `pong`을 돌려준다. [Ansible Ad Hoc Commands](https://docs.ansible.com/ansible/latest/command_guide/intro_adhoc.html) · [Ansible Ping Module](https://docs.ansible.com/ansible/latest/collections/ansible/builtin/ping_module.html)

```sh
docker compose up -d --build
docker compose exec -T -w /lab jenkins ansible --version
docker compose exec -T -w /lab jenkins ansible-inventory --graph
docker compose exec -T -w /lab jenkins ansible deploy -m ansible.builtin.ping
docker compose exec -T -w /lab jenkins ansible-doc community.docker.docker_container
```

## 4. 플레이북으로 이미지와 컨테이너 관리

`lab/deploy.yml`에 아래 내용을 저장한다. `docker_image_pull`은 전용 엔진에 이미지가 없을 때 내려받고, `docker_container`는 지정한 이미지와 포트로 컨테이너가 실행 중인지 확인한다. Docker 모듈은 Compose에서 전달한 `DOCKER_HOST`, `DOCKER_TLS_VERIFY`, `DOCKER_CERT_PATH`를 사용한다. [Docker Image Pull Module](https://docs.ansible.com/ansible/latest/collections/community/docker/docker_image_pull_module.html) · [Docker Container Module](https://docs.ansible.com/ansible/latest/collections/community/docker/docker_container_module.html)

```yaml
- name: Deploy the web container
  hosts: deploy
  gather_facts: false
  vars:
    web_image: nginx:1.28-alpine

  tasks:
    - name: Pull the image if it is missing
      community.docker.docker_image_pull:
        name: "{{ web_image }}"
        pull: not_present

    - name: Start the web container
      community.docker.docker_container:
        name: ansible-lab-web
        image: "{{ web_image }}"
        state: started
        pull: never
        published_ports:
          - "8080:80"
        restart_policy: unless-stopped

    - name: Wait for the web server
      ansible.builtin.uri:
        url: http://docker-engine:8080/
        status_code: 200
        timeout: 2
      register: web_response
      until: web_response is succeeded
      retries: 20
      delay: 1
```

```sh
docker compose exec -T -w /lab jenkins ansible-playbook --syntax-check deploy.yml
docker compose exec -T -w /lab jenkins ansible-playbook deploy.yml
curl -fsS http://127.0.0.1:18086/
```

첫 실행에서는 이미지나 컨테이너 상태가 바뀌면 `changed`로 표시된다. 같은 환경에 다시 적용할 때는 `changed=0`인지 확인한다. `not_present` 정책은 같은 태그가 로컬에 있으면 재사용한다. 배포 버전을 바꿀 때는 플레이북의 이미지 태그나 다이제스트를 갱신한다.

## 5. Jenkins에서 플레이북 실행

`http://127.0.0.1:18085`에서 [기본 문서의 초기 설정 절차](01_devops_ci_cd_and_jenkins_fundamentals.md#4-docker에서-jenkins-시작하기)를 따라 관리자 계정을 만든다. **New Item**에서 `ansible-deploy`라는 **Pipeline**을 생성하고 **Pipeline script**에 다음 코드를 저장한다. 준비 단계는 읽기 전용 입력을 Jenkins 작업 공간으로 복사한다. 검증 단계에서 문법 오류가 나면 배포 단계가 진행되지 않는다. [Jenkins Declarative Pipeline](https://www.jenkins.io/doc/book/pipeline/syntax/)

```groovy
pipeline {
    agent any

    options {
        disableConcurrentBuilds()
    }

    stages {
        stage('Prepare') {
            steps {
                deleteDir()
                sh 'cp -R /lab/. .'
            }
        }
        stage('Validate Playbook') {
            steps {
                sh 'ansible-playbook --syntax-check deploy.yml'
            }
        }
        stage('Deploy Container') {
            steps {
                sh 'ansible-playbook deploy.yml'
            }
        }
    }
}
```

**Build Now**로 실행한 뒤 Console Output의 `failed=0`과 마지막의 `Finished: SUCCESS`를 확인한다. Jenkins 작업을 한 번 더 실행해 변경이 없는지도 확인할 수 있다. 팀에서 관리할 때는 인벤토리, 플레이북, Jenkinsfile을 Git에 함께 두고 [앞 문서의 SCM 체크아웃 방식](02_jenkins_ci_cd_with_git_maven_tomcat_and_docker.md)으로 연결한다. 실습을 마치면 `docker compose down`으로 종료한다.
