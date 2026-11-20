# Running a Lightweight Local Kafka Environment

로컬에서는 Kafka 브로커와 KRaft 컨트롤러를 한 프로세스로 실행하고, 애플리케이션이 사용하는 토픽과 의존성만 추가한다. 01번 실습의 `compose.yaml`은 Apache Kafka 4.3.2 공식 JVM 이미지 `apache/kafka:4.3.2`를 사용한다. Apache의 GraalVM 기반 `apache/kafka-native:4.3.2`는 로컬 개발과 테스트용 실험 이미지다. [01번 Docker Kafka 실습](01_apache_kafka_cluster_and_log_fundamentals.md#6-docker에서-레코드와-복제-상태-확인하기) · [Apache Kafka · Docker](https://kafka.apache.org/43/getting-started/docker/)

## 1. 애플리케이션의 접속 주소

| 애플리케이션 실행 위치 | `bootstrap.servers` |
| --- | --- |
| 호스트에서 실행하는 IDE, 애플리케이션, CLI | `localhost:19092` |
| 같은 Compose 네트워크에서 실행하는 애플리케이션·UI | `kafka:29092` |

브로커는 `advertised.listeners`로 각 클라이언트에 메타데이터의 접속 주소를 알려준다. Spring Boot 애플리케이션은 `spring.kafka.bootstrap-servers`를 환경 변수 `SPRING_KAFKA_BOOTSTRAPSERVERS`로 주입할 수 있다. 호스트에서 실행할 때는 다음 값을 지정하고, Compose 서비스에서는 같은 변수에 `kafka:29092`를 넣는다. 소비자 그룹 ID도 프로필이나 실행 환경별로 지정하면 어떤 그룹의 오프셋을 조회할지 명확해진다. [Apache Kafka · Listener Configuration](https://kafka.apache.org/43/security/listener-configuration/) · [Spring Boot · Kafka](https://docs.spring.io/spring-boot/reference/messaging/kafka.html) · [Spring Boot · Environment Variable Binding](https://docs.spring.io/spring-boot/reference/features/external-config.html#features.external-config.typesafe-configuration-properties.relaxed-binding.environment-variables)

```bash
export SPRING_KAFKA_BOOTSTRAPSERVERS=localhost:19092
export SPRING_KAFKA_CONSUMER_GROUPID=local-orders
```

애플리케이션에서 `application.properties`의 플레이스홀더로 접속 주소를 받는 방식은 11번의 Spring Boot 설정 예제를 참고한다. [11번 Spring Boot Kafka 설정](11_configuring_spring_boot_for_kafka.md)

## 2. 메시지 왕복 확인

01번의 `compose.yaml`이 있는 디렉터리에서 실행한다. `up --wait`가 브로커 상태를 확인한 뒤, 실행마다 별도 토픽을 생성하고 키와 값이 들어간 레코드 한 건을 왕복시킨다. [Docker · Compose Up](https://docs.docker.com/reference/cli/docker/compose/up/) · [Apache Kafka · Quickstart](https://kafka.apache.org/43/getting-started/quickstart/)

```bash
(
  set -euo pipefail
  docker compose up -d --wait kafka
  kafka_cli() {
    tool=$1
    shift
    docker compose exec -T kafka "/opt/kafka/bin/$tool" --bootstrap-server kafka:29092 "$@"
  }

  topic="local-smoke-$(date +%s)-$$"
  kafka_cli kafka-topics.sh --create --topic "$topic" --partitions 1 --replication-factor 1
  printf 'smoke-key:ready\n' |
    kafka_cli kafka-console-producer.sh --topic "$topic" \
      --reader-property parse.key=true --reader-property key.separator=:

  record=$(kafka_cli kafka-console-consumer.sh --topic "$topic" \
    --from-beginning --max-messages 1 --timeout-ms 10000 --formatter-property print.key=true)
  test "$record" = $'smoke-key\tready'
  printf 'Smoke test passed for %s\n' "$topic"
)
```

Kafka 4.3.2 단일 브로커에서 키가 `smoke-key`이고 값이 `ready`인 레코드 한 건을 읽었다. 이 테스트는 컨테이너 네트워크를 사용한다. 호스트 경로도 확인하려면 호스트에 Kafka CLI를 설치한 상태에서 `bin/kafka-topics.sh --bootstrap-server localhost:19092 --list`를 실행한다. 애플리케이션에서만 실패하면 실행 위치에 맞는 환경 변수와 직렬화기 설정을 확인한다. [Apache Kafka · Quickstart](https://kafka.apache.org/43/getting-started/quickstart/)

## 3. UI와 CLI로 상태 확인

토픽의 키·값·오프셋을 화면에서 확인하려면 같은 디렉터리에 `compose.ui.yaml`을 추가하고 `docker compose -f compose.yaml -f compose.ui.yaml up -d kafka-ui`를 실행한다. Kafbat UI는 브라우저에서 `http://localhost:18080`으로 열고, Kafka에는 Compose 내부 주소로 연결한다. [Kafbat UI · Container Package](https://github.com/kafbat/kafka-ui/pkgs/container/kafka-ui) · [Kafbat UI · Configuration](https://ui.docs.kafbat.io/configuration/misc-configuration-properties)

```yaml
services:
  kafka-ui:
    image: ghcr.io/kafbat/kafka-ui:v1.5.1
    depends_on:
      kafka:
        condition: service_healthy
    ports:
      - "127.0.0.1:18080:8080"
    environment:
      KAFKA_CLUSTERS_0_NAME: local
      KAFKA_CLUSTERS_0_BOOTSTRAPSERVERS: kafka:29092
```

- **토픽**에서 파티션, 보관 설정, 레코드의 키와 값을 확인한다. CLI에서는 `kafka-topics.sh`로 토픽을 생성하고 `kafka-configs.sh`로 설정을 변경한다. [Kafbat UI · Features](https://ui.docs.kafbat.io/overview/features) · [Kafka CLI 실습](03_managing_kafka_topics_records_and_consumer_groups_with_the_cli.md)
- **소비자 그룹**에서 현재 오프셋, 로그 끝 오프셋, 파티션별 lag를 확인한다. CLI에서는 `kafka-consumer-groups.sh --bootstrap-server kafka:29092 --describe --group local-orders`로 같은 흐름을 확인할 수 있다. [Kafbat UI · Consumer Groups](https://ui.docs.kafbat.io/overview/features) · [Apache Kafka · Consumer Group Operations](https://kafka.apache.org/43/operations/basic-kafka-operations/)
- **브로커** 연결이 실패하면 `docker compose ps`와 `docker compose logs --tail=100 kafka`를 확인한다. 초기 연결 뒤 메타데이터 요청이 실패하면 클라이언트 위치에서 광고된 브로커 주소로 접근할 수 있는지 점검한다. [Apache Kafka · Listener Configuration](https://kafka.apache.org/43/security/listener-configuration/)
