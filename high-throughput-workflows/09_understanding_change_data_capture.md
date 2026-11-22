# Understanding Change Data Capture

CDC는 데이터베이스 변경을 별도 경로로 전달한다. 초기 상태와 변경 스트림을 이어 검색, 동기화, 업무 이벤트 처리에 활용할 수 있다. [Debezium 3.6 · MySQL Connector](https://debezium.io/documentation/reference/3.6/connectors/mysql.html) · [AWS · Transactional Outbox](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html)

## 1. 폴링으로 충분한지 먼저 확인한다

갱신 시각 폴링은 조회 사이의 중간 상태와 물리 삭제를 표현하기 어렵다. 로그 기반 CDC는 행 변경을 포착할 수 있지만, 초기 적재·복제 권한·재개 위치·로그 보존을 운영해야 한다. 허용 가능한 시차에 맞춰 선택한다. [Debezium 3.6 · MySQL Connector](https://debezium.io/documentation/reference/3.6/connectors/mysql.html) · [MySQL 8.4 · Binary Log](https://dev.mysql.com/doc/refman/8.4/en/binary-log.html)

## 2. 동기화의 완료 상태를 정의한다

가령 검색 색인이 최신 주문 상태를 반영해야 한다면 DB의 커밋 시각과 색인된 버전 사이의 차이를 측정한다. 초기 스냅샷에서 도착한 기존 행을 신규 업무 동작으로 해석할지 별도로 정한다. [Debezium 3.6 · MySQL Connector](https://debezium.io/documentation/reference/3.6/connectors/mysql.html) · [AWS · Transactional Outbox](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html)
