# Java Concurrency and Thread Pools

## 1. Java에서 동시성 문제가 발생하는 이유는 무엇인가요?

**30–60초 답변**

> 여러 스레드가 변경 가능한 상태를 공유하면 실행 순서에 따라 결과가 달라질 수 있습니다. 예를 들어 잔여 재고를 읽고 차감하는 사이에 다른 요청이 끼어들면 두 요청이 재고 하나를 동시에 예약할 수 있습니다. 이때는 확인과 차감을 한 연산으로 묶어 원자성을 확보해야 합니다. 또 한 스레드가 쓴 값을 다른 스레드가 볼 수 있도록 가시성을 확보하고, 초기화와 공개처럼 관찰 순서가 중요한 작업에는 happens-before 관계를 만들어야 합니다. 락을 도입한 뒤에는 락 획득 순서가 뒤섞여 교착상태가 생기거나, 하나의 락에 경합이 몰려 대기가 늘어날 수 있습니다. [Java Language Specification §17.1·§17.4](https://docs.oracle.com/javase/specs/jls/se25/html/jls-17.html)

**꼬리 질문 · Spring 싱글턴 서비스의 필드에 요청별 상태를 저장하면 어떻게 되나요?**

Spring의 싱글턴 빈 인스턴스는 해당 컨테이너 안에서 공유됩니다. 현재 요청의 사용자 ID를 인스턴스 필드에 저장했다가 나중에 읽으면, 그 사이 다른 요청이 필드를 덮어쓸 수 있습니다. 요청마다 달라지는 값은 메서드 인수나 요청별 지역 변수로 전달합니다. 지역 변수가 가리키는 객체도 여러 요청에서 공유한다면 그 객체의 변경은 별도로 보호합니다. [Spring Framework의 싱글턴 빈 스코프](https://docs.spring.io/spring-framework/reference/6.2/core/beans/factory-scopes.html#beans-factory-scopes-singleton) · [Java Language Specification §17.4.1](https://docs.oracle.com/javase/specs/jls/se25/html/jls-17.html#jls-17.4.1)

## 2. 가시성 문제가 정확히 언제 발생하나요?

**30–60초 답변**

> 서로 다른 스레드가 같은 변수에 접근하고 그중 하나가 쓰기인데, 그 접근들이 happens-before로 정렬되지 않으면 데이터 레이스입니다. 예를 들어 한 스레드가 일반 필드 `stop`에 `true`를 써도, 다른 스레드의 `while (!stop)` 루프가 그 변경을 관찰한다는 보장이 없습니다. Java 메모리 모델에서는 같은 `volatile` 필드에 대한 쓰기와 동기화 순서상 이후의 읽기 사이, 그리고 같은 모니터를 해제하는 동작과 이후에 획득하는 동작 사이에 happens-before 관계가 생깁니다. 스레드의 `start()`와 시작된 스레드의 동작 사이, 스레드의 모든 동작과 그 종료를 확인한 `join()` 반환 사이에도 이 관계가 생깁니다. [Java Language Specification §17.3](https://docs.oracle.com/javase/specs/jls/se25/html/jls-17.html#jls-17.3) · [§17.4.5](https://docs.oracle.com/javase/specs/jls/se25/html/jls-17.html#jls-17.4.5)

**꼬리 질문 · 설정 객체를 읽는 쪽에 락을 걸지 않고 안전하게 공개하려면요?**

`Config` 객체를 완전히 구성한 뒤 `volatile Config current`에 참조를 대입합니다. 독자는 `current`가 가리키는 스냅샷을 지역 변수에 한 번 읽어 사용합니다. 대입 전 초기화 쓰기 → `volatile` 쓰기 → 이후의 `volatile` 읽기 → 객체 필드 읽기로 happens-before 관계가 이어집니다. 공개 뒤에도 변경할 객체라면 후속 변경에도 동기화가 필요하므로, 설정 예시에서는 참조가 가리키는 내부 데이터까지 불변으로 두고 새 스냅샷으로 교체합니다. 생성 중 `this`가 유출되지 않은 객체의 `final` 필드에는 별도의 초기화 보장이 적용됩니다. 정적 초기화로 객체를 공개하는 방법도 있습니다. [Java Language Specification §17.4.5](https://docs.oracle.com/javase/specs/jls/se25/html/jls-17.html#jls-17.4.5) · [§17.5](https://docs.oracle.com/javase/specs/jls/se25/html/jls-17.html#jls-17.5) · [§12.4.2](https://docs.oracle.com/javase/specs/jls/se25/html/jls-12.html#jls-12.4.2)

## 3. Atomic 클래스를 써도 동시성 문제가 발생하는 사례가 있나요?

**30–60초 답변**

> 재고가 `1`인 `AtomicInteger stock`에서 `if (stock.get() > 0) stock.decrementAndGet()`을 실행한다고 가정하겠습니다. 두 스레드가 모두 `1`을 읽고 조건을 통과하면 첫 번째 차감에서 `0`, 두 번째 차감에서 `-1`이 됩니다. 차감 자체는 원자적이고, 조건 확인과 차감 사이에는 다른 스레드가 끼어들 수 있습니다. 재고가 하나의 값이라면 스냅샷을 읽어 양수인지 확인한 뒤 `compareAndSet(current, current - 1)`을 시도하고, 실패하면 값을 다시 읽어 조건부터 검사합니다. 재고와 예약 내역을 같이 바꿔야 한다면 두 상태를 함께 보호할 락이나 트랜잭션을 선택합니다. [AtomicInteger API](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/util/concurrent/atomic/AtomicInteger.html)

**꼬리 질문 · `updateAndGet()`에 넘긴 람다 안에서 예약 이벤트도 발행해도 되나요?**

경합 중에 갱신 함수가 재실행될 수 있어서 이벤트가 중복 발행될 수 있습니다. 갱신 함수는 상태 계산만 하고, 차감에 성공했음을 확인한 경로에서 이벤트를 처리합니다. 예약 상태를 DB에 저장한다면 예약과 발행할 이벤트를 같은 트랜잭션에 기록하고, 커밋된 이벤트를 별도 경로에서 발행할 수 있습니다. [AtomicInteger.updateAndGet()](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/util/concurrent/atomic/AtomicInteger.html#updateAndGet(java.util.function.IntUnaryOperator)) · [AWS의 트랜잭셔널 아웃박스 패턴](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html)

## 4. Java에서 동기화를 구현하는 방법에는 무엇이 있나요?

**30–60초 답변**

> 함께 지켜야 할 상태와 연산 범위에 맞춰 선택합니다. 한 JVM 안에서 여러 필드의 변경을 묶어야 하면 `synchronized`로 같은 모니터에서 읽기와 쓰기를 보호합니다. 진입 대기에 시간 제한이나 인터럽트 처리가 필요하면 `ReentrantLock`을 사용합니다. 단일 중지 플래그의 전달은 `volatile`로, 독립 카운터의 증가는 `AtomicInteger`로 처리할 수 있습니다. 키 하나를 최초 한 번만 등록하려면 `ConcurrentMap.putIfAbsent()`처럼 컬렉션에서 제공하는 원자적 연산을 사용합니다. 처음부터 불변 데이터를 공유하거나 변경 권한을 한 스레드에 한정하면 동기화할 상태가 줄어듭니다. [Java Language Specification §17.4.5](https://docs.oracle.com/javase/specs/jls/se25/html/jls-17.html#jls-17.4.5) · [ReentrantLock API](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/util/concurrent/locks/ReentrantLock.html) · [AtomicInteger API](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/util/concurrent/atomic/AtomicInteger.html) · [ConcurrentMap.putIfAbsent()](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/util/concurrent/ConcurrentMap.html#putIfAbsent(K,V))

**꼬리 질문 · 한 인스턴스에서 외부 API를 동시에 최대 20번 호출하게 하려면요?**

`Semaphore(20)`에 대해 호출 전에 `tryAcquire(timeout, unit)`으로 허가를 얻고, 얻은 경우에만 API를 호출한 뒤 `finally`에서 반환합니다. 허가를 얻지 못하면 남은 요청 기한에 맞춰 과부하 응답을 처리할 수 있습니다. 이 허가 수는 동시에 진행할 호출 수를 제한합니다. 초당 호출 횟수에도 상한이 있다면 시간 단위 요청량을 제어하는 별도 정책을 둡니다. [Semaphore API](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/util/concurrent/Semaphore.html)

## 5. `synchronized`의 장단점은 무엇인가요?

**30–60초 답변**

> `synchronized`는 같은 모니터를 사용하는 코드 사이에서 상호 배제와 가시성을 보장합니다. 범위가 코드에 드러나고, 예외가 발생해도 블록이나 메서드를 벗어나면 JVM이 모니터를 해제합니다. 짧은 임계 구역을 보호하기에 간단한 선택입니다. 여러 스레드가 같은 모니터를 오래 필요로 하면 대기가 늘어 처리량이 낮아지고, 여러 락을 서로 다른 순서로 잡으면 교착상태가 생길 수 있습니다. 획득 순서의 공정성이나 락 획득 대기 중 타임아웃·인터럽트 처리가 필요하면 `ReentrantLock`에서 해당 기능을 제공합니다. 그 경우 획득에 성공한 경로에서 `finally`로 해제를 보장합니다. [Java Language Specification §17.1](https://docs.oracle.com/javase/specs/jls/se25/html/jls-17.html#jls-17.1) · [§17.4.5](https://docs.oracle.com/javase/specs/jls/se25/html/jls-17.html#jls-17.4.5) · [ReentrantLock API](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/util/concurrent/locks/ReentrantLock.html)

**꼬리 질문 · `synchronized` 안에서 원격 호출을 해서 요청이 밀리면 어떻게 고치나요?**

스레드 덤프나 JFR의 `jdk.JavaMonitorEnter` 이벤트로 어떤 락에서 대기하는지 확인합니다. 상태를 일관되게 복사할 때만 락을 잡고 원격 호출은 밖에서 실행할 수 있는지 검토합니다. 응답을 반영할 때 락을 다시 잡아 버전이나 전제 조건을 확인해야, 호출 중 달라진 상태를 이전 응답으로 덮어쓰는 일을 막을 수 있습니다. [Oracle Java의 JFR 성능 분석 가이드](https://docs.oracle.com/en/java/javase/24/troubleshoot/troubleshoot-performance-issues-using-jfr.html)

## 6. `synchronized`는 어떻게 구현되어 있나요?

**30–60초 답변**

> JVM에서 각 객체에는 논리적으로 모니터가 연결됩니다. `synchronized (lock)` 블록은 바이트코드에서 `monitorenter`로 진입하고, 정상 종료와 예외 종료 경로에 `monitorexit`가 배치됩니다. `synchronized` 메서드는 클래스 파일의 메서드 플래그 `ACC_SYNCHRONIZED`를 보고 JVM이 호출과 종료 시 모니터를 얻고 해제합니다. 인스턴스 메서드는 `this`, 정적 메서드는 그 메서드를 선언한 클래스의 `Class` 객체를 잠급니다. 이미 모니터를 가진 스레드는 재진입할 수 있으며, 그 횟수만큼 해제해야 다른 스레드가 들어올 수 있습니다. [Java Virtual Machine Specification §2.11.10](https://docs.oracle.com/javase/specs/jvms/se25/html/jvms-2.html#jvms-2.11.10) · [§3.14](https://docs.oracle.com/javase/specs/jvms/se25/html/jvms-3.html#jvms-3.14) · [§6.5 `monitorenter`](https://docs.oracle.com/javase/specs/jvms/se25/html/jvms-6.html#jvms-6.5.monitorenter)

**꼬리 질문 · HotSpot에서 모든 `synchronized`가 같은 방식으로 실행되나요?**

HotSpot의 락 구현 경로는 JDK 버전과 설정에 따라 달라집니다. 예를 들어 JDK 23에서는 기본 `LockingMode`가 `LM_LEGACY`에서 `LM_LIGHTWEIGHT`로 바뀌었습니다. HotSpot 소스에는 객체 헤더의 잠금 비트를 CAS로 바꾸는 경로와 경합 등의 상황에 `ObjectMonitor`로 전환하는 경로가 있습니다. 이런 최적화와 관계없이 자바 코드에서는 같은 모니터의 상호 배제, 재진입, happens-before 규칙을 적용합니다. [Oracle JDK 24 릴리스 노트의 LockingMode 변경](https://www.oracle.com/java/technologies/javase/24all-relnotes.html) · [OpenJDK HotSpot의 synchronizer.cpp](https://github.com/openjdk/jdk/blob/master/src/hotspot/share/runtime/synchronizer.cpp) · [Java Language Specification §17.1·§17.4](https://docs.oracle.com/javase/specs/jls/se25/html/jls-17.html)

**꼬리 질문 · 가상 스레드를 도입하면 `synchronized`를 `ReentrantLock`으로 바꿔야 하나요?**

JDK 21–23에서는 가상 스레드가 `synchronized` 안에서 블로킹할 때 캐리어 플랫폼 스레드를 점유한 채 기다릴 수 있었습니다. JDK 24의 JEP 491은 모니터 획득 대기, 모니터 보유 중의 블로킹, `Object.wait()` 대기 등에서 모니터 때문에 캐리어에 묶이던 제약을 해소합니다. 네이티브 메서드나 외부 함수 호출이 걸린 경로는 여전히 고정될 수 있고, 같은 모니터에 대한 경합도 남습니다. 전환 여부는 배포 JDK, 실제 대기 지표, `tryLock()` 같은 기능 요구를 보고 판단합니다. [Oracle JDK 21 가상 스레드 가이드](https://docs.oracle.com/en/java/javase/21/core/virtual-threads.html) · [OpenJDK JEP 491](https://openjdk.org/jeps/491) · [Oracle JDK 24 변경 사항](https://docs.oracle.com/en/java/javase/24/migrate/significant-changes-jdk-24.html) · [Oracle JDK 24 가상 스레드 가이드](https://docs.oracle.com/en/java/javase/24/core/virtual-threads.html)

## 7. 스레드 풀을 왜 사용하고 크기는 어떻게 정하나요?

**30–60초 답변**

> 플랫폼 스레드 풀은 작업마다 스레드를 만드는 비용을 줄이고 실행에 쓰는 자원을 관리합니다. 일반적인 `ThreadPoolExecutor`는 워커가 `corePoolSize` 미만일 때 워커를 추가하고, 그 이후에는 큐에 넣습니다. 큐가 작업을 받지 못하면 `maximumPoolSize`까지 워커를 추가하고, 포화 상태에서는 거부 정책을 적용합니다. 종료된 풀에서도 새 작업은 거부됩니다. CPU 중심 작업은 가용 코어 수 근처에서 시작하고, I/O 중심 작업은 대기 비중과 하류 시스템의 처리 한도를 반영해 조정합니다. 큐에 허용할 대기 시간과 메모리를 기준으로 용량을 정하고, 포화 시 동작도 정의한 뒤 부하 테스트로 확인합니다. [ThreadPoolExecutor API](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/util/concurrent/ThreadPoolExecutor.html)

**꼬리 질문 · `newFixedThreadPool(16)`이면 부하가 들어와도 안전한가요?**

워커는 최대 16개이고 작업 큐는 무제한입니다. 유입이 지속적으로 처리량을 넘으면 큐 체류 시간과 메모리 사용이 늘어납니다. `corePoolSize`보다 큰 `maximumPoolSize`를 따로 둔 경우에도 무제한 큐가 작업을 계속 받아 주면 워커는 보통 코어 크기를 넘지 않습니다. 실시간 요청이라면 유한 큐와 `AbortPolicy`를 조합해 제출 실패를 명시적으로 처리할 수 있습니다. `CallerRunsPolicy`는 풀 실행 중에는 제출 스레드가 작업을 직접 수행하게 해 제출 속도를 늦출 수 있지만, 그만큼 요청 스레드가 점유되고 풀이 종료된 상태에서는 작업이 폐기됩니다. 부하 테스트에서는 큐 대기 시간, 활성 워커, 거부 건수와 p99를 같이 봅니다. [Executors.newFixedThreadPool()](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/util/concurrent/Executors.html#newFixedThreadPool(int)) · [ThreadPoolExecutor API](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/util/concurrent/ThreadPoolExecutor.html) · [CallerRunsPolicy API](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/util/concurrent/ThreadPoolExecutor.CallerRunsPolicy.html)

## 8. 컨텍스트 스위칭 비용이 있는데도 Spring MVC는 왜 스레드를 수백 개 사용하나요?

**30–60초 답변**

> 전통적인 동기 Spring MVC 요청은 JDBC나 외부 HTTP의 응답을 기다리는 동안에도 컨테이너의 요청 워커를 점유합니다. 대기하는 워커는 그동안 CPU를 쓰지 않으므로, 코어보다 많은 워커를 두면 다른 요청을 진행할 수 있습니다. 예를 들어 유입과 처리가 균형을 이루는 상태에서 초당 1,000건을 처리하고 각 요청이 워커를 평균 100ms 점유하면 평균 약 100개의 워커가 요청을 맡습니다. Tomcat 10.1 내장 HTTP 커넥터 풀의 기본 상한 `maxThreads`는 200이며, 배포 구성에서 별도 Executor를 지정하면 해당 Executor 설정이 적용됩니다. 실행 가능한 워커가 많이 몰리면 스케줄링과 컨텍스트 스위칭 비용이 늘고, DB 연결이 먼저 포화되면 워커를 늘려도 연결 대기가 길어질 수 있습니다. [Apache Tomcat 10.1 HTTP 커넥터 설정](https://tomcat.apache.org/tomcat-10.1-doc/config/http.html) · [Spring MVC 비동기 요청 처리](https://docs.spring.io/spring-framework/reference/6.2/web/webmvc/mvc-ann-async.html) · [Spring Boot 데이터소스 지표](https://docs.spring.io/spring-boot/reference/actuator/metrics.html)

**꼬리 질문 · DB 연결이 30개일 때 Tomcat 워커를 늘리면 처리량이 늘어나나요?**

HTTP 요청 중에는 DB 연결이 필요 없는 구간도 있으므로 두 풀의 크기를 동일하게 맞출 필요는 없습니다. DB 연결 30개가 이미 계속 사용 중이라면 워커를 추가해도 한 번에 빌려줄 수 있는 연결은 30개이고, 연결을 기다리는 요청이 늘어날 수 있습니다. 부하를 높이면서 연결 획득 시간, 풀의 활성 연결 수, DB 쿼리 지연과 성공 처리량을 확인합니다. 병목이 연결을 오래 보유하는 트랜잭션에 있으면 그 보유 시간을 줄이는 쪽부터 검토합니다. [Spring Boot 데이터소스 지표](https://docs.spring.io/spring-boot/reference/actuator/metrics.html#actuator.metrics.supported.jdbc)

**꼬리 질문 · MVC 비동기 처리나 가상 스레드를 쓰면 무엇이 달라지나요?**

`Callable`은 서블릿 요청 스레드를 반환하고 실행을 `AsyncTaskExecutor`에 넘깁니다. 그 작업에서 블로킹 JDBC를 호출하면 대기는 비동기 실행기의 스레드에서 일어납니다. `DeferredResult`는 다른 스레드나 콜백에서 결과를 제공하면 서블릿 컨테이너에 다시 디스패치합니다. Spring Boot 3.5의 기본 내장 Tomcat 구성에서는 `spring.threads.virtual.enabled=true`로 가상 스레드를 사용할 수 있습니다. 많은 블로킹 I/O 대기 중에 캐리어를 다른 작업에 돌릴 수 있고, 플랫폼 워커 상한인 `server.tomcat.threads.max`의 기본값 200은 가상 스레드를 켠 구성에서는 적용되지 않습니다. 어느 구성이든 DB 연결, 외부 서비스 동시 호출 수와 타임아웃은 실제 용량에 맞춰 관리합니다. [Spring MVC 비동기 요청 처리](https://docs.spring.io/spring-framework/reference/6.2/web/webmvc/mvc-ann-async.html) · [Spring Boot 3.5 설정 속성](https://docs.spring.io/spring-boot/3.5/appendix/application-properties/) · [Oracle JDK 24 가상 스레드 가이드](https://docs.oracle.com/en/java/javase/24/core/virtual-threads.html)
