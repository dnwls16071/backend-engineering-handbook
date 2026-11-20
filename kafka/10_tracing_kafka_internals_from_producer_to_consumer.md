# Tracing Kafka Internals from Producer to Consumer

Kafka의 동작을 확인하려면 레코드가 기록되는 위치, 복구 가능한 사본, 컨슈머가 다시 읽을 위치를 구분해야 한다. 주문 이벤트 한 건을 기준으로 전송부터 소비까지 따라간다.

## 1. 추천 서비스에서 Kafka가 맡는 역할

Netflix가 공개한 라이브 이벤트 추천 사례에서 Message Producer는 이벤트 일정 변경을 감지하고 알림을 예약했다. Message Router는 Kafka, Pushy(WebSocket 프록시), 키-값 저장소를 사용하는 두 단계 발행·구독 구조의 일부였다. 디바이스는 추천 데이터를 미리 받아 두고, 알림을 받은 시점에 노출할 수 있었다. 이 사례에서는 Kafka를 추천의 전달 흐름에 배치했다. [Netflix TechBlog · Real-Time Recommendations for Live Events](https://netflixtechblog.com/behind-the-streams-real-time-recommendations-for-live-events-e027cb313f8f)

## 2. 레코드가 브로커에 저장되는 경로

1. 프로듀서는 부트스트랩 브로커로부터 토픽 메타데이터를 받아 대상 파티션의 리더를 찾는다. 주문 이벤트의 키를 `orderId`로 정하면 동일한 파티셔닝 조건에서 같은 주문의 이벤트가 같은 파티션으로 간다.
2. 리더는 배치를 파티션의 활성 로그 세그먼트 뒤에 추가하고 각 레코드에 오프셋을 부여한다. 오프셋은 해당 파티션의 위치다. 토픽 전체의 순서를 비교할 때는 파티션을 함께 확인한다.
3. 로그는 여러 세그먼트로 나뉜다. 세그먼트의 오프셋 인덱스를 사용하면 해당 오프셋 근처의 파일 위치에서 읽기 시작할 수 있다. 순차 추가와 배치 전송은 디스크와 네트워크 접근을 효율화한다.
4. `cleanup.policy=delete`는 보관 시간·크기에 따라 오래된 세그먼트를 정리한다. `compact`는 키의 최신 상태를 재구성하도록 이전 값을 비동기로 정리한다. 정리 후에도 남은 레코드의 오프셋은 유지된다. [Apache Kafka · Design](https://kafka.apache.org/43/design/design/) · [브로커 로그와 세그먼트](01_apache_kafka_cluster_and_log_fundamentals.md#3-로그-세그먼트와-보관-정책)

## 3. 리더 장애와 프로듀서 재시도

파티션 팔로워는 리더에서 로그를 복제한다. 리더가 장애를 겪으면 컨트롤러는 ISR의 후보를 우선 선택한다. Kafka 4.1 이후 새 클러스터에서는 ELR(Eligible Leader Replicas)이 기본 활성화되어, ISR이 비어 있을 때도 안전한 후보가 있으면 리더로 선출할 수 있다. `acks=all`은 현재 ISR의 확인을 기다리고, `min.insync.replicas`는 그 조건에서 쓰기를 허용할 ISR의 최소 크기를 정한다. 복제 계수 3과 `min.insync.replicas=2`인 파티션에 ISR이 하나만 남으면 새 `acks=all` 쓰기는 실패한다. [Apache Kafka · Replication](https://kafka.apache.org/43/design/design/#replication) · [Apache Kafka · Eligible Leader Replicas](https://kafka.apache.org/43/operations/eligible-leader-replicas/) · [Kafka 기본 복제 구조](01_apache_kafka_cluster_and_log_fundamentals.md#4-복제-isr-생산자-확인)

파티션 데이터 복제와 클러스터 메타데이터 관리는 다른 역할이다. ZooKeeper 모드에선 ZooKeeper와 Kafka 컨트롤러가 클러스터 메타데이터 및 조정에 관여했다. Kafka 4.x는 KRaft 모드에서 컨트롤러 쿼럼이 메타데이터를 관리한다. 브로커는 프로듀서·컨슈머의 데이터 요청을 처리한다. [Apache Kafka · KRaft vs ZooKeeper](https://kafka.apache.org/43/getting-started/zk2kraft/)

기록 성공 응답이 유실되면 프로듀서가 같은 배치를 재시도할 수 있다. 멱등 전송은 클라이언트 내부 재시도에 의한 중복 기록을 막고, Kafka 트랜잭션은 출력과 입력 오프셋을 함께 확정할 수 있게 한다. 처리량을 조정할 때는 파티션별 `batch.size`, 최대 대기 시간 `linger.ms`, `compression.type`의 조합을 보고 전송 지연과 CPU 사용량을 함께 측정한다. [Apache Kafka · Producer Configs](https://kafka.apache.org/43/configuration/producer-configs/) · [프로듀서 멱등성과 트랜잭션](06_kafka_producer_idempotence_and_transactions.md)

## 4. 다음 소비자가 읽을 위치

컨슈머 그룹은 파티션을 구성원에게 나눠 준다. 구성원이 추가되거나 빠져 리밸런싱이 일어나면 새 담당 컨슈머는 그룹에 커밋된 오프셋을 기준으로 이어 읽는다. 읽기 위치는 `poll()`로 전진하고, 커밋 위치는 재시작할 때의 기준이 된다. 예를 들어 오프셋 41을 업무 처리한 뒤 42를 커밋하면 다음 실행은 42부터 읽기 시작한다. [Apache Kafka · KafkaConsumer](https://kafka.apache.org/43/javadoc/org/apache/kafka/clients/consumer/KafkaConsumer.html) · [리밸런싱과 안전한 종료](05_developing_reliable_kafka_consumer_applications.md#3-리밸런싱과-안전한-종료)

| 장애 지점 | 확인할 결과 |
| --- | --- |
| 업무 처리 전에 오프셋 커밋 | 중단된 뒤 재시작하면 처리하지 못한 레코드를 건너뛸 수 있다. |
| 업무 처리 후 커밋 전에 중단 | 같은 레코드를 다시 처리할 수 있으므로 목적지에서 중복 반영을 제어한다. |
| Kafka 출력과 입력 오프셋을 묶은 트랜잭션 중단 | 입력은 이전 커밋 위치부터 다시 읽을 수 있고, 중단한 출력은 `read_committed`에서 조회되지 않는다. |

재현할 때는 03번 문서의 CLI로 파티션 리더·ISR과 그룹 오프셋을 조회하고, 05번과 06번 문서의 실습으로 재시작·트랜잭션 중단 시 읽기 위치를 비교한다. [Kafka CLI](03_managing_kafka_topics_records_and_consumer_groups_with_the_cli.md) · [수동 커밋 실습](05_developing_reliable_kafka_consumer_applications.md#4-docker에서-수동-커밋과-재시작-확인하기) · [트랜잭션 중단·커밋 실습](06_kafka_producer_idempotence_and_transactions.md#4-docker에서-중단과-커밋-비교하기)
