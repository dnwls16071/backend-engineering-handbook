# Controlling Kafka Consumer Offsets and Replay

Kafka에 커밋하는 오프셋은 같은 그룹이 재시작하거나 파티션을 넘겨받을 때 다음에 읽을 위치다. Kafka 4.3.2 Java 컨슈머에서 처리 완료, 커밋, 재시작 순서에 따라 어떤 레코드가 다시 전달되는지 살펴본다.

## 1. 자동 커밋과 장애 시점

`enable.auto.commit=true`이면 컨슈머가 `auto.commit.interval.ms`에 따라 읽기 위치를 주기적으로 커밋한다. 컨슈머가 아는 위치는 `poll()`이 애플리케이션에 전달한 레코드를 기준으로 움직인다. `poll()`의 결과를 워커에게 넘기고 바로 다음 `poll()`을 호출하면, 워커의 처리가 끝나기 전에 읽기 위치가 저장될 수 있다. 자동 커밋에서 적어도 한 번 처리하는 흐름을 유지하려면 배치 처리를 다음 `poll()`이나 정상 `close()` 전에 모두 마친다. [Apache Kafka · Consumer Configs](https://kafka.apache.org/43/configuration/consumer-configs/) · [Apache Kafka · KafkaConsumer](https://kafka.apache.org/43/javadoc/org/apache/kafka/clients/consumer/KafkaConsumer.html)

직전 커밋이 40인 파티션에서 `poll()`이 40과 41을 반환한 상황을 생각해 보자. 두 건을 처리하고 42가 저장되기 전에 프로세스가 중단되면 40부터 다시 읽는다. 42가 저장된 상태에서 41의 처리가 끝나기 전에 장애가 나면 그룹은 42부터 재개하므로 41의 처리가 누락될 수 있다. 외부 DB에 반영한 뒤 커밋하는 흐름은 재전달에 대비해 이벤트 ID로 중복 처리를 방지할 수 있다. [Apache Kafka · KafkaConsumer](https://kafka.apache.org/43/javadoc/org/apache/kafka/clients/consumer/KafkaConsumer.html)

## 2. 수동 커밋의 범위와 순서

`enable.auto.commit=false`로 설정하고 업무 처리를 끝낸 위치를 파티션별로 커밋한다. 배치를 모두 처리했다면 `records.nextOffsets()`를 사용한다. 일부만 완료했다면 아직 처리하지 않은 첫 레코드의 오프셋을 기준으로 커밋한다. 워커가 40과 42를 끝냈어도 41이 남아 있다면 커밋할 다음 위치는 41이다. 직접 커밋 값을 만들 때는 가능하면 `OffsetAndMetadata`에 리더 epoch도 전달한다. [Apache Kafka · ConsumerRecords](https://kafka.apache.org/43/javadoc/org/apache/kafka/clients/consumer/ConsumerRecords.html) · [Apache Kafka · KafkaConsumer](https://kafka.apache.org/43/javadoc/org/apache/kafka/clients/consumer/KafkaConsumer.html)

| 호출 | 동작과 실패 처리 |
| --- | --- |
| `commitSync(offsets)` | 성공, 재시도 불가능한 오류 또는 타임아웃이 발생할 때까지 소비 스레드에서 대기한다. 타임아웃은 `Duration`으로 지정하거나 `default.api.timeout.ms`를 사용한다. 리밸런싱이 진행 중이면 `poll()`로 할당을 갱신한 후 아직 맡은 파티션의 완료 위치를 확인한다. |
| `commitAsync(offsets, callback)` | 응답을 기다리지 않고 반환한다. 콜백에 전달된 예외를 기록하고, 최신 처리 완료 위치를 기준으로 후속 커밋을 판단한다. 콜백을 생략하면 비동기 실패를 애플리케이션에서 받지 못한다. |

여러 `commitAsync()` 요청과 콜백은 호출 순서를 따른다. 예를 들어 커밋 42가 실패한 뒤 50이 이미 제출된 경우, 실패 콜백에서 42를 다시 제출하면 새 요청이 뒤에 붙어 저장 위치가 42로 되돌아갈 수 있다. 앞선 비동기 커밋과 후속 동기 커밋을 함께 쓸 때, 4.3.2 Javadoc에서 `commitSync()`가 반환되기 전에 앞선 비동기 콜백까지 실행된다는 보장은 `consumer` 프로토콜에 명시되어 있다. [Apache Kafka · KafkaConsumer](https://kafka.apache.org/43/javadoc/org/apache/kafka/clients/consumer/KafkaConsumer.html)

[05번의 수동 커밋과 재시작 예제](05_developing_reliable_kafka_consumer_applications.md#4-docker에서-수동-커밋과-재시작-확인하기)는 배치 전체를 처리한 뒤 `commitSync(records.nextOffsets())`를 호출한다. 마지막 커밋과 재시작 직후의 첫 오프셋을 비교하면 커밋 경계를 확인할 수 있다.

## 3. `assign()`과 `seek()`로 특정 범위 다시 읽기

테스트 브로커에서 재처리할 토픽·파티션과 오프셋 범위 `[from, to)`를 정한다. `assign(List.of(partition))`으로 파티션을 직접 선택하고 `seek(partition, from)`으로 읽기 위치를 옮긴다. `poll()`을 반복하며 해당 범위에 속한 레코드만 처리한다. 자동 커밋을 끄고 커밋 API를 호출하지 않는 조회 작업은 `group.id` 없이 실행할 수 있다. 재처리 진행을 Kafka에 커밋해야 한다면 재처리 전용 `group.id`를 지정한다. [Apache Kafka · KafkaConsumer](https://kafka.apache.org/43/javadoc/org/apache/kafka/clients/consumer/KafkaConsumer.html)

예를 들어 테스트 토픽의 `orders.replay.v1-0`에서 오프셋 40 이상 50 미만을 다시 읽으려면 다음 순서로 진행한다.

1. `new TopicPartition("orders.replay.v1", 0)`을 할당하고, `beginningOffsets()`와 `endOffsets()`로 범위를 확인한다. `auto.offset.reset=none`을 설정하면 보관 정책으로 시작 위치가 사라진 경우 오류로 확인할 수 있다.
2. `seek(partition, 40)` 이후 `poll()`로 반환된 레코드 중 오프셋이 40 이상 50 미만인 레코드를 처리한다. 로그 컴팩션으로 오프셋에 빈 구간이 생겨도 종료 조건은 다음 읽기 위치로 판단한다.
3. 배치 처리를 끝낸 뒤 다음 읽기 위치 `position(partition)`이 50 이상이면 종료한다. 빈 `poll()`은 시간 내에 반환할 데이터가 없었다는 뜻이므로 계속 확인하되, 작업 전체에 기한을 두고 초과하면 미완료로 기록한다.

[Apache Kafka · KafkaConsumer](https://kafka.apache.org/43/javadoc/org/apache/kafka/clients/consumer/KafkaConsumer.html) · [Apache Kafka · Consumer Configs](https://kafka.apache.org/43/configuration/consumer-configs/)
