# Operating Self-Managed and Managed Kafka Clusters

Kafka 운영 방식을 고를 때는 클러스터를 누가 유지보수하는지와 애플리케이션 팀이 어떤 데이터·접근 계약을 책임지는지 함께 본다. 처리량, 보관 기간, 허용 지연과 복구 목표가 같아야 운영 비용도 비교할 수 있다.

## 1. 운영 방식과 책임

| 방식 | 제공되는 것 | 팀이 운영하는 범위 |
| --- | --- | --- |
| VM 또는 물리 서버에서 자체 운영 | Kafka를 설치할 컴퓨팅·네트워크·저장소 | 브로커와 KRaft 컨트롤러, 복제 배치, 디스크, 업그레이드, 장애 대응 |
| Kubernetes에서 자체 운영 | Strimzi 같은 Operator를 통한 배포·설정·롤링 업데이트 자동화 | 노드·스토리지·네트워크 가용성, Kafka 정책, 변경 검증과 장애 대응 |
| 용량을 지정하는 관리형 서비스 | 제공자가 브로커 인프라와 유지보수의 일부를 관리 | 서비스가 허용하는 범위에서 브로커 용량, 파티션, 토픽 정책과 클라이언트 연결 설계 |
| 탄력적으로 확장하는 관리형 서비스 | 제공자가 사용량에 따라 서비스 용량을 조정 | 서비스 한도, 피크 처리량·지연, 보관 기간, 접근 권한과 소비 지연 관리 |

