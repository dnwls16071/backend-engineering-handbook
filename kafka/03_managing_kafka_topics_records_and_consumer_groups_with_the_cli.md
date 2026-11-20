# Managing Kafka Topics, Records, and Consumer Groups with the CLI

Kafka 4.3.2 CLI로 토픽을 만들고 설정을 확인한 뒤, 레코드를 발행·소비하고 소비자 그룹의 오프셋을 조회한다. 브로커와 CLI는 모두 [01번 Docker Compose 환경](01_apache_kafka_cluster_and_log_fundamentals.md#6-docker에서-레코드와-복제-상태-확인하기)을 사용한다. [Apache Kafka · Quick Start](https://kafka.apache.org/43/getting-started/quickstart/)

## 1. 로컬 브로커와 CLI 연결

`compose.yaml`이 있는 디렉터리에서 아래 명령을 실행한다. `kcli`는 실습 브로커 주소를 각 도구에 전달하는 셸 함수다. 이어지는 명령은 같은 셸에서 실행한다. 컨테이너 안의 도구는 `kafka:29092`로 접속하고, 호스트에서 실행하는 클라이언트는 `localhost:19092`를 사용한다.

```bash
docker compose up -d --wait

kcli() {
  tool="$1"
  shift
  docker compose exec -T kafka "/opt/kafka/bin/$tool" \
    --bootstrap-server kafka:29092 "$@"
}

kcli kafka-topics.sh --list
```

## 2. 토픽 생성과 설정 변경

`kafka-topics.sh --create`로 파티션 수, 복제 계수, 토픽 설정을 명시한다. `--describe`에서 파티션별 리더, 복제본, ISR과 설정을 볼 수 있다. [Apache Kafka · Basic Kafka Operations](https://kafka.apache.org/43/operations/basic-kafka-operations/) · [Topic Configs](https://kafka.apache.org/43/configuration/topic-configs/)

```bash
kcli kafka-topics.sh --create --topic orders.cli.v1 \
  --partitions 2 --replication-factor 1 --config cleanup.policy=delete

kcli kafka-topics.sh --describe --topic orders.cli.v1

kcli kafka-configs.sh --entity-type topics --entity-name orders.cli.v1 \
  --alter --add-config retention.ms=3600000

kcli kafka-configs.sh --entity-type topics --entity-name orders.cli.v1 --describe

kcli kafka-configs.sh --entity-type topics --entity-name orders.cli.v1 \
  --alter --delete-config retention.ms
```

`--delete-config`는 토픽의 재정의 값을 제거해 브로커 기본값을 적용한다. 설정을 바꾸기 전에는 대상 토픽과 적용 범위를 확인한다.

토픽은 두 방식으로 만들 수 있다.

| 방식 | 만드는 시점과 설정 |
| --- | --- |
| 명시적 생성 | CLI나 Admin API로 토픽을 생성한다. 생성 시 파티션, 복제 계수, 보관 정책을 정할 수 있다. |
| 자동 생성 | 브로커의 `auto.create.topics.enable`과 클라이언트 요청이 허용하면 존재하지 않는 토픽 접근 시 기본 설정으로 생성된다. 이름 오타도 별도 토픽을 만들 수 있다. |

운영에서 토픽 정책을 일관되게 적용하려면 애플리케이션 배포에 앞서 필요한 토픽을 명시적으로 생성한다. [Apache Kafka · Broker Configs](https://kafka.apache.org/43/configuration/broker-configs/#auto.create.topics.enable) · [Consumer Configs](https://kafka.apache.org/43/configuration/consumer-configs/)

## 3. 키가 있는 레코드 발행과 소비

Producer의 `--reader-property`로 표준 입력을 키와 값으로 나눈다. Consumer의 `--formatter-property`는 읽은 레코드의 출력 항목을 지정한다. [Apache Kafka · Quick Start](https://kafka.apache.org/43/getting-started/quickstart/) · [Kafka 4.3.2 · Console Consumer Options](https://github.com/apache/kafka/blob/4.3.2/tools/src/main/java/org/apache/kafka/tools/consumer/ConsoleConsumerOptions.java)

```bash
printf '%s\n' 'order-200:created' 'order-200:paid' 'order-200:shipped' |
  kcli kafka-console-producer.sh --topic orders.cli.v1 \
    --reader-property parse.key=true --reader-property key.separator=:

kcli kafka-console-consumer.sh --topic orders.cli.v1 --group cli-check-v1 \
  --from-beginning --max-messages 3 --timeout-ms 10000 \
  --command-property enable.auto.commit=true \
  --formatter-property print.key=true \
  --formatter-property print.partition=true \
  --formatter-property print.offset=true
```

`--from-beginning`은 읽을 수 있는 커밋 오프셋이 없을 때 보관 중인 가장 이른 위치부터 읽게 한다. 이미 정상적인 커밋 오프셋이 있는 그룹은 저장된 위치를 사용한다. 이 실습은 명시한 그룹에 오프셋을 남겨 다음 단계에서 확인한다.

## 4. 소비자 그룹과 오프셋 조회

`CURRENT-OFFSET`은 그룹이 커밋한 다음 읽기 위치다. `LOG-END-OFFSET`과의 차이인 `LAG`를 보면 파티션별 적체를 관찰할 수 있다. 세 건을 오프셋 0~2에서 소비해 모두 커밋하면 해당 파티션의 다음 읽기 위치는 3이다. [Apache Kafka · Managing Consumer Groups](https://kafka.apache.org/43/operations/basic-kafka-operations/)

```bash
kcli kafka-consumer-groups.sh --list
kcli kafka-consumer-groups.sh --describe --group cli-check-v1

kcli kafka-consumer-groups.sh --reset-offsets --dry-run \
  --group cli-check-v1 --topic orders.cli.v1 --to-earliest
```

Console Consumer를 종료한 상태에서 마지막 명령으로 변경할 위치를 미리 본다. 오프셋을 실제로 옮기는 `--execute`는 소비자가 멈춘 상태에서 적용하며, 위치를 뒤로 옮기면 이미 처리한 데이터가 다시 전달될 수 있다.

Docker의 Kafka 4.3.2에서 세 레코드가 파티션 1의 오프셋 0~2에 기록됐다. 미리보기는 새 읽기 위치로 0을 제시했고, 이후 조회에서 커밋 오프셋 3과 Lag 0을 확인했다.

## 5. 다른 운영 도구와 버전 호환성

| 도구 | 확인할 값 |
| --- | --- |
| `kafka-get-offsets.sh` | 파티션별 가장 이른 오프셋이나 로그 끝 위치 |
| `kafka-log-dirs.sh` | 브로커 로그 디렉터리별 파티션 배치와 크기 |
| `kafka-broker-api-versions.sh` | 브로커가 지원하는 요청 API의 버전 범위 |
| `kafka-metadata-quorum.sh` | KRaft 메타데이터 쿼럼의 리더와 투표자 |

```bash
kcli kafka-get-offsets.sh --topic orders.cli.v1 --time -1
kcli kafka-broker-api-versions.sh
docker compose exec -T kafka /opt/kafka/bin/kafka-topics.sh --version
```

클라이언트와 브로커는 공통으로 지원하는 Kafka 요청 API 버전을 사용한다. CLI 버전을 브로커 릴리스에 맞추면 옵션 이름과 관리자 기능의 차이로 인한 혼란을 줄일 수 있다. `--version`은 CLI의 버전을, `kafka-broker-api-versions.sh`는 브로커가 지원하는 API 범위를 보여 준다. [Apache Kafka · Protocol](https://kafka.apache.org/43/design/protocol/) · [Kafka 4.3 Upgrade](https://kafka.apache.org/43/getting-started/upgrade/) · [클러스터 운영과 상태 조회](02_operating_self_managed_and_managed_kafka_clusters.md)
