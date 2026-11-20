# Understanding Kafka Consumer Polling and Fetching

Kafka 4.3.2 Java 컨슈머에서 `poll(Duration)`은 그룹 할당과 읽기 위치를 갱신하고, 가져온 데이터를 애플리케이션에 넘긴다. `group.protocol=classic`을 사용한 [05번의 Java 컨슈머](05_developing_reliable_kafka_consumer_applications.md)를 기준으로 호출 경로를 따라간다.

## 1. `poll()`에서 역직렬화까지

1. `KafkaConsumer.poll()`은 classic 구현인 `ClassicKafkaConsumer.poll()`로 위임한다. `updateAssignmentMetadataIfNeeded()`에서 그룹 참여와 파티션 할당을 진행하고, 초기 읽기 위치가 필요한 파티션을 갱신한다.
2. `pollForFetches()`는 `Fetcher.collectFetch()`를 호출해 버퍼에 남은 응답을 먼저 확인한다. 읽을 데이터가 없으면 `sendFetches()`로 요청을 준비하고 네트워크 응답을 기다린다. Fetch 요청에는 파티션별 읽기 오프셋이 들어가며, 기본적으로 각 파티션의 리더 브로커에 보낸다.
3. `FetchCollector`가 완료된 응답에서 반환할 레코드를 모은다. `CompletedFetch.parseRecord()`가 설정된 키와 값의 `Deserializer`를 호출해 `ConsumerRecord`를 만들고, `poll()`은 이 레코드들을 `ConsumerRecords`로 반환한다. 반환 과정에서 컨슈머의 읽기 위치가 전진한다. 역직렬화가 실패하면 `RecordDeserializationException`에서 파티션과 오프셋을 확인할 수 있다.

