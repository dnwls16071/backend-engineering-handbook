# Java Resource Performance Tuning

Java 리소스 튜닝은 느린 요청이 CPU 계산, 객체 할당, GC, I/O 대기 중 어디에서 시간을 쓰는지 구분하는 데서 시작한다. 같은 입력과 동시성으로 변경 전후의 처리량, p95 응답 시간, 리소스 사용량을 비교한다. 여기서는 JDK 21과 HotSpot을 기준으로 설명한다.

## 1. JMX 설정과 리소스 모니터링

JVM은 플랫폼 MXBean을 통해 힙과 비힙 메모리, GC, 스레드 등의 상태를 노출한다. JConsole은 JDK에 포함된 GUI 도구다. 로컬 연결이 허용된 환경에서 대상 JVM과 같은 호스트에서 같은 OS 사용자로 실행하면 로컬 JVM 목록에서 프로세스를 선택할 수 있다. PID를 이미 알면 `jconsole <pid>` 형식으로 바로 연결한다.

| 확인할 항목 | 해석 |
| --- | --- |
| 힙의 `used`, `committed`, `max` | 현재 쓰는 양, JVM이 이미 사용 가능하도록 확보한 양, 사용할 수 있는 상한이다. 일부 메모리 영역의 상한은 정의되지 않아 `-1`로 표시될 수 있다. |
| GC 횟수와 시간 | 누적 값의 구간별 차이를 비교한다. GC 시간은 개별 요청의 지연이나 특정 GC의 최대 정지 시간과 구분해서 본다. |
| 스레드 수와 상태 | 요청 지연이 늘어난 시간대에 스레드 수와 상태를 확인한다. `BLOCKED`가 많으면 스택을 보고 어떤 모니터 락을 기다리는지 좁힌다. |

원격 연결이 필요하면 JMX 에이전트에 포트를 지정하고, 허용된 관리 네트워크에서 TLS와 인증을 사용한다. 읽기 전용 모니터링 권한으로 연결하는 구성을 우선한다. JMX로 이상이 발생한 시간과 리소스를 찾은 뒤, 원인 코드가 필요하면 JFR로 그 구간을 기록한다.

