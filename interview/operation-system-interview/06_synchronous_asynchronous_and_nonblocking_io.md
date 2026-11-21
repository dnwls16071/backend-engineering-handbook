# Synchronous, Asynchronous, and Nonblocking I/O

## 1. 동기 I/O와 비동기 I/O의 차이는 무엇인가요?

**30–60초 답변**

> I/O API 기준으로 동기는 호출의 반환에서 그 호출이 수행한 연산의 결과를 받는 방식입니다. 소켓의 `read()`는 읽은 바이트 수, EOF, 또는 오류를 돌려줍니다. 비동기는 요청을 제출하는 시점과 결과를 받는 시점이 분리됩니다. 예를 들어 `AsynchronousSocketChannel`의 `read()`에 콜백을 주면, 읽기 작업이 끝날 때 콜백이 결과를 받습니다. `Future`로 결과를 받는 API도 있고, 호출자가 즉시 `Future.get()`으로 기다리면 그 스레드는 결과가 올 때까지 진행하지 못할 수 있습니다. [Java NIO 채널 API](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/nio/channels/package-summary.html) · [Linux `read(2)`](https://man7.org/linux/man-pages/man2/read.2.html)

**꼬리 질문 · 이벤트를 받으면 모두 비동기 I/O인가요?**

이벤트가 무엇을 알려주는지 봅니다. `epoll`의 알림은 소켓에서 읽기나 쓰기를 시도할 수 있다는 **준비 상태**입니다. 실제 바이트 수는 이후 `read()`나 `write()`에서 받습니다. 완료 알림에서는 이미 제출한 I/O의 바이트 수나 오류가 결과로 전달됩니다. 비동기 API라도 내부적으로 작업 스레드에 의존할 수 있으므로, 호출자가 보는 API 계약과 구현의 실행 모델을 구분해서 설명합니다. [Linux `epoll(7)`](https://man7.org/linux/man-pages/man7/epoll.7.html) · [Java `AsynchronousFileChannel`](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/nio/channels/AsynchronousFileChannel.html)

## 2. 블로킹과 논블로킹 I/O의 차이는 무엇인가요?

**30–60초 답변**

> 블로킹은 I/O를 당장 진행할 수 없을 때 호출한 스레드가 준비를 기다릴 수 있는 방식입니다. 논블로킹 소켓은 지금 처리할 수 있는 만큼만 전송하고, 받을 데이터가 없는 상태처럼 진행할 수 없으면 `EAGAIN` 또는 `EWOULDBLOCK`을 반환합니다. 이 경우 호출자는 다른 일을 하거나 준비 알림을 기다렸다가 다시 호출할 수 있습니다. 논블로킹 소켓의 `read()`도 결과를 호출의 반환값으로 받으므로, 동기이면서 논블로킹일 수 있습니다. [Linux `recv(2)`](https://man7.org/linux/man-pages/man2/recv.2.html) · [Linux `open(2)`](https://man7.org/linux/man-pages/man2/open.2.html)

**꼬리 질문 · 준비 알림을 받으면 요청한 전체 데이터를 읽을 수 있나요?**

한 번에 읽을 수 있는 바이트는 요청보다 적을 수 있습니다. 스트림 소켓에서 길이가 양수인 읽기가 `0`을 반환하면 상대가 쓰기 방향을 정상 종료해 EOF에 도달했다는 뜻이고, `EAGAIN`은 현재 읽을 데이터가 없다는 뜻입니다. 준비 알림 이후 다른 스레드가 데이터를 먼저 가져갈 수도 있으므로, 소켓을 논블로킹으로 두고 실제 I/O 결과를 확인합니다. 파일 I/O도 소켓과 동일하게 동작한다고 가정하기 어렵습니다. Linux에서 일반 파일의 `O_NONBLOCK`만으로는 저장 장치 접근 대기를 피할 수 없습니다. [Linux `read(2)`](https://man7.org/linux/man-pages/man2/read.2.html) · [Linux `recv(2)`](https://man7.org/linux/man-pages/man2/recv.2.html) · [Linux `open(2)`](https://man7.org/linux/man-pages/man2/open.2.html)

## 3. 스레드 기반 I/O와 이벤트 루프 기반 I/O는 어떻게 다른가요?

**30–60초 답변**

> 요청마다 플랫폼 스레드를 쓰는 블로킹 모델에서는 요청을 순차 코드로 처리합니다. 소켓 응답을 기다릴 때 스레드는 잠들어 CPU를 내주지만, 대기 중에도 요청에 묶여 있어서 동시 대기가 많아지면 스레드 수나 풀의 대기열이 커질 수 있습니다. 이벤트 루프는 소수의 스레드가 `epoll`이나 Java `Selector`로 여러 연결의 준비 상태를 한꺼번에 기다리고, 준비된 연결을 돌아가며 처리합니다. 연결마다 전담 플랫폼 스레드를 두는 부담을 줄일 수 있는 대신 연결별 처리 상태를 유지해야 하고, 루프에서 오래 걸리는 작업을 실행하면 같은 루프의 다른 연결도 지연됩니다. [Linux `epoll(7)`](https://man7.org/linux/man-pages/man7/epoll.7.html) · [Java `Selector`](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/nio/channels/Selector.html)

**꼬리 질문 · 이벤트 루프에서 블로킹 DB 호출을 해야 한다면요?**

전용 워커 풀로 넘기고 완료 결과를 루프가 처리하도록 하거나 비동기 DB 클라이언트를 사용합니다. 워커 수와 대기열 상한을 DB 연결 풀과 함께 정합니다. 소켓 쪽도 소비가 느리면 읽기 관심을 일시 중지하거나 쓰기 대기 버퍼에 상한을 걸어 요청량을 제어합니다. Linux에서 에지 트리거 `epoll`을 사용한다면 보통 `EAGAIN`까지 처리합니다. 한 연결이 처리 시간을 독점하지 않도록 중간에 양보할 경우에는 아직 준비 상태인 연결을 별도 큐에 유지합니다. [Linux `epoll(7)`](https://man7.org/linux/man-pages/man7/epoll.7.html)
