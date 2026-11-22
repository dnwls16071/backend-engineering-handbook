# Choosing Data Structures for Services

자료구조는 자주 하는 연산을 기준으로 고른다. 키로 찾기, 순위로 읽기, 기록을 재생하기, 고유 개수를 세기에는 각각 다른 저장 구조가 맞는다. [Amazon · Dynamo](https://www.amazon.science/publications/dynamo-amazons-highly-available-key-value-store) · [Redis ZRANGE](https://redis.io/docs/latest/commands/zrange/) · [Kafka 4.3 Introduction](https://kafka.apache.org/43/getting-started/introduction/) · [Redis HyperLogLog](https://redis.io/docs/latest/develop/data-types/probabilistic/hyperloglogs/)

## 1. 요구와 연산을 연결한다

| 요구 | 구조 | 확인할 점 | 근거 |
| --- | --- | --- | --- |
| 상품 ID로 조회 | 키–값 인덱스 | 핫 키 및 원본 갱신 후 읽기 규칙 | [Amazon · Dynamo](https://www.amazon.science/publications/dynamo-amazons-highly-available-key-value-store) · [Microsoft Cache-Aside](https://learn.microsoft.com/en-us/azure/architecture/patterns/cache-aside) |
| 점수 상위 N개 | 정렬 집합 | 점수 변경과 동점 기준, 기간별 키 | [Redis ZRANGE](https://redis.io/docs/latest/commands/zrange/) |
| 사용자 이벤트 재생 | 파티션 로그 | 이벤트 키와 보존 기간, 재생 중 발생하는 중복 | [Kafka 4.3 Introduction](https://kafka.apache.org/43/getting-started/introduction/) · [AWS Transactional Outbox](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html) |
| 고유 방문자 근사 집계 | HyperLogLog | 근사 오차와 정답 확인에 쓸 표본 | [Redis HyperLogLog](https://redis.io/docs/latest/develop/data-types/probabilistic/hyperloglogs/) |

## 2. 데이터 원본과 조회 구조를 구분한다

게임 랭킹은 이벤트를 원본으로 두고 최신 점수의 정렬 집합을 파생 구조로 만들 수 있다. 랭킹이 손상되면 어느 시점의 이벤트에서 다시 만들어야 하는지와 동점 순서를 정한다. [Kafka 4.3 Introduction](https://kafka.apache.org/43/getting-started/introduction/) · [Redis ZRANGE](https://redis.io/docs/latest/commands/zrange/) · [Flink 2.2 Stateful Stream Processing](https://nightlies.apache.org/flink/flink-docs-release-2.2/docs/concepts/stateful-stream-processing/)

## 3. 복잡도 외에 운영 비용도 비교한다

요청당 계산량, 메모리, 큰 키의 집중, 복구에 필요한 재생 시간을 측정한다. 정확한 중복 제거가 필요한 과금과 오차를 허용하는 대시보드는 별도 경로로 설계한다. [Redis HyperLogLog](https://redis.io/docs/latest/develop/data-types/probabilistic/hyperloglogs/) · [Google SRE · Monitoring Distributed Systems](https://sre.google/sre-book/monitoring-distributed-systems/) · [AWS Transactional Outbox](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html)
