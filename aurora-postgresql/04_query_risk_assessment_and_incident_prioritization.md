# Query Risk Assessment and Aurora PostgreSQL Incident Prioritization

쓰기 경로와 읽기 경로의 사용자 영향, 잠금 전파 범위, 근거 강도를 함께 평가해 조치 순서를 정한다.

## 1. 위험도를 사례별로 평가하기

같은 실행 시간이어도 주문 성공률, 오류 지속 시간, 피크 구간의 호출 빈도, 차단한 세션 수에 따라 영향이 다르다. 단일 점수 대신 관측 구간, 영향받은 기능과 사용자 범위, 대기나 재시도 증가, 근거의 신뢰도를 따로 남긴다. 지표가 평시와 다른지를 [01번 기준선](01_event_readiness_and_local_postgresql_lab.md)과 대조한다.

## 2. 결제 경로와 관리자 조회의 우선순위 정하기

결제 경로의 짧은 쿼리라도 실제 결제 실패를 유발하면 먼저 대응한다. 관리자 집계가 오래 걸려도 격리된 Reader에서만 실행되고 다른 요청에 영향이 없다면 개선을 계획할 수 있다. 반대로 관리자 조회가 Writer의 풀이나 I/O를 차지해 결제에 영향을 주면 두 경로를 분리해 측정한다. 사용자 영향은 API 결과로, DB 측 영향은 인스턴스별 DB Load와 대기 분포로 확인한다. [Aurora DB Load](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/USER_PerfInsights.Overview.ActiveSessions.html)

## 3. 한 행의 락이 주문 전체로 전파되는 과정

같은 재고 행을 갱신하는 요청은 앞선 트랜잭션이 끝날 때까지 대기할 수 있다. 이 요청들이 연결을 오래 점유하면 공유 풀에서 다른 상품의 주문도 대기한다. 같은 시간대에 풀 사용량, 대기 세션 수, 루트 차단 세션을 확인한다. 앱의 503이 풀 대기에서 났는지, 실제 DB 오류에서 났는지도 구분한다. [Aurora Lock:transactionid](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/apg-waits.locktransactionid.html) · [차단 관계 진단](07_locks_deadlocks_connection_pools_and_retries.md)

## 4. 즉시, 당일, 계획, 보류로 분류하기

| 시점 | 판단과 실행 예 |
| --- | --- |
| 즉시 | 주문 실패가 이어지면 영향이 확인된 배치나 트래픽만 줄이고 오류·대기를 관찰한다. |
| 당일 | 반복되는 비정상 쿼리의 라우팅이나 실행 조건을 확인해 되돌릴 수 있는 완화를 적용한다. |
| 계획 | 조회 구조, 인덱스, 트랜잭션 흐름을 시험하고 개선 전후의 기준을 잡는다. |
| 보류 | 영향이나 원인 근거가 충분하지 않으면 추가로 수집할 지표와 재검토 시각을 정한다. |

각 항목은 담당자, 실행 또는 재검토 조건, 조치 후 확인할 지표를 기록한다.

## 5. 근거가 부족할 때 상태를 명확히 기록하기

예를 들어 관측 기간이 2분이고 Writer의 Lock 대기만 확인했다면, 그 사실과 Reader·애플리케이션 풀에서 아직 얻지 못한 자료를 함께 보고한다. 다음 관측 창과 필요한 데이터 소스를 지정한다. 정상 여부를 판단하려면 기준선과 충분한 관측 범위가 필요하다.
