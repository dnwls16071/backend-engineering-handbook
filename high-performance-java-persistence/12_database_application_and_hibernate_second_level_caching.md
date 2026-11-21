# Database, Application, and Hibernate Second-Level Caching

캐시마다 공유 범위와 무효화 책임이 다르다. 적중률을 해석하려면 무엇을 저장하고 어떤 쓰기가 무효화를 일으키는지 먼저 확인한다. [Hibernate 2차 캐시](https://docs.hibernate.org/orm/6.6/userguide/html_single/#caching)

## 1. 데이터베이스 캐싱

PostgreSQL의 공유 버퍼는 테이블과 인덱스의 페이지를 재사용한다. 운영체제 페이지 캐시도 읽기 비용에 영향을 준다. `EXPLAIN (ANALYZE, BUFFERS)`의 `shared hit`는 PostgreSQL 공유 버퍼에서 찾았다는 의미다. `shared read`는 공유 버퍼에 없어서 읽어 들였음을 나타내며, OS 캐시에 있으면 물리 디스크 읽기가 없을 수 있다. 캐시가 준비된 경우와 초기 실행의 조건을 구분해 측정한다. [PostgreSQL EXPLAIN](https://www.postgresql.org/docs/17/sql-explain.html) · [PostgreSQL 공유 버퍼 설정](https://www.postgresql.org/docs/17/runtime-config-resource.html)

## 2. 애플리케이션 수준 캐싱

상품 요약 DTO처럼 자주 읽고 수정이 드문 결과는 애플리케이션에서 키로 캐시할 수 있다. 키에는 결과에 영향을 주는 테넌트, 조회 조건, 언어 등을 포함한다. cache-aside를 적용한다면 미스에서 DB를 읽어 채우고, 쓰기 커밋 뒤 관련 키를 무효화한다. 미스가 진행되는 동안 쓰기가 커밋되면 이전 값이 다시 채워질 수 있으므로 허용 지연, 버전 검증, 만료 시간을 함께 정한다. 여러 인스턴스가 로컬 캐시를 쓴다면 인스턴스 간 무효화 전달 여부도 확인한다. [Microsoft Cache-Aside 패턴](https://learn.microsoft.com/en-us/azure/architecture/patterns/cache-aside)

## 3. Hibernate 2차 캐시 구성과 검증

1차 캐시는 Session 또는 EntityManager 범위다. 2차 캐시는 SessionFactory에 속하는 여러 세션에서 엔티티 상태나 컬렉션 같은 캐시 영역을 공유할 수 있다. 호환되는 `RegionFactory`와 제공자를 설정한 뒤 캐시할 엔티티를 선택한다. 쿼리 결과 캐시는 별도 기능이며 `hibernate.cache.use_query_cache=true`뿐 아니라 개별 쿼리의 cacheable 설정도 필요하다. [Hibernate 캐시 설정](https://docs.hibernate.org/orm/6.6/userguide/html_single/#caching)

```java
@Entity
@Cacheable
@org.hibernate.annotations.Cache(
        usage = org.hibernate.annotations.CacheConcurrencyStrategy.READ_ONLY)
class Country {
    @Id
    private String code;

    private String displayName;
}
```

이 엔티티는 갱신하지 않는 참조 데이터 예시다. 첫 트랜잭션에서 읽은 뒤 세션을 닫고, 같은 팩토리의 새 세션에서 다시 읽어 2차 캐시 적중과 SELECT 횟수를 확인한다. 별도 JDBC나 다른 서비스가 테이블을 직접 갱신하는 경로가 있으면 Hibernate에 무효화가 전달되는지도 검증한다. [Hibernate Statistics](https://docs.hibernate.org/orm/6.6/javadocs/org/hibernate/stat/Statistics.html)

## 4. Hibernate 2차 캐시의 동시성 전략

| 전략 | 적용 전 확인할 점 |
| --- | --- |
| `READ_ONLY` | 수정하지 않는 값에 적용한다. 캐시된 엔티티를 갱신하는 사용 방식과 충돌한다 |
| `NONSTRICT_READ_WRITE` | 드물게 수정되며 잠시 이전 값을 읽을 가능성을 허용한다 |
| `READ_WRITE` | 갱신 과정에서 소프트 락으로 캐시 적중·재채우기를 조절한다. 캐시 미스가 나면 DB를 읽을 수 있다 |
| `TRANSACTIONAL` | 캐시 제공자와 트랜잭션 환경이 이 전략을 지원하고 함께 동작해야 한다 |

캐시의 소프트 락은 DB의 행 잠금과 별도로 동작한다. 갱신 직후 다른 세션에서 같은 키를 읽고, 롤백과 외부 갱신도 포함해 실제 가시성을 검증한다. [Hibernate CacheConcurrencyStrategy](https://docs.hibernate.org/orm/6.6/javadocs/org/hibernate/annotations/CacheConcurrencyStrategy.html)
