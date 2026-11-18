# Java Troubleshooting

Java 장애를 진단할 때는 먼저 발생 시각과 영향 범위를 좁힌다. 예외가 난 코드 경로는 Stack Trace에서, 응답이 멈춘 스레드는 Thread Dump에서, 메모리를 붙잡는 참조는 Heap Dump에서 조사한다. 명령과 옵션 예시는 JDK 21 HotSpot을 기준으로 한다.

## 1. 에러 내용 분석하기

1. **증상을 분류한다.** 요청이 실패했는지, 응답이 지연됐는지, JVM 프로세스가 종료됐는지 확인한다. 최초 발생 시각, 영향받은 API와 인스턴스, 배포 버전을 기록한다.
2. **증거를 연결한다.** 같은 시간대의 오류 로그, 요청 ID, JVM·컨테이너 지표, 직전 배포나 설정 변경을 비교한다. 재시도로 같은 예외가 반복됐다면 최초 실패를 찾아 원래 오류 메시지와 스택을 확보한다.
3. **가설을 하나씩 검증한다.** 동일 버전과 입력으로 가능한 범위에서 재현한다. 예를 들어 커넥션 대기가 의심되면 해당 요청의 스택과 풀의 대기 수를 함께 본다.

| 관찰한 증상 | 우선 확보할 자료 |
| --- | --- |
| 일부 요청이 예외로 실패 | 오류 로그와 전체 Stack Trace, 요청 ID |
| JVM은 살아 있지만 여러 요청이 멈춤 | 같은 시간대의 Thread Dump 여러 개, CPU·외부 호출 지표 |
| GC 후에도 힙 사용량이 계속 높아짐 | GC 로그나 JFR로 추세 확인 후 필요한 시점의 Heap Dump |
| JVM 프로세스가 갑자기 종료됨 | 종료 코드, OS·컨테이너 이벤트, 생성된 JVM 치명 오류 로그 |

