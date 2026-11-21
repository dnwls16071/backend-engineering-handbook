# Aurora MySQL Event Readiness and Local Lab Setup

Aurora MySQL에서 쿠폰·주문 이벤트의 응답 지연, 실패율, 데이터 정합성을 함께 판단한다. SQL 실습은 격리된 MySQL 8.4로 수행한다. 운영 환경에서는 Aurora MySQL 8.4와 MySQL 8.0 호환인 Aurora MySQL 버전 3의 차이를 확인한다. [Aurora MySQL 8.4 호환성](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/AuroraMySQL.MySQL84.html) · [Aurora MySQL 버전 3](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/AuroraMySQL.MySQL80.html)

## 1. 이벤트 중 판단할 서비스 상태

요청률과 p95 지연, 오류율을 서비스 경로별로 확인한다. 품절과 중복 처리는 정상적인 업무 결과일 수 있으므로 타임아웃, 5xx, 초과 발급과 분리한다. DB는 Writer와 Reader를 인스턴스별로 나눠 CPU, DB Load의 대기 분포, 연결 수, Reader 지연을 본다. 계획된 배치와 배포 시각을 같은 시간축에 기록한다. [Aurora CloudWatch 지표](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/Aurora.AuroraMonitoring.Metrics.html)

## 2. Reader와 Writer 연결 구조 확인하기

클러스터 엔드포인트는 Writer에 연결한다. Reader 엔드포인트는 새 연결을 Aurora Replica로 분산하며, Replica가 없는 클러스터에서는 Writer에 연결된다. 기존에 빌린 연결이나 트랜잭션의 요청은 쿼리별로 이동하지 않는다. 쓰기 직후 읽기에 최신성이 필요한지, 앱이 어떤 풀을 실제로 사용하는지 확인한다. [Aurora 엔드포인트](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/Aurora.Overview.Endpoints.html) · [Reader 엔드포인트](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/Aurora.Endpoints.Reader.html)

```sql
SELECT DATABASE(), @@hostname, @@GLOBAL.innodb_read_only;
```

Aurora MySQL에서 `innodb_read_only`가 켜진 연결은 Reader에 연결된 것이다. 서비스가 요구한 역할과 실제 연결 대상이 일치하는지 요청 로그와 인스턴스 지표를 대조한다. [Aurora MySQL 연결 확인](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/AuroraMySQL.BestPractices.html)

## 3. 로컬 실습 환경 만들기

빈 로컬 MySQL 8.4를 사용한다. 예제는 컨테이너 네트워크를 끄고 내부 소켓으로만 접속한다. 서버 초기화가 끝나면 다음 SQL을 실행한다. 실습 종료 후 `docker stop aurora-my-lab`으로 컨테이너를 정리한다. [MySQL 공식 이미지](https://hub.docker.com/_/mysql)

```sh
docker run --detach --rm --network none --name aurora-my-lab -e MYSQL_ROOT_PASSWORD=lab-only -e MYSQL_DATABASE=aurora_lab mysql:8.4 --performance-schema=ON
docker exec -it aurora-my-lab mysql -uroot -p aurora_lab
```

```sql
CREATE TABLE aurora_my_inventory (
    product_id INT PRIMARY KEY,
    available INT NOT NULL CHECK (available >= 0)
) ENGINE = InnoDB;

CREATE TABLE aurora_my_orders (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    request_id VARBINARY(96) NOT NULL UNIQUE,
    product_id INT NOT NULL,
    status VARCHAR(20) NOT NULL,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    FOREIGN KEY (product_id) REFERENCES aurora_my_inventory(product_id)
) ENGINE = InnoDB;

INSERT INTO aurora_my_inventory VALUES (1, 1000), (2, 1000);

INSERT INTO aurora_my_orders (request_id, product_id, status, created_at)
WITH RECURSIVE seq(n) AS (
    SELECT 1 UNION ALL SELECT n + 1 FROM seq WHERE n < 100
)
SELECT CONCAT('seed-', n), 1 + MOD(n, 2),
       IF(MOD(n, 5) = 0, 'PAID', 'PENDING'),
       TIMESTAMPADD(MINUTE, n, '2025-01-01 00:00:00')
FROM seq;
```

## 4. 정상 기준선과 서비스 목표 세우기

같은 길이의 관측 창에 요청 유형, 트래픽, 캐시 상태, 풀 설정과 배포 버전을 기록한다. 주문 응답 지연이나 오류율의 목표와 동일 쿠폰 중복·초과 발급 방지 조건을 함께 둔다. DB 처리량만 올라가도 사용자 목표나 업무 정합성이 깨지면 안정적인 이벤트라고 볼 수 없다.

## 5. 단계별 부하 시험과 중단 기준

격리한 시험 환경에서 요청률을 조금씩 올린다. 각 단계의 최대 지속 시간, 요청 수, 데이터 복구 방법을 정한다. 서비스 오류율, 풀 대기, 복제 지연, 잘못된 발급 건수가 정한 경계에 닿으면 발생기를 멈춘다. 부하를 중단한 시각과 정상화가 관찰된 시각을 구분해 기록한다.
