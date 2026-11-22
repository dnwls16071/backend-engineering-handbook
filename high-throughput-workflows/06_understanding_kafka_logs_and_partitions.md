# Understanding Kafka Logs and Partitions

Kafka 토픽의 각 파티션은 오프셋이 붙은 로그다. 브로커는 파티션을 호스팅하고, 복제 구성이 있으면 리더와 팔로워를 통해 데이터를 유지한다. [Apache Kafka 4.3 · Introduction](https://kafka.apache.org/43/getting-started/introduction/) · [Apache Kafka 4.3 · Design](https://kafka.apache.org/43/design/design/)

## 1. 주문 단위 순서와 처리 병렬성을 함께 결정한다

같은 주문의 변경은 orderId를 키로 사용하고 동일 파티션 매핑을 유지한다. 한 파티션의 순서를 다른 파티션이나 토픽에 적용할 수 없다. 특정 키에 이벤트가 집중되면 파티션을 늘려도 그 키의 단일 파티션 병목이 남을 수 있다. [Apache Kafka 4.3 · Introduction](https://kafka.apache.org/43/getting-started/introduction/) · [Apache Kafka 4.3 · Design](https://kafka.apache.org/43/design/design/)

## 2. 내구성과 보존의 경계를 확인한다

리더 장애와 재전송 뒤에도 필요한 이벤트를 읽을 수 있도록 복제 수·ISR 설정과 보존 기간을 검토한다. 소비 오프셋과 로그 보존은 별개여서 오랫동안 뒤처진 소비자는 필요한 구간을 다시 읽을 수 있는지 확인해야 한다. [Apache Kafka 4.3 · Design](https://kafka.apache.org/43/design/design/) · [Apache Kafka 4.3 · Consumer Configs](https://kafka.apache.org/43/configuration/consumer-configs/)
