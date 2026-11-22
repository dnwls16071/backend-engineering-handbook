# Building a Lightweight Docker Environment

이 예는 빌드 도구를 담은 단계에서 실행 JAR를 만들고, JRE만 필요한 별도 런타임 이미지에 복사한다. MySQL·Kafka·Kafka Connect는 Compose 서비스로 배치한다. [Docker · Multi-stage Builds](https://docs.docker.com/build/building/multi-stage/) · [Docker · Build Best Practices](https://docs.docker.com/build/building/best-practices/) · [Docker Compose · Networking](https://docs.docker.com/compose/how-tos/networking/)

## 1. 빌드와 런타임 의존성을 분리한다

[Kotlin 빌드 문서](16_configuring_a_kotlin_spring_boot_build.md)의 Gradle Wrapper와 앱을 준비한 뒤 아래 Dockerfile을 사용한다. 이 실습의 bootJar 출력 이름은 workflow-app.jar다. 운영 배포에서는 베이스 이미지의 검증된 다이제스트를 기록한다. [Docker · Multi-stage Builds](https://docs.docker.com/build/building/multi-stage/) · [Docker · Build Best Practices](https://docs.docker.com/build/building/best-practices/) · [Spring Boot 3.5 · System Requirements](https://docs.spring.io/spring-boot/3.5/system-requirements.html)

```dockerfile
FROM eclipse-temurin:21-jdk AS build
WORKDIR /src
COPY . .
RUN ./gradlew --no-daemon bootJar

FROM eclipse-temurin:21-jre
WORKDIR /app
COPY --from=build --chown=10001:10001 /src/build/libs/workflow-app.jar /app/app.jar
USER 10001:10001
ENTRYPOINT ["java", "-jar", "/app/app.jar"]
```

## 2. 이름·포트와 준비 상태를 확인한다

Compose 컨테이너끼리는 서비스 DNS와 내부 포트를 쓴다. 호스트에서 실행하는 앱은 게시된 호스트 포트를 사용한다. Compose의 시작 순서만으로 연결 가능 여부를 판단하기 어려우므로 DB와 브로커에 healthcheck를 두고 앱에서 일시 연결 실패를 처리한다. .dockerignore로 .git, build, .gradle 및 로컬 환경 파일을 제외한다. [Docker Compose · Networking](https://docs.docker.com/compose/how-tos/networking/) · [Docker Compose · Startup Order](https://docs.docker.com/compose/how-tos/startup-order/) · [Docker · Build Best Practices](https://docs.docker.com/build/building/best-practices/)
