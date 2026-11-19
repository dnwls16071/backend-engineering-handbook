# Optimizing Single-Row and Bulk Inserts

쓰기 성능은 클라이언트 왕복 횟수, 문장 파싱, 커밋 비용, 데이터와 인덱스 페이지 갱신에 영향을 받는다. 실시간으로 들어오는 소량의 쓰기와 많은 레코드를 한 번에 가져오는 적재는 서로 다른 병목을 가질 수 있다. [Optimizing INSERT Statements](https://dev.mysql.com/doc/refman/8.4/en/insert-optimization.html)

## 소량 쓰기와 대량 적재

| 상황 | 확인할 최적화 |
| --- | --- |
| 한 요청에서 여러 행 쓰기 | 준비된 문장을 활용하고, 함께 반영해도 되는 행은 다중 행 `INSERT`나 배치로 묶는다. 트랜잭션은 업무상 원자성이 필요한 범위로 잡는다. |
| 대량 파일 적재 | `LOAD DATA`나 다중 행 배치를 비교한다. 가능하면 기본 키 순서로 넣어 InnoDB의 클러스터드 페이지 갱신을 모은다. |
| 배치 크기 조정 | 배치를 키우면 왕복과 커밋 횟수는 줄어들 수 있다. 잠금 시간, 롤백 범위, 문장 크기와 `max_allowed_packet`을 함께 본다. |

[Bulk Data Loading for InnoDB Tables](https://dev.mysql.com/doc/refman/8.4/en/optimizing-innodb-bulk-data-loading.html) · [LOAD DATA Statement](https://dev.mysql.com/doc/refman/8.4/en/load-data.html)

## 실습 · 한 문장에 여러 행 전달하기

실습 환경은 MySQL 8.4(InnoDB)다. 다음 예시는 한 문장으로 여러 행을 보내는 형태다. 같은 수의 행을 단건 문장으로 보낼 때와 비교하려면 두 방식의 커밋 횟수를 맞춘 뒤, 배치를 별도로 조정해 각 요소의 효과를 측정한다.

```sql
CREATE TABLE mysql_lab_readings (
    reading_id BIGINT PRIMARY KEY,
    source_id INT NOT NULL,
    reading_value INT NOT NULL
) ENGINE = InnoDB;

START TRANSACTION;
INSERT INTO mysql_lab_readings (reading_id, source_id, reading_value)
VALUES (101, 12, 38), (102, 12, 41), (103, 13, 29);
COMMIT;
```

세컨더리 인덱스가 있는 테이블은 삽입 시 해당 인덱스도 갱신한다. 적재 시간을 비교할 때는 인덱스 구성과 제약 조건까지 동일하게 유지한다.
