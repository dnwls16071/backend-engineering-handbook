# Monitoring Kafka with Confluent Control Center

Confluent Control Center로 로컬 클러스터의 토픽과 소비자 그룹을 조회하고, 생산을 계속하는 동안 소비가 멈추면 Lag가 어떻게 변하는지 CLI 수치와 대조한다. 이 실습은 공식 Quick Start의 **Confluent Platform 8.2.0**(Kafka 4.2 계열)과 **Control Center 2.5.0**을 사용한다. Platform과 Control Center는 별도 버전 체계를 사용하므로 다른 릴리스를 선택할 때는 호환표를 확인한다. Confluent Platform 8.0부터는 레거시 Control Center를 대체한 버전이 제공된다. [Confluent · Quick Start](https://docs.confluent.io/control-center/current/quickstart.html) · [Confluent · 버전 호환성](https://docs.confluent.io/platform/current/installation/versions-interoperability.html)

## 1. 로컬에서 Control Center 시작하기

별도 실습 디렉터리에서 공식 Compose 예제를 가져온다. Compose 스택에는 Confluent Server, Control Center, Prometheus와 Alertmanager가 포함된다. 다음 명령들은 `cp-control-center-lab/cp-all-in-one` 디렉터리에서 실행한다. [Confluent · Quick Start](https://docs.confluent.io/control-center/current/quickstart.html) · [Confluent · 실습용 Compose](https://github.com/confluentinc/cp-all-in-one/blob/8.2.0-post/cp-all-in-one/docker-compose.yml)

```bash
git clone --branch 8.2.0-post --single-branch \
  https://github.com/confluentinc/cp-all-in-one.git cp-control-center-lab
cd cp-control-center-lab/cp-all-in-one
docker compose up -d
docker compose ps
```

브라우저에서 [http://localhost:9021](http://localhost:9021)을 연다. 지표는 수집·집계 후 나타나므로 몇 분이 걸릴 수 있다. 클러스터가 표시되지 않으면 `docker compose logs --tail 80 broker control-center prometheus`로 각 서비스의 시작 상태를 확인한다. 컨테이너 내 브로커 주소는 `broker:29092`, 호스트에서 접근하는 주소는 `localhost:9092`다. [Confluent · 시작 확인](https://docs.confluent.io/control-center/current/quickstart.html#verify-control-center-is-running) · [Confluent · 문제 해결](https://docs.confluent.io/control-center/current/installation/troubleshooting.html)

## 2. 토픽과 메시지 조회

클러스터를 선택하고 **Topics → Add a Topic**에서 `orders.control-center.v1`을 만든다. 파티션 수와 복제 계수를 각각 1로 지정한다. 아래 CLI로 레코드 두 건을 발행하고, 토픽 상세에서 파티션 수, 리더와 복제본 배치, 오프셋을 확인한다. 메시지 브라우저에서 파티션 0을 선택하면 발행한 레코드가 보인다. [Confluent · 토픽 생성](https://docs.confluent.io/control-center/current/topics/create.html) · [Confluent · 메시지 보기](https://docs.confluent.io/control-center/current/topics/messages.html)

```bash
ccli() {
  local tool="$1"
  shift
  docker compose exec -T broker "$tool" --bootstrap-server broker:29092 "$@"
}

ccli kafka-topics --list
ccli kafka-topics --create --if-not-exists --topic orders.control-center.v1 \
  --partitions 1 --replication-factor 1
printf '%s\n' 'order-1-created' 'order-2-created' |
  ccli kafka-console-producer --topic orders.control-center.v1
```

## 3. 소비자 그룹과 Lag 확인

두 건을 읽고 종료하는 소비자로 `control-center-lab-v1` 그룹의 커밋을 만든다. `kafka-consumer-groups --describe`에서 `CURRENT-OFFSET`이 2인지 확인한 뒤 동일 토픽에 두 건을 추가로 발행한다. 소비를 다시 시작하기 전에는 `LOG-END-OFFSET`이 4이고 Lag는 2다. 아래 기대값은 새 토픽과 새 그룹에서 실행한 경우다. [03번 CLI 오프셋 조회](03_managing_kafka_topics_records_and_consumer_groups_with_the_cli.md#4-소비자-그룹과-오프셋-조회) · [Confluent · Consumer Lag](https://docs.confluent.io/control-center/current/clients/consumers.html#monitor-consumer-lag)

```bash
ccli kafka-console-consumer --topic orders.control-center.v1 --group control-center-lab-v1 \
  --from-beginning --max-messages 2 --timeout-ms 15000 \
  --command-property enable.auto.commit=true
ccli kafka-consumer-groups --describe --group control-center-lab-v1

printf '%s\n' 'order-3-created' 'order-4-created' |
  ccli kafka-console-producer --topic orders.control-center.v1
ccli kafka-consumer-groups --describe --group control-center-lab-v1
```

**Clients → Consumer Lag**에서 그룹 `control-center-lab-v1`을 선택하고 파티션 0의 오프셋과 Lag를 확인한다. 토픽 상세의 **Consumer lag**에서도 이 토픽을 읽는 그룹을 볼 수 있다. 이어서 위 소비 명령과 그룹 조회를 반복한다. 저장된 오프셋 2부터 다시 소비해 커밋이 4까지 올라가면 Lag는 0이다. CLI와 화면의 조회 시각이 다르면 화면에 새 수치가 반영된 뒤 비교한다. Lag는 끝 오프셋과 그룹의 커밋 오프셋 간 차이이므로 수치가 얼마나 오래 지속되는지는 시간 추세로 확인한다. [Confluent · Consumer Lag](https://docs.confluent.io/control-center/current/clients/consumers.html#monitor-consumer-lag) · [Confluent · 토픽 조회](https://docs.confluent.io/control-center/current/topics/overview.html)

## 4. Apache Kafka 실습으로 돌아가기

Confluent Compose 디렉터리에서 서비스를 중지한다.

```bash
docker compose stop
```

이후 [01번 Apache Kafka Compose](01_apache_kafka_cluster_and_log_fundamentals.md#6-docker에서-레코드와-복제-상태-확인하기)를 저장한 **원래 디렉터리**에서 아래 명령을 실행한다. 두 스택은 별개 클러스터이므로 각 실습의 토픽과 소비자 그룹은 생성한 클러스터에서 조회한다. Apache Kafka 실습 쉘에서는 `/opt/kafka/bin/`의 `.sh` 도구와 `kafka:29092`를 사용하고, 호스트에서는 `localhost:19092`로 접속한다.

```bash
docker compose up -d --wait
docker compose exec -T kafka /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server kafka:29092 --list
```