**공식 문서** [Oracle Java 트러블슈팅 준비](https://docs.oracle.com/en/java/javase/21/troubleshoot/prepare-java-troubleshooting.html) · [Oracle Java 메모리 누수 진단](https://docs.oracle.com/en/java/javase/21/troubleshoot/troubleshooting-memory-leaks.html)

## 2. Stack Trace에서 실패 경로 읽기

예외 타입과 메시지로 어떤 작업이 실패했는지 파악하고, 각 예외의 프레임을 위에서부터 읽는다. 바깥 예외의 애플리케이션 프레임은 실패의 업무 맥락을 보여준다. `Caused by`를 따라가면 하위 작업의 실패를 확인할 수 있다.

```text
java.lang.IllegalStateException: Order import failed
    at example.OrderImportService.load(OrderImportService.java:42)
Caused by: java.nio.file.NoSuchFileException: /data/orders.csv
    at java.base/sun.nio.fs.UnixException.translateToIOException(UnixException.java:92)
    ...
```

이 예에서는 주문 가져오기 중 파일 조회가 실패했다. `load`에 전달된 경로를 확인하고, 애플리케이션이 실행되는 환경에서 해당 경로와 파일 마운트가 유효한지 확인한다. 가장 안쪽 예외가 가리키는 실패와 그것을 일으킨 환경이나 입력까지 연결해야 수정 범위가 드러난다.

- `Suppressed`는 주 예외를 유지하면서 함께 기록된 예외다. try-with-resources로 자원을 닫는 중 발생한 오류가 대표적이다.
- `... n more`는 바깥 예외와 공통인 스택 프레임을 생략한 표기다. 소스 줄 번호가 있다면 운영 중인 빌드와 같은 버전의 소스를 연다.
- 수정 후 같은 입력으로 다시 실행해 실패가 해소됐는지 확인하고, 같은 조건을 회귀 검증에 사용한다.

**공식 문서** [Throwable과 printStackTrace](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/Throwable.html) · [StackTraceElement](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/StackTraceElement.html)

## 3. Thread Dump로 스레드 대기 분석하기

Thread Dump는 수집 순간의 스레드 상태와 실행 스택을 보여준다. `pid`에 대상 JVM의 PID를 지정하고, JVM이 실행 중인 호스트에서 같은 유효 사용자와 그룹 권한으로 수집한다. 지연이 이어진다면 짧은 간격으로 여러 번 떠서 같은 스택과 락이 계속 보이는지 비교한다.

```sh
jcmd "$pid" Thread.print -l > "threads-$(date -u +%Y%m%dT%H%M%SZ).txt"
```

| 상태 또는 패턴 | 확인할 내용 |
| --- | --- |
| `BLOCKED` | 모니터 락을 기다리는 스레드다. 여러 스레드가 동일한 락을 기다리면 락을 가진 스레드의 스택을 찾는다. |
| `WAITING`, `TIMED_WAITING` | 유휴 워커의 정상 대기일 수 있다. 요청을 처리해야 하는 스레드가 커넥션, 큐, 다른 작업의 완료를 기다리는지 스택을 확인한다. |
| `RUNNABLE` | JVM에서 실행할 수 있는 상태다. 운영체제 자원을 기다릴 수도 있으므로 CPU를 쓰는지는 CPU 지표와 함께 판단한다. |
| 동일한 락 대기 관계가 반복됨 | 서로 상대가 가진 락을 기다리는 순환은 데드락 후보이고, 하나의 락에 대기가 집중되면 락 경합 후보로 본다. |

JDK 21에서 가상 스레드의 스택까지 보고 싶다면 아래 형식으로 수집한다. JSON 형식에는 기존 `Thread.print -l`의 락 상세 정보가 포함되지 않으므로, 필요한 정보를 기준으로 명령을 고른다.

```sh
jcmd "$pid" Thread.dump_to_file -format=json "/var/lib/myapp/dumps/threads-$(date -u +%Y%m%dT%H%M%SZ).json"
```

**공식 문서** [JDK jcmd](https://docs.oracle.com/en/java/javase/21/docs/specs/man/jcmd.html) · [Java Thread.State](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/Thread.State.html) · [OpenJDK 가상 스레드 관측](https://openjdk.org/jeps/444#Observing-virtual-threads)

## 4. Heap Dump로 메모리를 유지하는 참조 찾기

Heap Dump는 한 시점의 Java 힙에 있는 객체와 참조 관계를 기록한다. 먼저 GC 로그나 JFR에서 부하가 비슷한 구간의 GC 후 사용량을 비교한다. 사용량이 계속 증가하거나 특정 객체가 많이 남는다면, 덤프를 통해 그 객체를 참조하는 소유자를 좁힐 수 있다.

```sh
jcmd "$pid" GC.heap_dump "/var/lib/myapp/dumps/heap-$(date -u +%Y%m%dT%H%M%SZ).hprof"
```

기본 `GC.heap_dump`는 Full GC를 요청하며, 덤프 크기와 힙 내용에 따라 영향이 클 수 있다. JVM이 쓸 수 있는 경로와 충분한 디스크 공간을 확보한 뒤 수집한다. 덤프에는 메모리에 있던 요청 데이터나 설정 값이 들어갈 수 있으므로 열람과 보관 범위를 제한한다.

Eclipse MAT에서는 다음 순서로 읽는다.

1. **Histogram**으로 인스턴스 수가 많거나 메모리를 많이 쓰는 클래스를 찾는다.
2. **Dominator Tree**에서 retained heap이 큰 객체를 본다. Shallow heap은 객체 자체의 크기이며, retained heap은 해당 객체가 더 이상 도달 가능하지 않을 때 함께 회수될 객체를 포함한 크기다.
3. **Path to GC Roots**로 객체가 살아 있는 참조 경로를 추적한다. 예를 들어 정적 맵이 오래된 요청 데이터를 계속 붙잡고 있으면, 맵에 항목이 추가되고 제거되는 조건을 확인한다.

객체가 크다는 사실만으로 누수를 확정하기 어렵다. GC 후 사용량의 변화, 객체의 예상 수명, 덤프에서 확인한 참조 경로를 함께 비교한다.

**공식 문서** [JDK jcmd](https://docs.oracle.com/en/java/javase/21/docs/specs/man/jcmd.html) · [Eclipse MAT Shallow and Retained Heap](https://help.eclipse.org/latest/topic/org.eclipse.mat.ui.help/concepts/shallowretainedheap.html) · [Eclipse MAT Dominator Tree](https://help.eclipse.org/latest/topic/org.eclipse.mat.ui.help/concepts/dominatortree.html) · [Eclipse MAT Leak Suspects](https://help.eclipse.org/latest/topic/org.eclipse.mat.ui.help/tasks/runningleaksuspectreport.html)

## 5. 덤프와 오류 로그 자동 생성 설정하기

JVM을 시작할 때 OOM에서 생성할 Heap Dump와 복구 불가능한 JVM 오류에서 생성할 오류 로그의 경로를 지정한다.

```sh
java \
  -XX:+HeapDumpOnOutOfMemoryError \
  -XX:HeapDumpPath=/var/lib/myapp/dumps \
  -XX:ErrorFile=/var/lib/myapp/dumps/hs_err_pid%p.log \
  -jar app.jar
```

| 설정 또는 수집 트리거 | 결과 |
| --- | --- |
| `HeapDumpOnOutOfMemoryError`와 `HeapDumpPath` | JVM이 덤프 대상으로 처리한 OOM에서 Java 힙을 HPROF로 기록한다. |
| `ErrorFile` | JVM 자체의 치명 오류가 발생했을 때 오류 보고서의 경로를 지정한다. |
| 응답 정지나 타임아웃 경보 | JVM이 살아 있을 때 운영 도구에서 `jcmd`를 호출해 Thread Dump를 수집하도록 구성할 수 있다. 수집 간격과 횟수를 정해 반복 실행을 제한한다. |

예시 디렉터리는 시작 전에 만들고 JVM의 실행 사용자에게 쓰기 권한을 준다. `HeapDumpPath`에 기존 디렉터리를 지정하면 그 안에 `java_pid<PID>.hprof`가 생성된다. `ErrorFile`의 `%p`는 JVM이 PID로 바꾼다. 파일 이름 충돌 가능성, 디스크 용량과 보존 기간도 확인한다. 컨테이너가 강제 종료되면 JVM이 파일을 남길 시간 없이 종료될 수 있으므로, 종료 이유는 플랫폼 이벤트와 함께 확인한다.

**공식 문서** [JDK java 실행 옵션](https://docs.oracle.com/en/java/javase/21/docs/specs/man/java.html) · [Oracle JVM 진단 옵션 준비](https://docs.oracle.com/en/java/javase/21/troubleshoot/prepare-java-troubleshooting.html) · [JDK jcmd](https://docs.oracle.com/en/java/javase/21/docs/specs/man/jcmd.html)
