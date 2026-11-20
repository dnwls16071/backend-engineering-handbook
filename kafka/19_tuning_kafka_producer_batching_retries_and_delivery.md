# Tuning Kafka Producer Batching, Retries, and Delivery

Kafka Java 프로듀서는 같은 파티션으로 갈 레코드를 배치로 묶고, 브로커가 어느 수준까지 기록을 확인할지 설정한다. 배치 크기와 대기 시간은 처리량과 지연에 영향을 주고, 확인 수준과 재시도 설정은 장애 시 기록 결과를 좌우한다. 수치와 기본값은 Kafka 클라이언트 4.3.2를 기준으로 한다. [Kafka · Producer Configs](https://kafka.apache.org/43/configuration/producer-configs/)

## 1. 브로커의 확인 수준을 고른다

| `acks` | 프로듀서가 기다리는 확인 | 장애 시 결과 |
| --- | --- | --- |
| `0` | 브로커 응답을 기다리지 않는다. | 기록 여부를 확인할 수 없고 브로커 응답을 바탕으로 재시도할 수 없다. 성공 메타데이터의 오프셋은 `-1`이다. |
| `1` | 파티션 리더가 로컬 로그에 기록하고 응답한다. | 복제 전에 리더가 장애를 겪으면 이미 성공으로 처리한 기록을 잃을 수 있다. |
| `all` | 리더가 현재 ISR 전체의 확인을 기다린다. | `min.insync.replicas`를 충족하지 못하면 쓰기가 실패한다. Kafka 4.3의 기본값이다. |

복제 계수 3, `min.insync.replicas=2`인 토픽은 ISR이 세 개일 때 세 복제본의 확인을 기다린다. ISR이 두 개로 줄면 두 복제본으로 쓸 수 있고, 하나까지 줄면 `acks=all` 쓰기가 실패한다. [01번 · 복제와 ISR](01_apache_kafka_cluster_and_log_fundamentals.md#4-복제-isr-생산자-확인) · [Kafka · Topic Configs](https://kafka.apache.org/43/configuration/topic-configs/) · [KafkaProducer API](https://kafka.apache.org/43/javadoc/org/apache/kafka/clients/producer/KafkaProducer.html)

## 2. 파티션별 배치가 얼마나 차는지 본다

`send()`는 레코드를 직렬화하고 파티션을 고른 뒤, `RecordAccumulator`의 해당 파티션 큐에 있는 `ProducerBatch`에 레코드를 추가한다. 백그라운드 `Sender`는 전송 가능한 배치를 꺼내 목적지 브로커별 요청으로 묶는다. 한 요청에 동일 브로커가 리더인 여러 파티션의 배치가 함께 들어갈 수 있다. [Kafka 4.3.2 · RecordAccumulator 소스](https://raw.githubusercontent.com/apache/kafka/4.3.2/clients/src/main/java/org/apache/kafka/clients/producer/internals/RecordAccumulator.java) · [Kafka · Producer Configs](https://kafka.apache.org/43/configuration/producer-configs/#batch.size)

| 설정 | Kafka 4.3 기본값 | 관찰할 변화 |
| --- | --- | --- |
| `batch.size` | `16384`바이트 | 파티션별 배치의 목표 크기다. 크면 더 많은 레코드를 담을 수 있고, 충분히 채우지 못하면 버퍼 공간이 남는다. |
| `linger.ms` | `5`ms | 배치가 덜 찼을 때 레코드를 더 모으는 시간이다. 배치가 먼저 차면 전송할 수 있으며, 브로커나 네트워크가 밀리면 실제 큐 대기는 더 길 수 있다. |
| `buffer.memory` | `33554432`바이트 | 전송할 레코드를 버퍼링하는 데 쓰는 메모리 기준이다. 버퍼가 부족하면 `send()`에서 확보를 기다린다. |

단일 호출 스레드가 매번 `send().get()`을 실행하면 응답이 올 때까지 다음 레코드를 제출하지 못한다. 같은 파티션에 한꺼번에 제출한 레코드가 적어 배치가 작아지므로 `linger.ms`를 늘려도 대기만 길어질 수 있다. 콜백을 사용하거나 여러 레코드를 제출한 뒤 Future를 모아 확인하면 기다리는 동안에도 레코드를 쌓을 수 있다. [18번 · Java 프로듀서 실습](18_building_and_debugging_java_kafka_producers.md#2-피자-주문의-생성과-조리를-발행한다) · [KafkaProducer API](https://kafka.apache.org/43/javadoc/org/apache/kafka/clients/producer/KafkaProducer.html)

부하를 비교할 때 키 분포와 레코드 크기, 전송량을 고정하고 `linger.ms` 또는 `batch.size`를 하나씩 바꾼다. `batch-size-avg`, `records-per-request-avg`, `record-queue-time-avg`로 배치 효과를 확인하고, 애플리케이션에서 전송 완료까지의 p95 지연과 `record-error-rate`를 함께 본다. [Kafka · Producer Metrics](https://kafka.apache.org/43/operations/monitoring/)

## 3. 타임아웃과 재시도 범위를 구분한다

| 설정 | 제어하는 범위 |
| --- | --- |
| `max.block.ms` | `send()`가 메타데이터와 버퍼 할당을 기다리는 시간 한도. 커스텀 직렬화나 파티셔너 내부 실행 시간은 이 한도에 포함되지 않는다. |
| `request.timeout.ms` | 브로커에 보낸 개별 요청의 응답을 기다리는 시간 한도. |
| `delivery.timeout.ms` | `send()` 반환 뒤 배치 대기, 응답 대기, 재시도를 포함해 최종 결과를 보고하는 시간 한도. `request.timeout.ms + linger.ms` 이상으로 설정한다. |
| `retries`, `retry.backoff.ms`, `retry.backoff.max.ms` | 재시도 횟수 상한, 첫 재시도의 대기 기준, 지수적으로 늘어나는 대기 시간의 상한. 전송 기한에 도달하거나 재시도 불가능한 오류가 발생하면 더 일찍 끝난다. |
| `max.in.flight.requests.per.connection` | 브로커 연결 하나에서 아직 응답이 없는 요청의 최대 수. |

`Future.get(기한, 단위)`의 타임아웃은 호출자가 더 기다리지 않겠다는 뜻이다. 전송은 계속될 수 있고 브로커가 이미 기록했을 수도 있어, 같은 이벤트를 곧바로 다시 제출하면 중복될 수 있다. 멱등성이 꺼진 채 재시도와 둘 이상의 진행 중 요청을 허용하면, 같은 파티션의 뒤 배치가 먼저 성공하고 앞 배치가 나중에 재시도되어 순서가 바뀔 수 있다. [Kafka · Producer Configs](https://kafka.apache.org/43/configuration/producer-configs/) · [KafkaProducer API](https://kafka.apache.org/43/javadoc/org/apache/kafka/clients/producer/KafkaProducer.html)

## 4. 중복과 유실을 어느 범위에서 제어할지 정한다

| 전달 의미 | 실패 상황에서의 동작 |
| --- | --- |
| 최대 한 번(at-most-once) | 실패한 전송을 재시도하지 않으면 재시도로 생기는 중복은 피하지만 기록을 잃을 수 있다. |
| 최소 한 번(at-least-once) | 성공을 확인할 때까지 다시 제출하는 흐름에서는 응답이 유실된 뒤 같은 이벤트가 중복 기록될 수 있다. |
| 정확히 한 번(exactly-once) | 멱등 프로듀서는 같은 프로듀서 세션의 내부 재시도로 생기는 중복 기록을 막는다. Kafka 입력 오프셋과 출력 레코드를 함께 확정하는 흐름은 트랜잭션과 `read_committed`를 사용한다. |

멱등 전송에는 `acks=all`, `retries>0`, `max.in.flight.requests.per.connection<=5`가 필요하다. Kafka 4.3에서는 충돌 설정이 없으면 기본으로 켜진다. `enable.idempotence=true`를 명시한 상태에서 조건을 어기면 `ConfigException`이 발생한다. 멱등성이 기본으로 켜진 상태에서도 연결당 진행 중 요청을 6 이상으로 설정하면 예외가 발생한다. [Kafka · Producer Configs](https://kafka.apache.org/43/configuration/producer-configs/#enable.idempotence) · [Kafka · 4.0 Producer 변경](https://kafka.apache.org/43/getting-started/upgrade/)

같은 이벤트를 애플리케이션이 `send()`로 두 번 제출하면 별개의 전송으로 처리된다. 애플리케이션 재발행에 대비하려면 안정적인 이벤트 ID로 중복 반영을 제어한다. [06번 · 멱등 프로듀서와 트랜잭션](06_kafka_producer_idempotence_and_transactions.md)

## 5. 커스텀 파티셔너가 필요한 조건을 정한다

주문 ID로 묶는 정도라면 키를 지정하고 Kafka의 기본 해시를 사용한다. 키 없이 파티션을 맡기면 기본 전략은 한 파티션에 레코드를 모아 배치 효율을 높인다. 특정 유형을 독립 파티션으로 라우팅해야 할 때 `partitioner.class`를 고려한다. `ProducerRecord`에 파티션을 직접 지정한 경우에는 그 번호가 우선한다. [Kafka · Producer Configs](https://kafka.apache.org/43/configuration/producer-configs/#partitioner.class)

커스텀 규칙을 배포하기 전에 키 없는 입력, 한 개뿐인 파티션, 파티션 증설, 특정 키의 트래픽 집중을 확인한다. 운영 중 규칙이나 파티션 수가 바뀌면 같은 키의 다음 레코드가 다른 파티션으로 갈 수 있으므로, 소비자가 기대하는 순서 범위도 확인한다. [04번 · Java 커스텀 파티셔너 구현](04_developing_reliable_kafka_producer_applications.md#3-java로-키-파티션-번호-커스텀-파티셔너를-검증한다)
