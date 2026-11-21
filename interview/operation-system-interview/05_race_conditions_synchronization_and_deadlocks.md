# Race Conditions, Synchronization, and Deadlocks

## 1. 경쟁 상태(Race Condition)란 무엇이고 왜 발생하나요?

**30–60초 답변**

> 경쟁 상태는 동시에 진행되는 작업들의 실행 순서에 따라 프로그램이 지켜야 할 조건이 깨지는 상황입니다. 예를 들어 초기값이 `0`인 공유 카운터에 두 스레드가 `count++`를 실행하면, 둘 다 `0`을 읽고 각자 `1`을 쓸 수 있습니다. 읽기, 계산, 쓰기 사이에 다른 스레드가 끼어들면서 증가 한 번이 사라진 겁니다. 멀티코어에서 동시에 실행될 때도, 단일 코어에서 스레드 실행이 번갈아 일어날 때도 이런 순서가 가능합니다. [Java Language Specification §17.4 메모리 모델](https://docs.oracle.com/javase/specs/jls/se21/html/jls-17.html#jls-17.4)

**꼬리 질문 · 데이터 레이스(Data Race)가 없어도 경쟁 상태가 발생하나요?**

가능합니다. Java에서 데이터 레이스는 서로 다른 스레드가 같은 변수에 접근하고 적어도 하나가 쓰기일 때, 그 접근이 happens-before 관계로 정렬되어 있지 않은 경우를 말합니다. 예를 들어 모든 접근을 같은 락으로 보호하는 맵도 `containsKey()`와 `put()`이 락을 각각 얻었다 놓으면, 두 스레드가 모두 키가 없다고 판단한 뒤 삽입해 첫 값을 덮어쓸 수 있습니다. 키를 처음 한 번만 등록하려면 확인과 삽입을 묶는 `ConcurrentMap.putIfAbsent()`를 사용할 수 있습니다. [Java Language Specification §17.4.5](https://docs.oracle.com/javase/specs/jls/se21/html/jls-17.html#jls-17.4.5) · [ConcurrentMap.putIfAbsent()](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/concurrent/ConcurrentMap.html#putIfAbsent(K,V))

## 2. 경쟁 상태를 어떻게 방지할 수 있나요?

**30–60초 답변**

> 먼저 함께 보호해야 할 공유 상태와 연산 범위를 정합니다. 재고가 `1`일 때 두 요청이 모두 차감되는 일을 막으려면, 남은 수량을 확인하고 차감하기까지를 하나의 임계 구역으로 묶습니다. Java에서는 같은 재고 데이터를 읽거나 갱신하는 모든 경로가 같은 락 인스턴스를 사용하도록 합니다. `synchronized` 블록이면 예외가 발생해도 모니터가 해제되고, `ReentrantLock`이면 획득에 성공한 뒤 `finally`에서 해제합니다. 독립된 카운터 하나의 증가라면 `AtomicInteger.incrementAndGet()`으로 처리할 수 있습니다. 설계 단계에서 공유하는 값을 불변으로 만들거나 변경 가능한 값을 한 스레드에 한정하는 방법도 있습니다. [Java Language Specification §17.1](https://docs.oracle.com/javase/specs/jls/se21/html/jls-17.html#jls-17.1) · [ReentrantLock](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/concurrent/locks/ReentrantLock.html) · [AtomicInteger](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/concurrent/atomic/AtomicInteger.html)

**꼬리 질문 · 여러 서버 인스턴스가 같은 DB 재고를 갱신하면 어떻게 하나요?**

JVM의 락은 같은 락 객체를 공유하는 스레드 사이에서 동작합니다. PostgreSQL의 `READ COMMITTED`에서 단일 행의 재고를 차감한다면 `UPDATE stock SET quantity = quantity - 1 WHERE product_id = ? AND quantity > 0`처럼 확인과 차감을 한 문장으로 처리할 수 있습니다. 앞선 갱신이 커밋되면 대기하던 갱신이 변경된 행에서 `WHERE` 조건을 다시 평가합니다. 갱신 건수가 `1`이고 커밋에 성공하면 차감 성공을 반환합니다. 갱신 건수가 `0`이면 해당 상품이 없거나 재고가 없는 경우를 처리합니다. [PostgreSQL의 Read Committed 격리 수준](https://www.postgresql.org/docs/18/transaction-iso.html#XACT-READ-COMMITTED)

## 3. 이진 세마포어와 뮤텍스의 차이는 무엇인가요?

**30–60초 답변**

> 둘 다 한 번에 한 스레드만 임계 구역에 들어가게 할 수 있습니다. 뮤텍스는 소유권이 있어서 락을 획득한 스레드가 해제하는 방식으로 공유 상태를 보호합니다. 이진 세마포어는 가용 허가 수를 `0` 또는 `1`로 유지하며, 세마포어를 획득한 이력이 없는 스레드도 허가를 추가할 수 있습니다. 예를 들어 허가 수 `0`에서 소비자가 기다리고, 생산자가 준비를 마친 뒤 허가 하나를 추가해 소비자를 진행시킬 수 있습니다. [POSIX pthread_mutex_lock()과 pthread_mutex_unlock()](https://man7.org/linux/man-pages/man3/pthread_mutex_unlock.3p.html) · [Java Semaphore](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/concurrent/Semaphore.html)

**꼬리 질문 · Java에서 `Semaphore(1)`이면 허가가 항상 최대 하나인가요?**

생성자 인수 `1`은 초기 허가 수입니다. `release()`는 허가를 추가하므로, 획득 없이 호출하면 가용 허가가 `2`가 될 수 있습니다. 상호 배제에 사용하려면 정상적인 획득 한 번에 해제 한 번을 대응시켜 최대 하나를 유지해야 합니다. `ReentrantLock.unlock()`은 현재 스레드가 락을 소유하는지 검사하고, 소유하지 않았다면 `IllegalMonitorStateException`을 던집니다. [Semaphore.release()](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/concurrent/Semaphore.html#release()) · [ReentrantLock.unlock()](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/concurrent/locks/ReentrantLock.html#unlock())

## 4. 가시성(Visibility)과 원자성(Atomicity)의 차이는 무엇인가요?

**30–60초 답변**

> 가시성은 한 스레드가 쓴 값이 다른 스레드의 읽기에 어떻게 반영되는지에 관한 성질입니다. 원자성은 여러 단계로 이루어진 연산도 다른 스레드에서 볼 때 하나의 연산처럼 적용되는 성질입니다. Java에서 `volatile` 필드 쓰기는 같은 필드의 이후 읽기보다 happens-before 관계에서 앞섭니다. `volatile int count`에 `count++`를 하면 읽기와 쓰기 사이에 다른 스레드의 증가가 끼어들 수 있습니다. 증가 전체를 원자적으로 처리하려면 `AtomicInteger.incrementAndGet()`을 쓰고, 여러 필드에 걸친 조건을 지켜야 한다면 관련 접근을 같은 락으로 보호합니다. 같은 락을 해제한 뒤 다른 스레드가 그 락을 획득할 때도 happens-before 관계가 생깁니다. [Java Language Specification §17.4.5](https://docs.oracle.com/javase/specs/jls/se21/html/jls-17.html#jls-17.4.5) · [AtomicInteger.incrementAndGet()](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/concurrent/atomic/AtomicInteger.html#incrementAndGet())

**꼬리 질문 · `volatile` 플래그로 일반 필드의 초기화 결과도 전달할 수 있나요?**

한 스레드가 `payload`를 한 번 초기화하고 `volatile boolean ready`에 `true`를 쓴다고 가정합니다. 다른 스레드가 그 `true`를 읽고 나서 `payload`를 읽으면 초기화 결과를 볼 수 있습니다. `payload` 쓰기 → `ready` 쓰기 → `ready` 읽기 → `payload` 읽기 순서로 happens-before 관계가 이어집니다. 공개 후에도 `payload`를 계속 변경한다면 이후 쓰기와 읽기에 맞는 동기화가 필요합니다. [Java Language Specification §17.4.5의 happens-before 순서](https://docs.oracle.com/javase/specs/jls/se21/html/jls-17.html#jls-17.4.5)

## 5. 교착상태(Deadlock)란 무엇이고 발생 조건 네 가지는 무엇인가요?

**30–60초 답변**

> 교착상태는 서로 필요한 자원이 반환되기를 기다리는 작업들이 모두 진행을 멈춘 상태입니다. 예를 들어 스레드 A가 락 1을 쥔 채 락 2를 기다리고, 스레드 B는 락 2를 쥔 채 락 1을 기다립니다. 자원 교착의 네 가지 필요조건은 상호 배제, 점유 대기, 비선점, 순환 대기입니다. 상호 배제는 한 자원 인스턴스를 동시에 한 작업만 점유하는 것이고, 점유 대기는 자원을 가진 채 추가 자원을 기다리는 것입니다. 비선점은 보유자의 자원을 강제로 회수할 수 없는 것이고, 순환 대기는 각 작업이 다음 작업이 가진 자원을 기다려 고리를 이루는 것입니다. [Coffman 외, System Deadlocks](https://uobdv.github.io/Design-Verification/Supplementary/System_Deadlocks-Four_necessary_and_sufficient_conditions_for_deadlock.pdf)

**꼬리 질문 · 자원 할당 그래프에 사이클이 생기면 항상 교착상태인가요?**

락처럼 자원 종류마다 인스턴스가 하나인 모델에서는 현재의 요청과 할당 관계로 그린 그래프의 사이클이 교착을 뜻합니다. 같은 종류의 자원에 교환 가능한 인스턴스가 여러 개라면 사이클 바깥의 작업이 인스턴스 하나를 반환해 사이클 안의 작업을 진행시킬 수 있습니다. 교착인지 판단하려면 현재 가용 수량으로 완료할 수 있는 작업부터 찾아 그 작업이 반환할 자원을 가용 수량에 더하는 과정을 반복합니다. [Holt, Some Deadlock Properties of Computer Systems](https://turing.cs.hbg.psu.edu/comp512.papers/Holt-72.pdf)

## 6. 교착상태를 어떻게 예방하고, 발생하면 어떻게 복구하나요?

**30–60초 답변**

> 예방하려면 네 가지 필요조건 중 하나를 깨도록 자원 사용 규칙을 정합니다. 예를 들어 두 계좌의 락이 필요한 이체에서 이체 방향과 관계없이 모든 경로가 계좌 ID 오름차순으로 락을 획득하면 순환 대기를 막을 수 있습니다. 이미 교착이 발생했다면 누가 어느 자원을 보유하고 기다리는지 확인하고, 자원을 반환할 수 있도록 작업을 중단하거나 롤백합니다. PostgreSQL은 교착을 탐지해 관련 트랜잭션 하나를 중단합니다. 애플리케이션은 재시도 가능한 작업이라면 롤백 뒤 새 트랜잭션으로 전체 작업을 제한된 횟수만큼 다시 실행할 수 있습니다. [Coffman 외, System Deadlocks](https://uobdv.github.io/Design-Verification/Supplementary/System_Deadlocks-Four_necessary_and_sufficient_conditions_for_deadlock.pdf) · [PostgreSQL의 교착상태 처리](https://www.postgresql.org/docs/18/explicit-locking.html#LOCKING-DEADLOCKS)

**꼬리 질문 · 락 대기가 타임아웃되면 교착상태라고 판단하나요?**

타임아웃은 정해진 시간 안에 락을 얻지 못했다는 신호입니다. Java 플랫폼 스레드에서는 스레드 덤프로 락의 소유자와 대기자를 확인하고 `ThreadMXBean.findDeadlockedThreads()`로 모니터나 `ReentrantLock` 같은 소유권 있는 동기화 객체의 대기 사이클을 찾을 수 있습니다. 시간 제한을 둔 `tryLock()`으로 두 번째 락을 기다렸다면 실패 시 이미 잡은 첫 번째 락을 해제하고, 작업을 취소하거나 제한된 횟수만큼 다시 시도할 수 있습니다. [ThreadMXBean.findDeadlockedThreads()](https://docs.oracle.com/en/java/javase/21/docs/api/java.management/java/lang/management/ThreadMXBean.html#findDeadlockedThreads()) · [ReentrantLock.tryLock()](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/concurrent/locks/ReentrantLock.html#tryLock(long,java.util.concurrent.TimeUnit))
