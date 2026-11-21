# Two-Level Caching with Local L1 and Remote L2

각 애플리케이션 인스턴스에 Caffeine L1을 두고 Redis를 공유 L2로 사용한다. 네트워크 왕복을 줄이는 효과와 여러 인스턴스가 서로 다른 값을 읽을 수 있는 시간을 함께 측정한다. [Caffeine 3.2 설정 예제](https://github.com/ben-manes/caffeine/blob/v3.2.1/README.md)

## 1. 로컬 L1과 원격 L2의 읽기 순서

L1을 먼저 조회하고 미스면 L2를 확인한다. L2에도 값이 없으면 원본을 읽고 L2와 L1에 채운다. 값 객체는 변경 가능한 공유 참조를 그대로 넘기지 않고 불변 조회 모델로 만든다. 같은 프로세스에서 같은 키를 동시에 채울 때는 Caffeine의 `get(key, mappingFunction)`으로 계산을 합칠 수 있다. 다른 프로세스의 동시 로딩은 별도로 관찰한다. [Caffeine 로딩 API](https://github.com/ben-manes/caffeine/wiki/Population)

## 2. L1의 크기와 TTL 정하기

아래 예의 최대 10,000개와 2초는 실측을 시작할 설정이다. 항목 크기가 고르면 `maximumSize`, 크기 편차가 크면 `maximumWeight`와 `weigher`를 검토한다. 가중치는 객체 수명과 정확한 JVM 메모리 사용량을 대신하지 않으므로 힙과 GC를 함께 본다. freshness가 중요하면 쓰기 시각 기준인 `expireAfterWrite`를 사용하고 원본 버전이 이미 오래됐는지도 확인한다. [Caffeine eviction](https://github.com/ben-manes/caffeine/wiki/Eviction)

```java
import com.github.benmanes.caffeine.cache.Cache;
import com.github.benmanes.caffeine.cache.Caffeine;
import java.time.Duration;
import java.util.function.Function;

final class ProductL1 {
    record ProductView(long version, String name) {}

    private final Cache<String, ProductView> entries = Caffeine.newBuilder()
        .maximumSize(10_000)
        .expireAfterWrite(Duration.ofSeconds(2))
        .recordStats()
        .build();

    ProductView read(String key, Function<String, ProductView> loadFromL2OrOrigin) {
        return entries.get(key, loadFromL2OrOrigin);
    }

    void invalidate(String key) {
        entries.invalidate(key);
    }
}
```

로더가 부재를 캐시해야 한다면 `null` 대신 정의된 부재 표현을 사용하고 짧은 음성 캐시 만료 정책을 적용한다. 값 조회가 실패한 경우와 값이 실제로 없는 경우는 서로 다른 응답으로 처리한다. [캐시 부재 처리](03_preventing_cache_penetration_with_the_null_object_pattern.md)

## 3. 여러 인스턴스의 일관성 창 계산하기

A와 B가 같은 상품을 L1에 저장했다면 A의 쓰기 완료만으로 B의 값이 즉시 바뀌지 않는다. 커밋 이후 무효화 이벤트를 받아 두 인스턴스가 모두 항목을 지우는 시간을 측정한다. 이벤트가 누락될 수 있으면 TTL로 완화하되, 늦게 끝난 로더가 예전 값을 재삽입할 수 있다. 원본 버전과 관측 시각을 함께 유지해 오래된 값을 새 값처럼 다시 캐싱하지 않는다. [무효화와 버전 키](12_cache_invalidation_versioned_keys_and_consistency_windows.md)

## 4. L1을 추가하기 전후의 같은 창 비교하기

동일한 키 분포와 데이터, 인스턴스 수, 부하로 L2 단독과 L1+L2를 비교한다. 워밍업 이후 같은 길이의 창에서 L1 요청당 적중률, L1 미스 중 L2 적중률, 전체 요청당 Redis 호출 수, 원본 QPS와 응답 p95·p99를 기록한다. 전체 캐시 적중률을 계산할 때는 요청을 중복 집계하지 않는다. L1이 Redis 전송량을 줄였더라도 로컬 힙과 GC 비용이 늘었는지 확인한다. [원격 캐시 대역폭 측정](09_remote_cache_bandwidth_and_payload_measurement.md) · [Caffeine 통계](https://github.com/ben-manes/caffeine/wiki/Statistics)

## 5. L1의 장애 지점 점검하기

배포나 오토스케일로 여러 인스턴스가 동시에 시작하면 캐시가 비어 L2와 원본이 평소보다 바빠질 수 있다. L1 TTL이 짧아도 예전 L2 값을 다시 읽으면 stale 응답이 이어질 수 있다. 부하 테스트에서는 롤링 배포, 무효화 이벤트 지연, Redis 장애, 오래 걸리는 로더를 각각 시험한다. L1 로더가 같은 키의 요청을 합치더라도 느린 로더 한 건에 요청들이 함께 기다릴 수 있으므로 로딩 시간과 전체 요청 예산을 제한한다. [Caffeine 캐시 채우기](https://github.com/ben-manes/caffeine/wiki/Population)
