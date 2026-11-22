# Capturing MySQL Changes from the Binary Log

MySQL의 바이너리 로그는 복제와 복구에 쓰이는 변경 기록이다. Debezium은 MySQL 복제 프로토콜로 행 변경을 읽어 다운스트림 이벤트를 만든다. [MySQL 8.4 · Binary Log](https://dev.mysql.com/doc/refman/8.4/en/binary-log.html) · [Debezium 3.6 · MySQL Connector](https://debezium.io/documentation/reference/3.6/connectors/mysql.html)

## 1. 행 기반 로깅과 이미지 범위를 확인한다

이 실습은 log_bin이 켜져 있고 binlog_format=ROW, binlog_row_image=FULL인 MySQL을 사용한다. 행 이미지에서 필요한 이전·이후 필드를 읽을 수 있는지, 커넥터 복제 서버 ID가 다른 참여자와 충돌하지 않는지 확인한다. [MySQL 8.4 · Binary Logging Options](https://dev.mysql.com/doc/refman/8.4/en/replication-options-binary-log.html) · [Debezium 3.6 · MySQL Connector](https://debezium.io/documentation/reference/3.6/connectors/mysql.html)

## 2. 소스 지연과 로그 보존을 함께 운영한다

커넥터가 장시간 멈출 수 있는 기간과 복구 시간을 고려해 binlog를 보존한다. 기록한 소스 위치가 이미 제거됐다면 보존 상태를 조사하고 스냅샷과 대상 재동기화 계획으로 복구한다. [MySQL 8.4 · Binary Logging Options](https://dev.mysql.com/doc/refman/8.4/en/replication-options-binary-log.html) · [Debezium 3.6 · MySQL Connector](https://debezium.io/documentation/reference/3.6/connectors/mysql.html)
