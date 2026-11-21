# Detecting Hot Keys and Preventing Cache Stampedes

핫 키는 반복 조회가 몰리는 키다. 캐시 스탬피드는 인기 값의 만료나 삭제 직후 여러 요청이 동시에 원본을 다시 읽는 상황이다. 평소 키별 부하와 만료 직후의 원본 호출을 함께 본다. [핫 키가 Redis Cluster에 집중되는 이유](08_handling_hot_keys_with_application_level_sharding_and_replication.md)

## 1. 핫 키의 호출률과 응답 크기 찾기

애플리케이션에서 표본을 추출해 논리 키 유형별 호출률과 반환 바이트를 구한다. 호출이 가장 많은 키와 가장 많은 바이트를 반환하는 키가 다를 수 있다. 개별 키 식별자를 그대로 메트릭 라벨에 넣으면 값의 개수가 급증하고 민감한 값이 노출될 수 있으므로, 표본 로그나 한도가 있는 상위 키 기록을 사용한다. `redis-cli --hotkeys`는 LFU 계열 정책에서 기록한 빈도 추정치를 사용한다. 샤드별 SCAN의 부하를 고려하며, 큰 메모리 키를 조사하는 `--memkeys`와 목적을 구분한다. [Redis CLI 핫 키 스캔](https://redis.io/docs/latest/develop/tools/cli/) · [페이로드 측정](09_remote_cache_bandwidth_and_payload_measurement.md)

## 2. 만료 직후 원본 호출 폭증 재현하기

다음 독립 실습은 키 하나가 만료된 순간을 두고, 스레드 16개가 동시에 같은 값을 요청하는 상황을 모의한다. 공유 값 없이 매번 원본을 호출하는 경우와 한 번 계산한 값을 대기 요청이 함께 받는 경우의 원본 호출 수를 비교한다. 실제 Redis 부하 시험에서는 TTL 직전·직후의 Redis 미스, 원본 QPS, 로딩 지연과 실패 수를 같이 기록한다.

```python
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Lock
from time import sleep

def count_origin_calls(coalesce):
    workers = 16
    start = Barrier(workers, timeout=5)
    refresh_lock = Lock()
    count_lock = Lock()
    calls = 0
    value = None

    def origin():
        nonlocal calls
        with count_lock:
            calls += 1
        sleep(0.02)
        return "product-view"

    def request(_):
        nonlocal value
        start.wait()
        if not coalesce:
            return origin()
        with refresh_lock:
            if value is None:
                value = origin()
            return value

    with ThreadPoolExecutor(max_workers=workers) as pool:
        assert list(pool.map(request, range(workers))) == ["product-view"] * workers
    return calls

assert count_origin_calls(False) == 16
assert count_origin_calls(True) == 1
```

## 3. 키별 single-flight와 분산 락

같은 프로세스에서는 진행 중인 로드를 키별로 공유할 수 있다. 합쳐진 요청도 기다릴 수 있는 시간을 제한하고, 로드가 실패하면 대기 요청에 실패를 전달한 뒤 진행 중 상태를 정리한다. 여러 인스턴스가 원본으로 몰리는 경우 분산 조율을 추가할 수 있다. 리스를 얻은 작업자는 로딩 전에 L2를 다시 보고, 완료 후 자신의 소유권을 확인해 해제한다. 리스 만료 뒤 구 작업자가 값을 덮어쓰는 문제는 값 버전이나 단조 증가 토큰으로 별도로 방지한다. [캐시 요청 합치기](06_mitigating_cache_stampedes.md) · [Redis 분산 락의 소유권과 만료](https://redis.io/docs/latest/develop/clients/patterns/distributed-locks/)

## 4. 확률적으로 만료 전에 갱신하기

이전 로딩에 걸린 시간 `D`, 현재 시각 `now`, 만료 시각 `expires_at`, 난수 `U`가 있을 때 `now - beta * D * ln(U) >= expires_at`이면 조기 갱신을 시도할 수 있다. `0 < U < 1`이고 `beta > 0`이며 시간 단위를 맞춘다. 만료 시각이 가까워지거나 로딩 비용이 크면 시도 확률이 높아진다. 갱신 후보가 여러 개 생길 수 있으므로 키별 합치기와 원본 동시성 한도를 함께 적용한다. [Optimal Probabilistic Cache Stampede Prevention](https://cseweb.ucsd.edu/~avattani/papers/cache_stampede.pdf)

## 5. TTL 지터와 음성 캐시

여러 키의 TTL에 작은 범위의 지터를 주면 한 번에 채운 값들이 같은 순간 만료되는 일을 줄일 수 있다. TTL 상한이 신선도 정책에 정해져 있다면 지터 결과도 그 범위 안에 둔다. 같은 인기 키 하나의 만료는 지터만으로 요청이 합쳐지지 않는다. 원본에서 부재가 확인된 키는 짧은 음성 TTL로 저장할 수 있다. 타임아웃과 일시 오류는 부재로 저장하지 않고, 새 데이터 생성 시 음성 항목도 지운다. [음성 캐시와 부재 처리](03_preventing_cache_penetration_with_the_null_object_pattern.md)