**공식 문서** [JDK jconsole](https://docs.oracle.com/en/java/javase/21/docs/specs/man/jconsole.html) · [JMX 모니터링 및 관리](https://docs.oracle.com/en/java/javase/21/management/monitoring-and-management-using-jmx-technology.html) · [MemoryUsage](https://docs.oracle.com/en/java/javase/21/docs/api/java.management/java/lang/management/MemoryUsage.html)

## 2. 메서드 사용 시 주의할 점

메서드 호출을 줄이기 전에 메서드가 호출될 때마다 무엇을 하는지 본다. 반복문 안의 메서드가 매번 DB를 조회하거나 큰 컬렉션을 복사한다면 호출 횟수와 실제 작업량이 함께 늘어난다. 예를 들어 주문 100건의 고객 정보를 건별 조회한다면, 조회가 병목인지 측정한 뒤 고유 ID를 모아 한 번에 조회할 수 있는지 검토한다. 배치로 바꾸면 결과 매핑과 실패 처리도 확인한다.

- HotSpot은 실행 중 수집한 프로파일을 바탕으로 메서드를 최적화한다. 인라이닝은 호출 경계의 비용을 줄일 수 있고, Escape Analysis가 가능한 경우 일부 객체 할당을 제거할 수 있다. 코드만 보고 호출 비용이나 할당량을 단정하기 어렵다.
- 운영 코드의 병목은 JFR의 실행 샘플, 할당, 락 대기 이벤트로 좁힌다. 작은 메서드의 차이를 따로 검증할 때는 JMH에서 워밍업과 JVM 포크를 두고, 계산 결과를 반환하거나 `Blackhole`에 전달해 사용되지 않는 계산이 제거되는 상황을 피한다.
- 시작 지연과 워밍업 이후 처리량은 각각 측정한다. 한 경로의 호출을 줄였다면 전체 요청 시간, I/O 횟수, 요청당 할당량도 함께 비교한다.

```sh
jcmd "$pid" JFR.start name=tuning settings=profile duration=60s filename=tuning.jfr
```

`pid`에는 관측할 JVM의 PID를 넣는다. 기록 경로는 대상 JVM이 쓸 수 있는 위치로 지정한다. `profile`은 비교적 상세한 기록이 필요할 때 짧은 구간에 사용한다.

**공식 문서** [HotSpot 성능 최적화](https://docs.oracle.com/en/java/javase/21/vm/java-hotspot-virtual-machine-performance-enhancements.html) · [OpenJDK JMH 예제](https://github.com/openjdk/jmh/tree/master/jmh-samples) · [JDK jcmd](https://docs.oracle.com/en/java/javase/21/docs/specs/man/jcmd.html)

## 3. `static`의 잘못된 사용 피하기

`static` 필드는 클래스에 속하며 인스턴스마다 복제되지 않는다. 상수나 불변 값을 공유하거나 인스턴스 상태가 필요 없는 메서드를 정의하는 데 쓸 수 있다. 공유 데이터를 수정하거나 오래 보관할 때는 동시성과 데이터 수명을 함께 설계한다.

- `static final Map<K, V>`에서 `final`은 필드의 재할당을 막는다. 맵이 가변이면 항목은 여전히 변경할 수 있다. 공유 맵에서 `containsKey`와 `put`을 따로 호출하면 두 동작 사이에 다른 스레드가 끼어들 수 있다. `ConcurrentHashMap.computeIfAbsent`는 이 키의 조회와 삽입을 조율하며, 매핑 함수가 오래 걸리면 다른 갱신이 대기할 수 있다.
- 오래 살아 있는 클래스의 정적 컬렉션에 객체를 계속 추가하면 해당 객체도 계속 참조된다. 같은 부하에서 GC 후 힙 사용량이 꾸준히 높아진다면 컬렉션의 크기, 항목 제거 조건, 객체의 참조 경로를 확인한다.
- 정적 초기화에서 파일이나 네트워크를 읽으면 시작 시간 또는 클래스가 처음 사용되는 요청의 지연으로 나타날 수 있다. 요청별 상태에는 요청 범위를 사용하고, 전역 캐시에는 용량 상한과 만료 조건을 둔다.

**공식 문서** [JLS 정적 필드와 final 필드](https://docs.oracle.com/javase/specs/jls/se21/html/jls-8.html#jls-8.3.1) · [JLS 클래스 초기화](https://docs.oracle.com/javase/specs/jls/se21/html/jls-12.html#jls-12.4) · [ConcurrentHashMap](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/concurrent/ConcurrentHashMap.html)

## 4. 큰 클래스의 코드 분할하기

코드가 길다면 책임과 I/O 경계를 찾아 나눈다. 예를 들어 주문 처리 클래스에서 입력 변환은 `OrderParser`, 업무 규칙은 `OrderValidator`, 원본 저장은 `OrderRepository`로 나누고 서비스에서 처리 순서를 조율할 수 있다. 파싱의 CPU와 할당량, 저장의 호출 횟수와 대기 시간을 따로 확인하기 쉬워진다.

- 클래스 분할은 구조를 개선하는 작업이다. 성능은 분리 전후에 추가된 복사, 중간 컬렉션, 외부 호출을 실제로 측정해 판단한다.
- JVM 명세의 `code_length < 65536` 제한은 메서드 하나의 바이트코드에 적용된다. 생성 코드나 큰 초기화 블록이 이 한도에 닿았다면 클래스의 소스 줄 수를 줄이는 것보다 생성되는 메서드의 본문을 나누는 작업이 필요하다.
- `jdeps -verbose:class -filter:none app.jar`로 컴파일된 클래스 간 의존성을 확인할 수 있다. 호출 빈도와 실행 시간은 JFR 같은 런타임 측정으로 확인한다.

**공식 문서** [JVM 명세의 Code 속성](https://docs.oracle.com/javase/specs/jvms/se21/html/jvms-4.html#jvms-4.7.3) · [JDK jdeps](https://docs.oracle.com/en/java/javase/21/docs/specs/man/jdeps.html) · [JDK jcmd](https://docs.oracle.com/en/java/javase/21/docs/specs/man/jcmd.html)

## 5. 디자인 패턴으로 비용 줄이기

프로파일에서 비용의 원인을 찾은 뒤, 그 비용을 줄일 수 있는 패턴을 선택한다.

| 관찰한 비용 | 적용할 수 있는 패턴 | 확인할 지표 |
| --- | --- | --- |
| 같은 불변 데이터가 요청마다 생성됨 | Flyweight로 공통 인스턴스 공유 | 요청당 할당량, 공유 테이블 크기 |
| 거의 사용하지 않는 구성 요소가 시작 시간을 늘림 | Lazy Initialization으로 첫 사용 시점에 초기화 | 시작 시간, 첫 호출 지연 |
| 같은 입력으로 비싼 계산을 반복함 | Memoization으로 결과 재사용 | 히트율, 캐시 크기, 부하 시 지연 |

불변 데이터를 공유할 때 `List.copyOf`로 목록 자체의 변경을 막을 수 있지만, 가변 원소는 별도로 관리한다. 지연 초기화는 작업을 첫 사용 시점으로 옮기므로 첫 요청 비용과 실패 처리도 측정한다. 결과 캐싱은 키가 계속 늘거나 원본이 바뀔 수 있을 때 용량 상한과 무효화 규칙이 필요하다.

**공식 문서** [Java List의 변경 불가 목록](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/List.html) · [JLS 초기화 시점](https://docs.oracle.com/javase/specs/jls/se21/html/jls-12.html#jls-12.4) · [ConcurrentHashMap](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/concurrent/ConcurrentHashMap.html)

## 6. 파일을 효율적으로 읽기

파일의 크기와 형식, 필요한 접근 단위에 맞춰 API를 선택한다. 한 번에 처리해야 할 데이터만 메모리에 보관한다.

| 상황 | 방법 |
| --- | --- |
| 작고 크기가 제한된 파일 전체가 필요함 | 텍스트는 `readString`, 바이너리는 `readAllBytes` |
| 큰 텍스트를 줄 단위로 처리함 | `newBufferedReader`와 `readLine`, 또는 `Files.lines` |
| 큰 바이너리를 순차 처리함 | `InputStream.read(byte[])`로 읽은 바이트 수만큼 처리 |

`Files.lines`는 줄을 지연해서 읽지만, 스트림이 열려 있는 동안 파일도 열린다. try-with-resources로 닫고, 인코딩은 파일의 실제 형식에 맞춘다. `toList()`처럼 처리 결과를 모두 모으거나 한 줄 자체가 매우 길면 스트리밍 방식에서도 메모리 사용량이 커질 수 있다.

```java
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;

class LogScan {
    static long countErrors(Path path) throws IOException {
        try (var lines = Files.lines(path, StandardCharsets.UTF_8)) {
            return lines.filter(line -> line.startsWith("ERROR ")).count();
        }
    }
}
```

**공식 문서** [Java Files](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/nio/file/Files.html) · [BufferedReader](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/io/BufferedReader.html) · [InputStream](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/io/InputStream.html)

## 7. 최대 힙 메모리를 늘리면 좋은 경우

`-Xmx`는 Java 힙의 상한이고, `-Xms`는 초기·최소 힙 크기를 설정한다. 부하가 몰리는 동안 생존 객체와 새로 할당될 객체가 힙에 들어갈 여유가 부족하면, 상한을 높여 할당 여유를 확보하고 GC 빈도나 GC에 쓰는 시간을 줄일 수 있다. 효과는 수집기, 객체 수명, 할당 속도에 따라 달라진다.

| 관찰한 상태 | 확인할 조치 |
| --- | --- |
| GC 후 사용량은 비슷한 수준으로 돌아오지만 피크에 힙 상한 근처에서 GC가 잦음 | 운영 환경에 메모리 여유가 있을 때 `-Xmx`를 높여 같은 부하로 비교한다. |
| 비슷한 부하에서 GC 후 사용량이 계속 올라감 | 오래 유지되는 객체나 캐시의 참조 경로를 조사한다. 힙 증설은 문제 발생 시점을 늦출 수 있다. |
| 힙은 안정적인데 프로세스 메모리가 환경 한도에 접근함 | Metaspace, 스레드 스택, 코드 캐시, 직접 버퍼 등 힙 외 사용량을 살핀다. |

```sh
java -Xms512m -Xmx2g -Xlog:gc*:file=gc.log:time,uptime,level,tags -jar app.jar
```

위 수치는 실행 예시다. 실제 상한은 대표 부하에서 GC 후 사용량, GC 횟수와 정지 시간 분포, 처리량과 응답 지연을 보고 정한다. `-Xmx`를 호스트나 컨테이너 메모리 한도와 같게 잡으면 힙 외 메모리의 여유가 줄어든다. JVM 내부 네이티브 사용량이 필요하면 시작 시 `-XX:NativeMemoryTracking=summary`를 켜고 `jcmd "$pid" VM.native_memory summary`로 본다. NMT의 집계 범위와 프로세스 전체 메모리 사용량을 함께 확인한다.

**공식 문서** [JDK java 실행 옵션](https://docs.oracle.com/en/java/javase/21/docs/specs/man/java.html) · [G1 GC 튜닝](https://docs.oracle.com/en/java/javase/21/gctuning/garbage-first-garbage-collector-tuning.html) · [Java 메모리 누수 진단](https://docs.oracle.com/en/java/javase/21/troubleshoot/troubleshooting-memory-leaks.html) · [Native Memory Tracking](https://docs.oracle.com/en/java/javase/21/vm/native-memory-tracking.html)