클러스터를 직접 운영할 때는 브로커의 복제 배치와 KRaft 컨트롤러 과반을 각각 설계한다. 여러 가용 영역을 쓴다면 같은 파티션의 복제본이 여러 장애 영역에 퍼지도록 배치한다. 롤링 업그레이드 중에는 재시작한 브로커가 복제를 따라잡고 ISR이 회복됐는지 확인한 뒤 다음 브로커로 이동한다. [Apache Kafka · KRaft](https://kafka.apache.org/43/operations/kraft/) · [Basic Kafka Operations](https://kafka.apache.org/43/operations/basic-kafka-operations/) · [Kafka 4.3 Upgrade](https://kafka.apache.org/43/getting-started/upgrade/) · [Strimzi · Overview](https://strimzi.io/docs/operators/latest/overview.html)

## 2. 관리형 Kafka 서비스에서 확인할 것

- **Amazon MSK**. Provisioned에서는 브로커 유형과 용량 등을 선택한다. Standard와 Express의 저장소 관리 범위가 다르다. MSK Serverless는 클러스터 용량 조정을 서비스에 맡기는 방식이며, 토픽·파티션 한도와 연결 조건을 워크로드에 맞춰 확인한다. [AWS · MSK Provisioned](https://docs.aws.amazon.com/msk/latest/developerguide/msk-provisioned.html) · [MSK Broker Types](https://docs.aws.amazon.com/msk/latest/developerguide/broker-instance-types.html) · [MSK Serverless](https://docs.aws.amazon.com/msk/latest/developerguide/serverless.html)
- **Confluent Cloud**. 클러스터 유형에 따라 탄력적 용량과 전용 용량, 네트워크 연결 옵션과 사용 한도가 달라진다. 사용하려는 클라이언트와 함께 인증 방식, 사설 연결, 할당량을 확인한다. [Confluent Cloud · Cluster Types](https://docs.confluent.io/cloud/current/clusters/cluster-types.html) · [Confluent Cloud · Client Compatibility](https://docs.confluent.io/cloud/current/faq.html)

인프라 유지보수를 위임해도 팀은 이벤트 스키마와 파티션 키, 서비스 계정의 권한, Producer 오류 처리, 소비자 오프셋과 Lag을 관리한다. 공급자 설정 범위는 서비스마다 다르므로 필요한 Kafka 버전, 토픽 설정, 관리 API와 모니터링 지표를 실제로 사용할 수 있는지 확인한다. [AWS · Security in Amazon MSK](https://docs.aws.amazon.com/msk/latest/developerguide/security.html) · [Confluent Cloud · Cluster Limits](https://docs.confluent.io/cloud/current/clusters/cluster-types.html)

## 3. 관리형 서비스의 장단점 비교

| 판단 기준 | 비교 방법 |
| --- | --- |
| 운영 인력 | 직접 해야 하는 설치, 패치, 브로커 교체, 증설, 야간 대응을 적고 제공자가 맡는 범위를 확인한다. |
| 제어 범위 | 자체 운영에서 조정할 수 있는 브로커 설정과 버전, 관리형 서비스에서 지원하는 변경 범위·작업 시간·할당량을 비교한다. |
| 가용성 | 서비스의 SLA와 별개로 애플리케이션에서 생산 실패, 백로그, 복구 후 중복 반영을 검증한다. 다중 가용 영역과 지역 간 복구는 서로 다른 장애 범위로 평가한다. |
| 비용 | 브로커 또는 서비스 용량, 보관 저장량, 송수신, 사설 연결, 운영 인력을 같은 기간과 부하로 계산한다. 전체 로그를 별도 소비자 그룹 두 개가 읽으면 읽기 부하가 두 번 발생한다. |
| 이전 비용 | 토픽과 스키마를 옮기는 범위, 소비 위치를 옮길 방법, 클라이언트 인증과 네트워크의 변경, 전환 도중의 운영 시간을 함께 계산한다. |

지속 평균 유입이 10 MB/s라면 하루치 논리 로그가 약 864 GB다. 자체 운영에서 복제 계수 3으로 모두 보관하는 단순 계산은 약 2.6 TB다. 실제 용량에는 압축률과 보관 정책, 내부 토픽, 디스크 여유, 장애 복구용 여유를 반영한다. 관리형 서비스의 청구는 해당 요금제의 용량·저장·전송 단위로 다시 계산한다. [Apache Kafka · Topic Configs](https://kafka.apache.org/43/configuration/topic-configs/) · [Confluent Cloud · Cluster Provisioning](https://docs.confluent.io/cloud/current/clusters/cluster-types.html)

## 4. 장애 징후를 구분한다

| 지표 또는 상태 | 해석 |
| --- | --- |
| `OfflinePartitionsCount` | Kafka 4.3의 컨트롤러가 관측한 내부 토픽 이외의 오프라인 파티션 수다. |
| `UnderReplicatedPartitions` | ISR의 수가 할당된 복제본 수보다 작은 파티션을 센다. |
| `UnderMinIsrPartitionCount` | ISR이 `min.insync.replicas`보다 작은 파티션을 센다. `acks=all` 생산 실패와 함께 본다. |
| Consumer Lag | 소비자가 읽을 데이터가 얼마나 밀렸는지 보여 준다. 생산 속도, 처리 오류, 소비자 처리량을 추가로 본다. |
| KRaft 쿼럼 상태 | 메타데이터 리더와 컨트롤러 상태를 확인한다. 토픽의 데이터 파티션 ISR은 별도로 확인한다. |

[Apache Kafka · Monitoring](https://kafka.apache.org/43/operations/monitoring/) · [Basic Kafka Operations](https://kafka.apache.org/43/operations/basic-kafka-operations/)

[01번의 Docker 실습](01_apache_kafka_cluster_and_log_fundamentals.md#6-docker에서-레코드와-복제-상태-확인하기)에서 토픽을 만든 뒤 다음 조회로 메타데이터 리더와 파티션 배치를 확인한다.

```bash
docker compose exec -T kafka /opt/kafka/bin/kafka-metadata-quorum.sh \
  --bootstrap-server kafka:29092 describe --status

docker compose exec -T kafka /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server kafka:29092 --describe --topic orders.lifecycle.v1
```

첫 명령의 `LeaderId`는 메타데이터 쿼럼의 리더이고, 두 번째 명령은 토픽 파티션별 리더와 복제본 및 ISR을 보여 준다. 단일 노드 실습에서는 두 역할을 같은 노드가 맡을 수 있다. [Apache Kafka · Metadata Quorum Tool](https://kafka.apache.org/43/operations/kraft/)

Kafka 4.3.2에서 두 명령을 실행해 메타데이터 리더가 노드 1이고, 토픽의 파티션 세 개도 각각 브로커 1을 리더와 ISR로 표시하는 것을 확인했다.
