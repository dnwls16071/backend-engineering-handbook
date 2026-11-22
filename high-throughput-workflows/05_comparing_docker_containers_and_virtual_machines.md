# Comparing Docker Containers and Virtual Machines

Linux 컨테이너는 독립 파일 시스템과 제한된 자원으로 실행되는 프로세스이며 Linux 커널을 공유한다. VM은 가상 하드웨어에서 자체 게스트 커널을 부팅한다. [Docker · What Is a Container?](https://docs.docker.com/get-started/docker-concepts/the-basics/what-is-a-container/) · [Docker · Desktop on Mac](https://docs.docker.com/desktop/setup/install/mac-install/)

## 1. Docker Desktop에서 어느 경계를 공유하는지 본다

macOS에서 실행한 Linux 컨테이너는 Docker Desktop이 제공하는 Linux VM 안에서 동작한다. 파일 공유, 컨테이너 포트 노출, VM에 할당한 CPU와 메모리를 실습 성능과 연결해 본다. [Docker · Desktop on Mac](https://docs.docker.com/desktop/setup/install/mac-install/) · [Docker Compose · Networking](https://docs.docker.com/compose/how-tos/networking/)

## 2. 경량 이미지를 선택하는 목적을 정한다

이미지 레이어가 작으면 전송량과 빌드 산출물이 줄 수 있다. 런타임에서 필요한 JRE, 네이티브 라이브러리, 아키텍처와 인증서가 포함되는지 검증한다. [Docker · Build Best Practices](https://docs.docker.com/build/building/best-practices/) · [Docker · Multi-stage Builds](https://docs.docker.com/build/building/multi-stage/)
