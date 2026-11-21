# Aurora MySQL Reader CPU Spikes and Ranking Queries

Reader에서 인기 랭킹 쿼리가 갑자기 많아졌다면 호출 수, 실행당 작업량, 인스턴스 연결 쏠림을 따로 확인한다.

## 1. 같은 쿼리의 호출량 폭증 확인하기

평시와 이벤트 창을 같은 길이로 잘라 지문별 호출 수, 실행당 시간, 검사 행 수를 비교한다. 호출 수만 증가했다면 API 경로와 캐시를 먼저 보고, 한 번의 실행 비용도 올랐다면 바인딩 범위와 계획을 확인한다. Writer와 Reader 인스턴스의 카운터를 섞지 않는다. [이벤트 구간의 지문 집계](03_slow_query_observability_and_workload_windows.md)

## 2. 랭킹·집계·정렬의 CPU 작업 확인하기

상위 10건만 반환해도 집계 대상 행을 모두 처리해야 할 수 있다. 행을 읽고 필터링하는 비용, 그룹 수, 내부 임시 테이블이나 추가 정렬의 사용 여부를 따로 확인한다. 아래는 [로컬 실습](01_event_readiness_and_local_mysql_lab.md)에서 실행하는 읽기 예제다. `EXPLAIN ANALYZE`는 문장을 실제 실행하므로 부하가 큰 운영 조회에는 먼저 일반 EXPLAIN을 사용한다. [MySQL EXPLAIN ANALYZE](https://dev.mysql.com/doc/refman/8.4/en/explain.html#explain-analyze)

```sql
EXPLAIN ANALYZE FORMAT=TREE
SELECT product_id, COUNT(*) AS paid_count
FROM aurora_my_orders
WHERE status = 'PAID'
GROUP BY product_id
ORDER BY paid_count DESC, product_id
LIMIT 10;
```

## 3. 한 Reader에 집중된 연결 찾기

Reader 엔드포인트는 새 연결을 분산한다. 풀의 장기 연결이 재사용되면 인스턴스별로 실행 수가 다른 상태가 이어질 수 있다. 인스턴스별 CPU·연결 수를 비교하고, 앱의 풀별 연결 대상과 연결 생성 시각을 확인한다. 기존 연결을 한꺼번에 닫으면 재연결 요청이 몰릴 수 있으므로 변경의 영향도 함께 관찰한다. [Aurora Reader 엔드포인트](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/Aurora.Endpoints.Reader.html)

## 4. 캐시 만료와 DB 호출 폭증 연결하기

Redis 미스와 랭킹 요청량이 같은 창에서 증가하는지 비교한다. 같은 키를 한 번만 갱신하고 대기 요청이 결과를 공유하거나, 여러 키의 TTL이 동시에 끝나지 않게 조정한다. 랭킹 결과가 잠시 늦어도 된다면 이전 값의 허용 나이와 원본 호출 한도를 함께 정한다. [캐시 스탬피드 대응](../cache/11_detecting_hot_keys_and_preventing_cache_stampedes.md)

## 5. 쿼리, 호출량, Reader 확장 중 선택하기

실행당 작업량이 크면 과거 기간 제한, 사전 집계, 인덱스나 조회 모델을 검증한다. 호출량을 줄일 수 있으면 중복 조회나 캐시 미스 원인을 고친다. 인스턴스 전반에 분산된 읽기 용량이 부족할 때는 Reader 확장의 효과를 같은 측정 창에서 확인한다. 변경 후 API p95, DB Load, 실행 수와 복제 지연을 함께 비교한다. [Aurora 인스턴스별 지표](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/Aurora.AuroraMonitoring.Metrics.html)
