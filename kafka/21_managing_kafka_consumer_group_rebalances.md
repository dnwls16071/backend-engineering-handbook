# Managing Kafka Consumer Group Rebalances

리밸런싱은 그룹의 소비자들이 맡을 파티션을 다시 정하는 과정이다. Kafka 4.3.2의 Java 컨슈머에서 `subscribe()`를 사용한 그룹을 기준으로, 프로토콜과 할당 전략에 따라 파티션이 어떻게 이동하는지 살펴본다.

## 1. classic 그룹의 참여와 할당

1. 컨슈머는 `FindCoordinator`로 `group.id`를 담당하는 브로커를 찾는다. 그룹에 멤버가 들어오거나 나가거나, 구독 토픽의 파티션 구성이 바뀌면 재할당이 일어날 수 있다.
2. 각 멤버는 `JoinGroup`으로 구독 정보와 지원하는 할당 전략을 전달한다. 코디네이터는 그룹 세대를 만들고 그룹 리더와 사용할 전략을 정한다.
3. 그룹 리더는 선택된 assignor로 멤버별 파티션을 계산해 `SyncGroup`으로 보낸다. 각 멤버는 코디네이터의 `SyncGroup` 응답으로 자신의 할당을 받아 적용한다. 컨슈머는 `poll()`에서 이 과정을 진행하고 할당 관련 콜백을 실행한다.

