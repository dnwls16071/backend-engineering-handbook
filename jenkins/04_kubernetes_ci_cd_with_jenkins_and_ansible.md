# Kubernetes CI/CD with Jenkins and Ansible

Jenkins가 웹 이미지를 빌드하고, Ansible이 그 이미지로 Kubernetes Deployment와 Service를 갱신하는 실습이다. Kubernetes 노드는 kind가 만드는 Docker 컨테이너다. Jenkins와 클러스터는 Docker Compose에서 실행하며, Jenkins는 전용 Docker 엔진과 Kubernetes API에 각각 TLS로 연결한다. [kind Quick Start](https://kind.sigs.k8s.io/docs/user/quick-start/) · [Jenkins Pipeline](https://www.jenkins.io/doc/book/pipeline/)

## 1. Kubernetes 객체와 배포 흐름

| 요소 | 역할 |
| --- | --- |
| Node와 Pod | 노드는 워크로드를 실행한다. Pod는 Kubernetes가 배치하는 실행 단위다. |
| Deployment | Pod 템플릿과 복제본 수를 관리하고 이미지 변경 시 롤아웃을 진행한다. |
| Service | 레이블로 Pod를 선택하고 일정한 접근 경로를 제공한다. |
| Ansible 플레이북 | Kubernetes API에 매니페스트를 적용하고 배포 결과를 확인한다. |

실습 순서는 이미지 빌드, kind 노드에 이미지 로드, Deployment와 Service 적용, 롤아웃과 HTTP 응답 확인이다. [Kubernetes Deployments](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/) · [Kubernetes Service](https://kubernetes.io/docs/concepts/services-networking/service/)

## 2. Docker Compose에 kind와 Jenkins 구성

새 실습 디렉터리에 `Dockerfile`을 둔다. 같은 Dockerfile의 `engine`은 kind가 사용할 엔진 이미지를, `jenkins`는 빌드와 배포 명령을 실행할 이미지를 정의한다. Ansible 설치 구성은 [앞 문서](03_infrastructure_as_code_with_jenkins_and_ansible.md)를 이어서 사용한다. [kind v0.30.0 Release](https://github.com/kubernetes-sigs/kind/releases/tag/v0.30.0) · [Jenkins Docker Installation](https://www.jenkins.io/doc/book/installing/docker/)

```dockerfile
FROM docker:28-cli AS tools
ARG TARGETARCH
RUN wget -qO /usr/local/bin/kind "https://kind.sigs.k8s.io/dl/v0.30.0/kind-linux-${TARGETARCH}" \
    && chmod 0755 /usr/local/bin/kind

FROM docker:28-dind AS engine
COPY --from=tools /usr/local/bin/kind /usr/local/bin/kind

FROM jenkins/jenkins:lts-jdk21 AS jenkins
USER root
COPY --from=tools /usr/local/bin/docker /usr/local/bin/docker
COPY --from=tools /usr/local/libexec/docker/cli-plugins/docker-buildx /usr/local/libexec/docker/cli-plugins/docker-buildx
COPY --from=tools /usr/local/bin/kind /usr/local/bin/kind
RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 python3-venv \
    && rm -rf /var/lib/apt/lists/*
ENV PATH="/opt/ansible/bin:${PATH}" \
    ANSIBLE_COLLECTIONS_PATH=/opt/ansible-collections
RUN python3 -m venv /opt/ansible \
    && pip install --no-cache-dir ansible-core==2.19.10 kubernetes==34.1.0 jsonpatch==1.33 \
    && ansible-galaxy collection install kubernetes.core:==5.1.0 -p /opt/ansible-collections
USER jenkins
RUN jenkins-plugin-cli --jenkins-update-center-download-url https://archives.jenkins.io/plugins \
    --plugins workflow-aggregator pipeline-model-definition
```

`compose.yaml`은 Jenkins UI를 `18087`번, 배포한 웹 서비스를 `18088`번에 연결한다. 실습용 Kubernetes API 주소는 Compose 내부의 `docker:6443`이다. [Docker Daemon TLS](https://docs.docker.com/engine/security/protect-access/) · [kind Configuration](https://kind.sigs.k8s.io/docs/user/configuration/)

```yaml
services:
  jenkins:
    build:
      context: .
      target: jenkins
    depends_on:
      docker-engine:
        condition: service_healthy
    environment:
      DOCKER_HOST: tcp://docker:2376
      DOCKER_TLS_VERIFY: "1"
      DOCKER_CERT_PATH: /certs/client
      KUBECONFIG: /var/jenkins_home/kube/config
    ports:
      - "127.0.0.1:18087:8080"
    volumes:
      - jenkins_home:/var/jenkins_home
      - docker_certs:/certs/client:ro
      - ./lab:/lab:ro

  docker-engine:
    build:
      context: .
      target: engine
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
      - "127.0.0.1:18088:8080"
    volumes:
      - docker_certs:/certs/client
      - docker_data:/var/lib/docker
      - ./kind.yaml:/kind.yaml:ro

volumes:
  jenkins_home:
  docker_certs:
  docker_data:
```

`kind.yaml`은 컨트롤 플레인 노드 하나를 정의한다. 노드의 `30080`번은 예제에서 사용할 Service의 NodePort와 일치해야 한다. API 서버 인증서에는 Jenkins가 사용할 DNS 이름 `docker`를 추가한다. [kind NodePort Mappings](https://kind.sigs.k8s.io/docs/user/configuration/#nodeport-with-port-mappings)

```yaml
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
networking:
  apiServerAddress: "0.0.0.0"
  apiServerPort: 6443
nodes:
  - role: control-plane
    extraPortMappings:
      - containerPort: 30080
        hostPort: 8080
        listenAddress: "0.0.0.0"
kubeadmConfigPatches:
  - |
    kind: ClusterConfiguration
    apiServer:
      certSANs:
        - docker
```

## 3. 클러스터 생성과 kubectl 기본 명령

아래의 `docker compose up`은 4절 파일을 `lab/`에 저장한 뒤 실행한다. kind가 만든 kubeconfig의 서버 주소를 Compose 내부 주소로 지정해 Jenkins 볼륨에 저장한다. kubeconfig에는 이 실습 클러스터의 관리자 자격 증명이 포함되므로 Jenkins 사용자만 읽을 수 있게 저장한다.

```sh
docker compose up -d --build
docker compose exec -T docker-engine kind create cluster \
  --name jenkins-lab --config /kind.yaml --wait 120s

docker compose exec -T docker-engine kind get kubeconfig --name jenkins-lab --internal |
  docker compose exec -T jenkins sh -eu -c '
    umask 077
    mkdir -p "$JENKINS_HOME/kube"
    sed "s|server: https://.*|server: https://docker:6443|" > "$KUBECONFIG"
    test -s "$KUBECONFIG"
  '
```

다음 함수는 kind 노드에 포함된 kubectl을 실행한다. 배포 전에는 `get nodes`로 노드 준비 상태를 보고, 배포 후에는 Pod와 Service, 롤아웃을 확인한다. `describe`의 이벤트는 대기 중인 Pod의 원인을 찾는 데 도움이 된다. [kubectl Quick Reference](https://kubernetes.io/docs/reference/kubectl/quick-reference/) · [kubectl rollout status](https://kubernetes.io/docs/reference/kubectl/generated/kubectl_rollout/kubectl_rollout_status/)

```sh
lab_kubectl() {
  docker compose exec -T docker-engine docker exec jenkins-lab-control-plane \
    kubectl --kubeconfig=/etc/kubernetes/admin.conf "$@"
}

lab_kubectl get nodes
lab_kubectl get deployments,pods,services
# 다음은 배포 후 실행
lab_kubectl rollout status deployment/jenkins-lab-web --timeout=90s
lab_kubectl describe deployment/jenkins-lab-web
lab_kubectl logs deployment/jenkins-lab-web
```

## 4. 매니페스트와 Ansible 플레이북

`lab/site/Dockerfile`은 현재 배포된 버전을 확인할 수 있도록 빌드 ID를 응답 본문에 넣는다.

```dockerfile
FROM nginx:1.28-alpine
ARG RELEASE
RUN printf 'Jenkins build %s\n' "$RELEASE" > /usr/share/nginx/html/index.html
```

`lab/resources.yaml.j2`는 Deployment와 Service를 정의한다. 두 객체의 네임스페이스를 `default`로 지정하고 셀렉터를 Pod의 `app` 레이블과 맞춘다. 빌드한 이미지는 kind 노드에 직접 로드하므로 매니페스트의 `imagePullPolicy`는 `Never`로 지정한다. [Loading an Image Into Your Cluster](https://kind.sigs.k8s.io/docs/user/quick-start/#loading-an-image-into-your-cluster) · [Kubernetes Images](https://kubernetes.io/docs/concepts/containers/images/)

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: jenkins-lab-web
  namespace: default
spec:
  replicas: 2
  selector:
    matchLabels:
      app: jenkins-lab-web
  template:
    metadata:
      labels:
        app: jenkins-lab-web
    spec:
      containers:
        - name: web
          image: "{{ image_ref }}"
          imagePullPolicy: Never
          ports:
            - containerPort: 80
          readinessProbe:
            httpGet:
              path: /
              port: 80
---
apiVersion: v1
kind: Service
metadata:
  name: jenkins-lab-web
  namespace: default
spec:
  type: NodePort
  selector:
    app: jenkins-lab-web
  ports:
    - port: 80
      targetPort: 80
      nodePort: 30080
```

`lab/deploy.yml`은 Jenkins 컨테이너에서 로컬로 실행된다. Jinja 템플릿의 이미지 값을 바인딩하고 `kubernetes.core.k8s` 모듈로 두 객체를 적용한다. 이 모듈은 `KUBECONFIG`를 사용한다. 적용 후 Service 응답에 해당 배포의 빌드 ID가 있는지 확인한다. [Ansible Kubernetes Module](https://docs.ansible.com/ansible/latest/collections/kubernetes/core/k8s_module.html) · [Ansible URI Module](https://docs.ansible.com/ansible/latest/collections/ansible/builtin/uri_module.html)

```yaml
- name: Deploy a web image to kind
  hosts: localhost
  connection: local
  gather_facts: false
  vars:
    ansible_python_interpreter: "{{ ansible_playbook_python }}"

  tasks:
    - name: Apply the Deployment and Service
      kubernetes.core.k8s:
        state: present
        definition: "{{ lookup('ansible.builtin.template', 'resources.yaml.j2') | from_yaml_all | list }}"
        wait: true
        wait_timeout: 120

    - name: Wait for the new build to be served
      ansible.builtin.uri:
        url: http://docker:8080/
        status_code: 200
        return_content: true
        timeout: 2
      register: web_response
      until:
        - web_response.status | default(0) == 200
        - "('Jenkins build ' ~ release_id) in (web_response.content | default(''))"
      retries: 30
      delay: 2
```

## 5. Jenkins에서 빌드와 Kubernetes 배포 연결

`http://127.0.0.1:18087`에서 [Jenkins 초기 설정](01_devops_ci_cd_and_jenkins_fundamentals.md#4-docker에서-jenkins-시작하기)을 진행한다. **New Item**에서 `kind-deploy`라는 **Pipeline**을 만들고 **Pipeline script**에 다음 내용을 저장한다. 빌드 번호를 이미지 태그에 포함해 배포할 버전을 구분한다. [Declarative Pipeline Syntax](https://www.jenkins.io/doc/book/pipeline/syntax/)

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
                sh 'cp -R /lab/. . && ansible-playbook -i localhost, --syntax-check deploy.yml'
            }
        }
        stage('Build Image') {
            steps {
                sh 'docker build --build-arg RELEASE="$BUILD_NUMBER" -t "jenkins-lab-web:$BUILD_NUMBER" site'
            }
        }
        stage('Load Image into kind') {
            steps {
                sh 'kind load docker-image "jenkins-lab-web:$BUILD_NUMBER" --name jenkins-lab'
            }
        }
        stage('Deploy and Verify') {
            steps {
                sh '''
                    ansible-playbook -i localhost, deploy.yml \
                        -e "image_ref=jenkins-lab-web:$BUILD_NUMBER release_id=$BUILD_NUMBER"
                '''
            }
        }
    }
}
```

**Build Now** 실행 후 `Finished: SUCCESS`를 확인한다. `curl -fsS http://127.0.0.1:18088/`의 응답이 현재 빌드 번호와 일치하는지 보고, `lab_kubectl rollout status deployment/jenkins-lab-web`로 롤아웃을 확인한다. 작업을 한 번 더 실행하면 새 이미지 태그와 응답 문구를 비교할 수 있다.

Git 변경을 시작점으로 사용하려면 저장소 루트에 `Jenkinsfile`과 `lab/`을 커밋하고 Item을 **Pipeline script from SCM**으로 설정한다. `options`에 `skipDefaultCheckout()`을 추가하고, Prepare 단계에서는 `deleteDir()` 다음에 `checkout scm`을 실행한다. 준비 명령의 복사 경로를 `cp -R lab/. .`로 바꾸면 체크아웃한 코드에서 매니페스트와 이미지를 준비한다. 변경 감지 일정은 [SCM 체크아웃과 Poll SCM](02_jenkins_ci_cd_with_git_maven_tomcat_and_docker.md) 방식으로 연결한다.

실습을 종료할 때는 `docker compose exec -T docker-engine kind delete cluster --name jenkins-lab`으로 실습 클러스터를 지운 뒤 `docker compose down`을 실행한다.
