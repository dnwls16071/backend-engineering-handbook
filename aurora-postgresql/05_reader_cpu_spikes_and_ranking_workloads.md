# Aurora PostgreSQL Reader CPU Spikes and Ranking Workloads

Reader의 CPU가 올랐을 때 SQL 실행당 비용이 변했는지, 호출 수가 늘었는지, 연결이 한 Replica에 집중됐는지 차례로 확인한다.

## 1. 랭킹 쿼리의 실행 수와 비용 나누기

[쿼리 통계 스냅샷](03_query_observability_and_event_window_analysis.md)을 정상 창과 이벤트 창에서 각각 비교한다. 동일 지문의 평균 시간은 비슷한데 실행 수만 늘었다면 요청 수, 캐시 미스, 무효화 시점을 먼저 본다. 평균 시간도 늘었다면 입력 행 수와 실행 계획, 해당 인스턴스의 CPU·I/O 경합을 확인한다. Writer와 Reader의 통계를 합치기 전에 각 연결의 실제 목적지를 확인한다. [Aurora 인스턴스별 지표](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/Aurora.AuroraMonitoring.Metrics.html)

## 2. 집계와 정렬이 사용하는 비용 읽기

실습 쿼리는 PAID 주문을 상품별로 집계한 뒤 상위 10건을 고른다. `LIMIT`은 반환 결과를 제한하지만 집계에 필요한 입력을 먼저 처리해야 한다. 계획에서는 스캔 행 수, 집계의 메모리 사용과 분할, 정렬 노드와 임시 블록 사용량을 본다. `work_mem`은 여러 연산과 병렬 워커에 곱해 적용될 수 있으므로 동시 요청을 고려한다. [PostgreSQL EXPLAIN](https://www.postgresql.org/docs/18/using-explain.html) · [PostgreSQL 메모리 설정](https://www.postgresql.org/docs/18/runtime-config-resource.html)

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT product_id, count(*) AS order_count
FROM aurora_lab_orders
WHERE status = 'PAID'
GROUP BY product_id
ORDER BY order_count DESC, product_id
LIMIT 10;
```

## 3. 한 Reader로 몰리는 연결 진단하기

Reader 엔드포인트의 분산 단위는 새 연결이다. 풀의 기존 연결을 사용하면 새 쿼리가 다른 Reader로 자동 이동하지 않는다. 인스턴스별 연결 수, 신규 연결 생성 시각, 앱 인스턴스와 풀 설정을 비교하고, 실제 연결에서 도착한 인스턴스를 기록한다. Reader를 추가한 뒤에도 기존 풀의 연결이 한 서버에 남을 수 있으므로 연결 교체와 재연결 폭주를 함께 고려한다. [Aurora Reader 엔드포인트](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/Aurora.Endpoints.Reader.html)

## 4. 캐시 만료 직후 원본 요청 확인하기

같은 랭킹의 캐시 TTL 경계에서 미스 수, 원본 랭킹 실행 수, Reader CPU와 DB Load가 함께 오르는지 본다. 동일 키 갱신을 한 번으로 합치거나, 여러 키의 만료에 지터를 준다. 최신성이 허용하는 동안 이전 랭킹을 제공한다면 값의 생성 시각과 허용 기간을 정한다. [캐시 스탬피드 대응](../cache/11_detecting_hot_keys_and_preventing_cache_stampedes.md)

## 5. Reader 증설과 쿼리 개선의 판단 기준

호출량은 안정적인데 한 번의 집계가 많은 행을 읽으면 기간 조건, 사전 집계, 조회 모델 개선을 먼저 검증한다. 각 Reader가 같은 수준으로 지속적으로 포화되고 트래픽이 나눌 수 있는 읽기라면 증설 효과를 측정할 수 있다. 부하가 한 Reader에 치우쳐 있으면 연결 분배를 확인한다. 변경 전후 동일 구간에서 API p95, DB Load의 CPU 부분, 집계 또는 정렬 작업량, 복제 지연을 대조한다.
