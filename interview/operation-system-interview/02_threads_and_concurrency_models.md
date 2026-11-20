# Threads and Concurrency Models

## 9. 스레드란 무엇이며 왜 사용하나요?

**30–60초 답변**

> 스레드는 프로세스 안에서 독립적으로 실행이 진행되는 흐름입니다. 같은 프로세스의 스레드는 코드와 힙, 열린 파일을 공유하고, 각자 스택과 레지스터 문맥을 가집니다. 예를 들어 서버의 한 스레드가 네트워크 응답을 기다리는 동안 다른 스레드가 준비된 요청을 처리할 수 있습니다. CPU 작업을 분리할 수 있다면 여러 코어에서 병렬로 처리할 수도 있습니다. 여러 스레드가 공유 데이터를 읽고 쓸 때는 락이나 스레드 안전한 큐 등으로 접근을 조율합니다. [Linux `pthreads(7)`](https://man7.org/linux/man-pages/man7/pthreads.7.html) · [Linux `sched(7)`](https://man7.org/linux/man-pages/man7/sched.7.html)

**꼬리 질문 · CPU가 하나여도 스레드를 여러 개 쓰는 이유가 있나요?**

논리 CPU가 하나여도 여러 작업을 번갈아 진행할 수 있으므로 동시성은 가능합니다. 한 스레드가 I/O를 기다리는 동안 다른 스레드가 CPU를 쓰면 응답성을 높일 수 있습니다. 실행 가능한 CPU 작업만 여러 개라면 동시에 실행하는 데 논리 CPU가 여러 개 필요하며, 스레드를 늘리면 문맥 교환이나 락 경합 비용이 커질 수 있습니다. [Linux `sched(7)`](https://man7.org/linux/man-pages/man7/sched.7.html)

## 10. 프로세스와 스레드의 차이는 무엇인가요?

**30–60초 답변**

> 프로세스는 자체 가상 주소 공간을 갖고 자원을 관리하는 단위이고, 스레드는 그 안에서 명령을 실행하는 단위입니다. 서로 다른 프로세스는 기본적으로 격리된 주소 공간을 사용하므로 데이터를 교환하려면 소켓이나 공유 메모리 같은 수단이 필요합니다. 같은 프로세스의 스레드는 힙과 파일 디스크립터를 공유하지만 스택과 실행 문맥은 각각 가집니다. 그래서 스레드끼리는 객체 참조를 큐로 넘길 수 있고 공유 상태의 변경도 서로에게 영향을 줍니다. Linux에서 스케줄러가 CPU를 배정하는 대상은 개별 스레드입니다. [Linux `fork(2)`](https://man7.org/linux/man-pages/man2/fork.2.html) · [Linux `pthreads(7)`](https://man7.org/linux/man-pages/man7/pthreads.7.html) · [Linux `sched(7)`](https://man7.org/linux/man-pages/man7/sched.7.html)

**꼬리 질문 · 같은 프로세스에서 다른 스레드가 열린 파일을 닫으면 어떻게 되나요?**

파일 디스크립터 테이블을 공유하므로 한 스레드에서 디스크립터를 닫으면 다른 스레드도 그 번호를 새 I/O에 계속 쓸 수 있다고 가정하면 안 됩니다. 번호가 재사용되면 같은 정수가 다른 파일을 가리킬 수 있습니다. Linux에서는 이미 시작된 블로킹 I/O가 열린 파일에 대한 참조를 유지해 `close()` 이후에 완료될 수도 있습니다. 따라서 디스크립터를 누가 언제 닫을지 스레드 사이에 정해야 합니다. [Linux `pthreads(7)`](https://man7.org/linux/man-pages/man7/pthreads.7.html) · [Linux `close(2)`](https://man7.org/linux/man-pages/man2/close.2.html)

## 11. 사용자 수준 스레드와 커널 수준 스레드의 차이는 무엇인가요?

**30–60초 답변**

> 사용자 수준 스레드는 런타임이나 라이브러리가 실행할 작업을 고르고 문맥을 전환합니다. 커널 수준 스레드는 운영체제 스케줄러가 개별적으로 CPU에 배정합니다. Linux의 POSIX 스레드 구현인 NPTL은 각 `pthread`가 커널의 스케줄링 단위 하나에 대응하는 1:1 모델입니다. 사용자 수준 실행 단위를 OS 스레드 하나에 올리는 N:1 모델에서는 런타임이 문맥을 전환하고, 코어가 여러 개여도 한 번에 한 작업씩 실행됩니다. M:N 모델에서는 런타임이 여러 사용자 수준 실행 단위를 여러 OS 스레드에 나눠 올려 여러 코어를 활용할 수 있습니다. [Linux NPTL과 1:1 모델](https://man7.org/linux/man-pages/man7/pthreads.7.html#DESCRIPTION) · [Go 런타임 스케줄러](https://go.dev/src/runtime/HACKING#scheduler-structures)

**꼬리 질문 · 사용자 수준 스레드 하나가 블로킹 시스템 콜을 하면 모두 멈추나요?**

N:1 모델에서는 그 호출로 유일한 OS 스레드가 잠들면 그 위의 다른 작업도 실행을 기다립니다. 1:1 모델에서는 해당 스레드가 잠들어도 다른 스레드를 스케줄할 수 있습니다. Go처럼 여러 OS 스레드를 쓰는 런타임은 시스템 콜로 한 OS 스레드가 대기할 때 다른 OS 스레드에서 실행 가능한 고루틴을 계속 처리할 수 있습니다. 대기 중인 OS 스레드가 언제 풀리는지는 해당 호출에 달려 있습니다. [Linux `pthreads(7)`](https://man7.org/linux/man-pages/man7/pthreads.7.html) · [Go 런타임의 G, M, P](https://go.dev/src/runtime/HACKING#gs-ms-ps)

## 12. 여러 프로세스 대신 스레드를 사용하는 이유는 무엇인가요?

**30–60초 답변**

> 같은 주소 공간에서 데이터를 자주 주고받거나 캐시, 연결 풀 같은 자원을 함께 쓰는 작업에 스레드가 적합합니다. 예를 들어 파일을 읽는 스레드가 버퍼 참조를 큐에 넣으면 처리 스레드가 같은 버퍼를 사용할 수 있습니다. 새 스레드는 기존 주소 공간을 쓰고, 같은 프로세스 안에서 스레드를 전환할 때도 주소 공간을 계속 사용할 수 있습니다. 대신 공유 데이터와 버퍼 수명을 동기화해야 합니다. 작업 하나가 비정상 종료해도 나머지 작업과 서버를 계속 살려야 한다면 별도 프로세스로 실행하고 IPC로 결과를 받는 구조가 적합합니다. [Linux `pthreads(7)`](https://man7.org/linux/man-pages/man7/pthreads.7.html) · [Linux `fork(2)`](https://man7.org/linux/man-pages/man2/fork.2.html) · [Linux `signal(7)`](https://man7.org/linux/man-pages/man7/signal.7.html)

**꼬리 질문 · 스레드를 쓰면 항상 메모리 사용량과 처리 시간이 줄어드나요?**

Linux의 `fork()`는 copy-on-write로 부모의 사적 메모리 페이지를 자식과 처음에 공유하고, 쓰기가 발생하는 페이지를 필요할 때 분리합니다. 프로세스 간에도 공유 메모리로 복사를 줄일 수 있습니다. 스레드 쪽은 개별 스택의 메모리와 락 경합 비용이 듭니다. 같은 부하에서 처리량과 p99 지연을 비교하고, 메모리 비교에는 공유 페이지의 비용을 비례 배분한 PSS를 볼 수 있습니다. [Linux `fork(2)`](https://man7.org/linux/man-pages/man2/fork.2.html) · [Linux `mmap(2)`](https://man7.org/linux/man-pages/man2/mmap.2.html) · [Linux `proc_pid_smaps(5)`](https://man7.org/linux/man-pages/man5/proc_pid_smaps.5.html)