[Apache Kafka · Distribution](https://kafka.apache.org/43/implementation/distribution/) · [Apache Kafka · Protocol](https://kafka.apache.org/43/design/protocol/) · [Apache Kafka · ConsumerRebalanceListener](https://kafka.apache.org/43/javadoc/org/apache/kafka/clients/consumer/ConsumerRebalanceListener.html)

## 2. 하트비트, 세션, `poll()` 간격

| 설정 | 확인하는 동작 |
| --- | --- |
| `heartbeat.interval.ms` | classic 클라이언트가 코디네이터에 생존 신호를 보내는 간격이다. `session.timeout.ms`보다 작게 설정한다. |
| `session.timeout.ms` | classic 코디네이터가 하트비트를 받지 못한 멤버를 그룹에서 제거하기까지 기다리는 시간이다. 프로세스나 네트워크가 끊긴 경우에 적용된다. |
| `max.poll.interval.ms` | 그룹을 사용하는 애플리케이션이 `poll()`을 다시 호출하기까지 허용되는 최대 간격이다. 하트비트가 계속 전송되는 동안에도 배치 처리와 커밋이 너무 오래 걸리면 이 한도를 초과할 수 있다. |

classic 컨슈머의 하트비트는 백그라운드 스레드가 전송한다. `group.instance.id`를 설정하지 않으면 동적 멤버로 참여한다. 이 값을 설정한 정적 멤버는 같은 ID로 세션 만료 전에 재시작할 때 기존 할당을 유지할 수 있다. 동일 그룹에서 그 ID를 공유하는 두 프로세스를 동시에 실행하면 classic 프로토콜에서 한 인스턴스가 `FencedInstanceIdException`으로 차단될 수 있다. 정적 멤버가 `max.poll.interval.ms`를 넘기면 하트비트 전송이 중단되고 세션 만료 후 파티션이 재할당된다. [Apache Kafka · Consumer Configs](https://kafka.apache.org/43/configuration/consumer-configs/) · [Apache Kafka · KIP-62](https://cwiki.apache.org/confluence/spaces/KAFKA/pages/63406974/KIP-62+Allow+consumer+to+send+heartbeats+from+a+background+thread) · [Apache Kafka · KIP-345](https://cwiki.apache.org/confluence/spaces/KAFKA/pages/87300241/KIP-345+Introduce+static+membership+protocol+to+reduce+consumer+rebalances)

## 3. 다중 토픽 할당과 파티션 회수

classic 그룹은 `partition.assignment.strategy`로 클라이언트 assignor를 정한다. `RangeAssignor`는 토픽별로 파티션을 나눈다. `RoundRobinAssignor`는 여러 토픽의 파티션을 순서대로 돌며 각 파티션을 구독한 멤버에게 배정한다. `StickyAssignor`는 균형을 유지하면서 기존 소유권을 최대한 보존한다. `CooperativeStickyAssignor`는 비슷한 보존 목표를 가지고, 옮겨야 하는 파티션만 기존 멤버에게서 회수한 뒤 새 멤버에게 할당한다. 앞의 세 전략은 eager 방식으로 기존 파티션 전부를 반납한 뒤 할당을 적용한다. [Apache Kafka · Consumer Configs](https://kafka.apache.org/43/configuration/consumer-configs/) · [Apache Kafka · StickyAssignor](https://kafka.apache.org/43/javadoc/org/apache/kafka/clients/consumer/StickyAssignor.html) · [Apache Kafka · CooperativeStickyAssignor](https://kafka.apache.org/43/javadoc/org/apache/kafka/clients/consumer/CooperativeStickyAssignor.html)

`orders`와 `payments`에 각각 파티션이 세 개 있고, 멤버 ID `A`, `B`가 두 토픽을 모두 구독한 경우다.

| 전략 | 멤버 `A` | 멤버 `B` |
| --- | --- | --- |
| Range | `orders-0`, `orders-1`, `payments-0`, `payments-1` | `orders-2`, `payments-2` |
| Round Robin | `orders-0`, `orders-2`, `payments-1` | `orders-1`, `payments-0`, `payments-2` |

Range는 각 토픽에서 남는 한 파티션을 먼저 오는 멤버 `A`에 주므로 전체 할당은 4대 2가 된다. Round Robin은 토픽을 이어서 순환하므로 3대 3이 된다. 구독 토픽이 멤버마다 다르면 Round Robin은 구독하지 않은 멤버를 건너뛰므로 결과가 달라질 수 있다. [Apache Kafka · RangeAssignor](https://kafka.apache.org/43/javadoc/org/apache/kafka/clients/consumer/RangeAssignor.html) · [Apache Kafka · RoundRobinAssignor](https://kafka.apache.org/43/javadoc/org/apache/kafka/clients/consumer/RoundRobinAssignor.html)

`onPartitionsRevoked()`에서는 반납 대상의 작업을 멈추고, 아직 소유권이 있을 때 연속으로 처리를 마친 위치까지만 커밋한다. `onPartitionsAssigned()`에서는 새 파티션의 상태를 초기화한다. `onPartitionsLost()`는 이미 소유권을 잃은 파티션의 로컬 상태를 정리하는 데 사용한다. cooperative 방식에서는 유지하는 파티션의 작업을 이어갈 수 있다. [Apache Kafka · ConsumerRebalanceListener](https://kafka.apache.org/43/javadoc/org/apache/kafka/clients/consumer/ConsumerRebalanceListener.html)

## 4. 새 consumer 그룹 프로토콜

`group.protocol=consumer`는 KIP-848의 프로토콜을 선택한다. 코디네이터가 `ConsumerGroupHeartbeat` 요청과 응답으로 멤버 상태와 할당을 동기화하고, 클라이언트는 증분 변경을 적용한다. 브로커가 `group.consumer.assignors`로 제공하는 전략으로 할당을 계산하며, 클라이언트는 `group.remote.assignor`로 지원 전략을 선택할 수 있다. 하트비트 간격과 세션 타임아웃은 서버 측의 `group.consumer.heartbeat.interval.ms` 및 `group.consumer.session.timeout.ms`가 정한다. `max.poll.interval.ms`는 이 프로토콜에서도 클라이언트의 처리 진행을 확인한다. [Apache Kafka · Consumer Rebalance Protocol](https://kafka.apache.org/43/operations/consumer-rebalance-protocol/) · [Apache Kafka · Consumer Configs](https://kafka.apache.org/43/configuration/consumer-configs/)
