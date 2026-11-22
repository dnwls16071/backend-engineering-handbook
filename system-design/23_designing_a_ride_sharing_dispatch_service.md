# Designing a Ride-Sharing Dispatch Service

승차 요청에 가까운 운전자를 찾는 문제와, 동시에 여러 요청이 한 운전자를 잡지 않도록 확정하는 문제를 분리한다. 위치 색인은 후보 검색에 쓰고 배차 상태는 명확한 소유자가 확정한다. [Redis GEOSEARCH](https://redis.io/docs/latest/commands/geosearch/) · [PostgreSQL 18 SELECT](https://www.postgresql.org/docs/18/sql-select.html#SQL-FOR-UPDATE-SHARE) · [Microsoft Microservice Boundaries](https://learn.microsoft.com/en-us/azure/architecture/microservices/model/microservice-boundaries)

## 1. 위치 갱신과 후보 검색을 구성한다

운전자 위치와 수신 시각 또는 증가 순번을 기록해 늦게 도착한 위치가 최신 위치를 덮지 않게 한다. 예를 들어 GEOSEARCH로 반경 후보를 구한 뒤 위치 유효 시간, 운행 상태, 도로 이동 ETA를 적용해 후보를 좁힌다. [Redis GEOSEARCH](https://redis.io/docs/latest/commands/geosearch/) · [PostgreSQL 18 UPDATE](https://www.postgresql.org/docs/18/sql-update.html)

## 2. 배차 수락을 한 번만 확정한다

제안마다 고유 offer_id와 만료 시각을 둔다. 운전자가 수락하면 원본에서 요청이 미배차이고 해당 운전자가 가용한지 조건부로 검증한다. 수락 응답이 끊기면 같은 요청 ID로 원본을 조회한다. 해당 제안이 종료됐고 확정된 배차가 없을 때 다음 후보로 넘어간다. [PostgreSQL 18 SELECT](https://www.postgresql.org/docs/18/sql-select.html#SQL-FOR-UPDATE-SHARE) · [PostgreSQL 18 UPDATE](https://www.postgresql.org/docs/18/sql-update.html) · [AWS Idempotent APIs](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/)

## 3. 오래된 위치와 응답 유실을 검증한다

위치 갱신 주기, 수락 기한, 요청부터 배차까지의 지연, 후보 없음 비율을 관찰한다. 두 승객이 같은 운전자를 선택하는 경쟁과 수락 직후 응답이 끊기는 경우를 시험한다. [Redis GEOSEARCH](https://redis.io/docs/latest/commands/geosearch/) · [AWS Idempotent APIs](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/) · [Google SRE · Monitoring Distributed Systems](https://sre.google/sre-book/monitoring-distributed-systems/)