[Apache Kafka 4.3.2 · ClassicKafkaConsumer](https://github.com/apache/kafka/blob/4.3.2/clients/src/main/java/org/apache/kafka/clients/consumer/internals/ClassicKafkaConsumer.java) · [FetchCollector](https://github.com/apache/kafka/blob/4.3.2/clients/src/main/java/org/apache/kafka/clients/consumer/internals/FetchCollector.java) · [CompletedFetch](https://github.com/apache/kafka/blob/4.3.2/clients/src/main/java/org/apache/kafka/clients/consumer/internals/CompletedFetch.java) · [RecordDeserializationException](https://kafka.apache.org/43/javadoc/org/apache/kafka/common/errors/RecordDeserializationException.html)

## 2. Fetch 응답 크기와 `poll()` 반환량

| 설정 | 적용 범위 |
| --- | --- |
| `fetch.min.bytes` | 브로커가 Fetch에 응답하기 전에 확보하려는 최소 바이트 수다. 값을 올리면 응답에 더 많은 데이터를 담을 수 있고, 유입이 적을 때는 대기 시간이 길어질 수 있다. |
| `fetch.max.wait.ms` | 로컬 로그에서 최소 바이트 수를 채우기 위해 브로커가 기다리는 최대 시간이다. |
| `fetch.max.bytes` | 브로커 한 대의 Fetch 응답에서 가져올 전체 데이터 크기를 제한한다. |
| `max.partition.fetch.bytes` | Fetch 응답의 파티션별 데이터 크기를 제한한다. |
| `max.poll.records` | `poll()` 한 번에 애플리케이션으로 반환하는 최대 레코드 수다. Fetch 요청의 크기는 앞의 바이트 설정이 제어한다. |

Fetch 응답에 읽을 수 있는 레코드가 250건 들어왔고 `max.poll.records=100`이면, 버퍼에 남은 데이터가 다음 `poll()`들에 최대 100건씩 전달된다. 한 Fetch의 첫 번째 비어 있지 않은 파티션에 있는 첫 레코드 배치는 진행을 보장하기 위해 `fetch.max.bytes` 또는 `max.partition.fetch.bytes`를 넘더라도 반환될 수 있다. `poll(Duration)`의 인자는 해당 호출이 데이터를 기다리는 시간에 적용된다. 그룹의 `max.poll.interval.ms`는 애플리케이션이 다시 `poll()`을 호출하기까지 허용되는 간격이다. [Apache Kafka · Consumer Configs](https://kafka.apache.org/43/configuration/consumer-configs/) · [Apache Kafka · KafkaConsumer](https://kafka.apache.org/43/javadoc/org/apache/kafka/clients/consumer/KafkaConsumer.html)

## 3. 디버거에서 확인할 위치

IDE에 `kafka-clients` 4.3.2 소스를 연결하고 로컬 테스트 토픽과 전용 그룹으로 실행한다. 첫 `poll()`과 이후 `poll()`에서 `ClassicKafkaConsumer.updateAssignmentMetadataIfNeeded()`, `pollForFetches()`, `FetchCollector.collectFetch()`, `CompletedFetch.parseRecord()` 순서로 살펴본다. `poll()`을 적어도 두 번 호출하고 `max.poll.records=1`로 설정하면 응답 하나에서 여러 레코드를 나눠 반환하는 경로를 확인하기 쉽다. 브레이크포인트를 오래 유지하면 그룹 타임아웃이 발생할 수 있으므로 멈춤 범위를 소비 스레드로 좁히거나 로그포인트로 파티션과 오프셋을 남긴다. [Apache Kafka 4.3.2 · ClassicKafkaConsumer](https://github.com/apache/kafka/blob/4.3.2/clients/src/main/java/org/apache/kafka/clients/consumer/internals/ClassicKafkaConsumer.java) · [Apache Kafka · Consumer Configs](https://kafka.apache.org/43/configuration/consumer-configs/)

## 4. `wakeup()`과 종료

`KafkaConsumer` 인스턴스는 소비 스레드가 소유한다. 종료를 요청하는 다른 스레드는 종료 플래그를 먼저 설정하고 스레드 안전한 `wakeup()`을 호출한다. 대기 중인 `poll()`이나 `commitSync()`가 `WakeupException`으로 중단될 수 있다. 중단할 호출이 없다면 예외를 지원하는 다음 호출에서 예외가 발생한다. 소비 스레드는 종료 요청으로 발생한 예외를 처리하고 `finally`에서 `close(CloseOptions.timeout(...))`를 호출한다. `close()`의 대기 시간은 종료 옵션으로 정한다. [Apache Kafka · KafkaConsumer](https://kafka.apache.org/43/javadoc/org/apache/kafka/clients/consumer/KafkaConsumer.html) · [Apache Kafka · CloseOptions](https://kafka.apache.org/43/javadoc/org/apache/kafka/clients/consumer/CloseOptions.html)

## 5. 커밋 위치와 `auto.offset.reset`

`position()`은 현재 컨슈머가 다음에 읽을 오프셋이다. 그룹 코디네이터는 `OffsetCommit`을 받아 `__consumer_offsets` 내부 토픽에 그룹별·토픽 파티션별 커밋을 기록한다. 이 토픽에는 로그 컴팩션이 적용되며, 코디네이터는 커밋 조회에 캐시를 사용한다. 새로 할당된 파티션에 유효한 커밋이 있으면 해당 위치에서 읽기를 시작한다. [Apache Kafka · Distribution](https://kafka.apache.org/43/implementation/distribution/) · [Apache Kafka · KafkaConsumer](https://kafka.apache.org/43/javadoc/org/apache/kafka/clients/consumer/KafkaConsumer.html)

그룹에 커밋이 없거나 보관 기간 경과 등으로 읽기 위치가 로그 범위를 벗어나면 `auto.offset.reset`이 적용된다. `earliest`는 현재 보관 중인 첫 위치, `latest`는 로그 끝을 선택한다. `by_duration:PT1H`는 현재 시각에서 한 시간 전을 기준으로 위치를 찾고, `none`은 예외를 발생시킨다. `earliest`로 설정한 그룹도 유효한 커밋이 있으면 그 위치에서 재개한다. [Apache Kafka · Consumer Configs](https://kafka.apache.org/43/configuration/consumer-configs/)
