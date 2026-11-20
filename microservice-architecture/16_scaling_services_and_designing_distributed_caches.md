# Scaling Services and Designing Distributed Caches

확장할 대상을 찾으려면 먼저 사용량과 자원 병목을 측정한다. 애플리케이션 복제본을 늘려도 DB 쓰기나 한 키의 쓰기가 병목이면 개선은 제한적이다. 요청 지연과 큐, 캐시 적중률, DB 부하를 같은 시간축에서 확인한다. [Scale Cube](https://microservices.io/articles/scalecube.html) · [병목 식별](../load_testing_guideline/02_bottleneck_identification.md)

## 병목에 따라 확장 방법 고르기

| 증상 | 검토할 설계 |
| --- | --- |
| 무상태 HTTP 처리기의 CPU 부족 | 복제본 추가와 부하 분산, DB 연결 수와 전체 동시성 확인 |
| 반복 조회가 DB 자원을 사용 | 읽기 모델이나 캐시, 복제본 지연을 허용할 수 있는지 확인 |
| 단일 DB 쓰기 한계 | 인덱스·쓰기 부하 개선 후 파티션·샤딩 비용 검토 |
| 인기 상품이나 고객의 Hot Key | 요청 합치기, 조회 모델 보완, 키를 분산할 수 있는지 판단 |

## Redis 장바구니와 도메인 책임

장바구니의 소유 서비스는 수량과 수명, 체크아웃에서의 가격·재고 확인 규칙을 정한다. 장바구니 원본이 DB라면 Redis를 Cache-aside 어댑터로 두고, 조회 미스에서 원본을 읽어 캐시한다. 쓰기 커밋 후 키를 무효화하고, 재조회와 교차되어 옛 값이 다시 채워지는 경우도 검증한다. 오래된 캐시의 허용 범위와 TTL, 버전 비교 여부는 업무 계약에서 정한다. [Redis Cache-aside](https://redis.io/docs/latest/develop/use-cases/cache-aside/)

Redis가 장바구니의 주 저장소라면 만료, eviction, 영속성, 장애 조치 때 데이터 손실의 허용 범위가 달라진다. 장바구니 조회의 편의와 체크아웃의 불변식을 분리하고, 체크아웃의 가격·재고 판단은 소유 서비스에서 확인한다. 동시 갱신은 캐시가 있다는 이유로 해결되지 않으므로 원본의 트랜잭션이나 조건부 갱신과 함께 설계한다. [캐시 스탬피드 완화](../cache/06_mitigating_cache_stampedes.md) · [Valkey 영속성과 고가용성](../valkey/06_valkey_persistence_memory_and_high_availability.md)
