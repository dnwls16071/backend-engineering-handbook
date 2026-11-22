# Configuring Kafka in Spring Boot

Spring Boot가 구성하는 레코드 리스너에 키·값 역직렬화, 소비 그룹, 오프셋 커밋 시점을 명시한다. 이 실습의 값은 JSON 문자열이다. [Spring Boot 3.5 · Application Properties](https://docs.spring.io/spring-boot/3.5/appendix/application-properties/index.html) · [Spring Kafka 3.3 · Listener Containers](https://docs.spring.io/spring-kafka/reference/3.3/kafka/receiving-messages/message-listener-container.html) · [Debezium 3.6 · Outbox Event Router](https://raw.githubusercontent.com/debezium/debezium/v3.6.0.Final/documentation/modules/ROOT/pages/transformations/outbox-event-router.adoc)

## 1. Kafka와 Activity DB의 설정을 분리한다

아래를 src/main/resources/application.yml에 저장한다. 표시된 주소는 호스트에서 앱을 실행할 때 쓰는 로컬 실습 기본값이다. 기존 커밋 오프셋이 없는 그룹에만 earliest가 적용된다. 비밀번호는 실습 환경 변수로 전달한다. [Spring Boot 3.5 · Application Properties](https://docs.spring.io/spring-boot/3.5/appendix/application-properties/index.html) · [Spring Kafka 3.3 · Listener Containers](https://docs.spring.io/spring-kafka/reference/3.3/kafka/receiving-messages/message-listener-container.html) · [Apache Kafka 4.3 · Consumer Configs](https://kafka.apache.org/43/configuration/consumer-configs/) · [Docker Compose · Networking](https://docs.docker.com/compose/how-tos/networking/)

```yaml
spring:
  main:
    web-application-type: none
  kafka:
    bootstrap-servers: ${KAFKA_BOOTSTRAP:127.0.0.1:19092}
    consumer:
      group-id: order-workflow
      auto-offset-reset: earliest
      enable-auto-commit: false
      key-deserializer: org.apache.kafka.common.serialization.StringDeserializer
      value-deserializer: org.apache.kafka.common.serialization.StringDeserializer
    listener:
      ack-mode: record
  datasource:
    url: ${WORKFLOW_DB_URL:jdbc:mysql://127.0.0.1:13306/workflow_lab}
    username: ${WORKFLOW_DB_USER:workflow_app}
    password: ${WORKFLOW_DB_PASSWORD}
```

## 2. 정상 반환과 실패를 오프셋 정책에 연결한다

RECORD 모드에서는 레코드 리스너가 정상 처리한 뒤 컨테이너가 해당 오프셋을 커밋한다. 실패 레코드는 오류 처리기의 복구 정책을 따른다. 로컬 예제에서는 실패 시 컨테이너를 중단해 원인을 확인하고, 운영에서는 재시도 및 실패 레코드 보존 정책을 정한다. [Spring Kafka 3.3 · Listener Containers](https://docs.spring.io/spring-kafka/reference/3.3/kafka/receiving-messages/message-listener-container.html) · [Spring Kafka 3.3 · Handling Exceptions](https://docs.spring.io/spring-kafka/reference/3.3/kafka/annotation-error-handling.html)
