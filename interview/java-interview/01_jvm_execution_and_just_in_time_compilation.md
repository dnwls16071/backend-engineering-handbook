# JVM Execution and Just-in-Time Compilation

## 3. JVM의 장점과 단점은 무엇인가요?

**30–60초 답변**

> JVM의 장점은 같은 `.class` 파일을 호환되는 JVM이 있는 여러 운영체제와 CPU에서 실행할 수 있다는 점입니다. 가비지 컬렉션(GC)이 사용하지 않는 객체의 메모리를 회수하고, HotSpot은 실행 중에 수집한 정보를 바탕으로 자주 쓰는 코드를 최적화합니다. 그만큼 JVM 기동과 클래스 로딩, JIT 컴파일에 시간과 자원이 듭니다. 실행 중에는 GC의 CPU 사용량과 일시 정지, 클래스 메타데이터나 코드 캐시 같은 런타임 메모리도 고려해야 합니다. 짧게 실행되는 프로그램이면 시작 지연이, 장시간 실행되는 서버면 처리량과 응답 지연이 더 중요할 수 있습니다. [JVMS §2.5.3, §2.13](https://docs.oracle.com/javase/specs/jvms/se25/html/jvms-2.html) · [HotSpot 성능 최적화](https://docs.oracle.com/en/java/javase/25/vm/java-hotspot-virtual-machine-performance-enhancements.html) · [HotSpot GC 튜닝 가이드](https://docs.oracle.com/en/java/javase/25/gctuning/index.html)

**꼬리 질문 · 같은 JAR를 배포할 때 대상 환경에서 무엇을 확인하나요?**

우선 실행할 JDK가 JAR 안의 클래스 파일 버전과 사용하는 Java API를 지원하는지 확인합니다. 빌드에서 `javac --release 17`을 쓰면 해당 소스를 Java 17의 언어 규칙과 지원 API에 맞춰 컴파일하고 Java 17용 클래스 파일을 생성합니다. 의존 라이브러리의 요구 버전도 확인하고, JNI를 쓴다면 대상 운영체제와 CPU에 맞는 네이티브 라이브러리를 배포합니다. [Oracle `javac`의 `--release` 옵션](https://docs.oracle.com/en/java/javase/25/docs/specs/man/javac.html) · [JVMS §4.1 클래스 파일 버전](https://docs.oracle.com/javase/specs/jvms/se25/html/jvms-4.html#jvms-4.1) · [JNI 라이브러리 로딩](https://docs.oracle.com/en/java/javase/25/docs/specs/jni/design.html)

## 4. Java가 C나 C++보다 느릴 수 있는 이유는 무엇인가요?

**30–60초 답변**

> C나 C++을 미리 기계어로 컴파일해 배포했다면 실행 시 이미 생성된 기계어를 사용할 수 있습니다. 일반적인 HotSpot 실행에서는 JVM 초기화와 클래스 로딩이 필요하고, 자주 쓰는 경로가 최적화되기 전에는 인터프리터나 낮은 단계의 컴파일 코드로 실행됩니다. 그래서 짧게 끝나는 작업은 이 초기 비용의 영향을 크게 받습니다. 충분히 실행한 뒤에는 HotSpot이 실제 호출 패턴을 활용해 인라이닝 등을 적용할 수 있고, 객체 할당과 GC 비용은 워크로드에 따라 달라집니다. 어느 쪽이 빠른지는 같은 작업을 수행하는 두 구현의 시작 시간과 워밍업 이후 처리량·지연 시간을 각각 측정해서 판단합니다. [HotSpot의 계층형 컴파일과 최적화](https://docs.oracle.com/en/java/javase/25/vm/java-hotspot-virtual-machine-performance-enhancements.html) · [GCC 최적화 옵션](https://gcc.gnu.org/onlinedocs/gcc/Optimize-Options.html)

**꼬리 질문 · 두 구현의 HTTP 요청 처리 성능을 어떻게 비교하나요?**

같은 하드웨어에서 입력, 동시성, 응답 내용, 외부 시스템 조건을 맞추고 각 구현의 배포용 최적화 설정을 사용합니다. 새 프로세스의 첫 응답 시간과, 대표 트래픽을 충분히 흘린 뒤의 초당 처리량·p95/p99 지연 시간을 따로 기록합니다. 응답 시간 대부분이 DB 대기라면 요청 추적으로 DB 시간과 애플리케이션 내부 처리 시간을 구분해야 CPU 처리 성능 차이를 해석할 수 있습니다. [Oracle JFR 성능 진단 가이드](https://docs.oracle.com/en/java/javase/25/troubleshoot/troubleshoot-performance-issues-using-jfr.html)

## 5. Java 프로그램의 실행 과정을 설명해 주세요.

**30–60초 답변**

> 일반적인 빌드에서는 `javac`가 `.java` 소스를 바이트코드가 들어 있는 `.class` 파일로 컴파일합니다. `java`로 실행하면 JVM이 시작 클래스를 로딩하고 링크한 뒤 초기화해 `main` 메서드를 호출합니다. 링크에는 클래스 파일의 검증, 정적 필드에 기본값을 준비하는 작업, 심볼릭 참조의 해석이 포함됩니다. 참조 해석은 실제로 필요해질 때까지 늦출 수 있습니다. 클래스 초기화에서는 명시적인 정적 필드 초기화식과 `static` 블록을 실행합니다. 이후 필요한 클래스도 동적으로 로드되고, 일반적인 HotSpot에서는 인터프리터와 JIT로 생성한 기계어가 함께 사용됩니다. [Oracle `javac`](https://docs.oracle.com/en/java/javase/25/docs/specs/man/javac.html) · [JVMS §5 JVM 시작과 클래스 로딩·링크·초기화](https://docs.oracle.com/javase/specs/jvms/se25/html/jvms-5.html) · [Oracle `java`의 혼합 실행 모드](https://docs.oracle.com/en/java/javase/25/docs/specs/man/java.html)

**꼬리 질문 · `ClassLoader.loadClass()`를 호출하면 `static` 블록도 바로 실행되나요?**

`loadClass()`는 클래스 로딩을 요청합니다. 일반적인 클래스 초기화 시점은 첫 인스턴스를 생성하거나, 그 클래스가 선언한 정적 메서드를 호출하거나, 컴파일 타임 상수가 아닌 정적 필드에 접근할 때입니다. 리플렉션으로 초기화까지 요청하려면 `Class.forName(name, true, loader)`를 사용합니다. [JVMS §5.5 초기화 조건](https://docs.oracle.com/javase/specs/jvms/se25/html/jvms-5.html#jvms-5.5) · [Java SE `ClassLoader.loadClass`](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/lang/ClassLoader.html#loadClass(java.lang.String)) · [Java SE `Class.forName`](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/lang/Class.html#forName(java.lang.String,boolean,java.lang.ClassLoader))

## 6. 인터프리터와 JIT 컴파일러의 차이는 무엇인가요?

**30–60초 답변**

> 인터프리터는 바이트코드 명령을 실행할 때마다 해석하므로 해당 메서드의 기계어가 준비되기 전에도 실행을 시작할 수 있습니다. JIT 컴파일러는 실행 중에 메서드를 기계어로 변환하고, JVM은 생성된 코드를 재사용합니다. 컴파일에는 CPU와 코드 캐시가 필요하지만, 자주 실행되는 메서드는 해석 비용을 줄이고 인라이닝 같은 최적화의 효과를 반복해서 얻습니다. HotSpot의 계층형 컴파일에서는 C1이 빠르게 기계어를 생성하면서 프로파일을 수집할 수 있고, C2는 수집된 정보를 바탕으로 더 적극적으로 최적화할 수 있습니다. [HotSpot 계층형 컴파일](https://docs.oracle.com/en/java/javase/25/vm/java-hotspot-virtual-machine-performance-enhancements.html) · [Oracle HotSpot C1과 C2](https://docs.oracle.com/en/java/javase/11/jrockit-hotspot/compilation-optimization.html)

**꼬리 질문 · HotSpot에서 인터프리터만 사용하는 실행과 어떻게 비교할 수 있나요?**

같은 애플리케이션을 기본 혼합 모드와 `java -Xint ...`로 각각 실행하면 `-Xint` 실행에서는 Java 바이트코드를 인터프리터로만 처리합니다. 같은 입력으로 초기 지연과 반복 처리량을 측정하고, 기본 실행의 JFR 컴파일 이벤트를 함께 보면 성능이 언제 바뀌는지 확인할 수 있습니다. [Oracle `java`의 `-Xint`, `-Xmixed`](https://docs.oracle.com/en/java/javase/25/docs/specs/man/java.html) · [OpenJDK JDK 25 JFR 이벤트 정의](https://github.com/openjdk/jdk/blob/jdk-25-ga/src/hotspot/share/jfr/metadata/metadata.xml)

## 7. JIT 컴파일러는 자주 실행되는 코드를 어떻게 찾나요?

**30–60초 답변**

> HotSpot은 메서드 진입 횟수를 세는 호출 카운터와 루프에서 앞선 바이트코드 위치로 되돌아가는 분기 횟수를 세는 백에지 카운터를 사용합니다. 계층형 컴파일 정책은 이 카운터가 각 단계의 조건을 만족할 때 컴파일을 요청할 수 있습니다. 백에지가 반복되는 긴 루프라면 메서드가 실행 중인 상태에서 해당 지점에 맞게 컴파일된 코드로 이어갈 수 있는데, 이를 OSR(On-Stack Replacement)이라고 합니다. 실제 임계값은 컴파일 단계와 JVM 설정에 따라 달라지고, HotSpot은 컴파일 큐 부하에 맞춰 임계값을 조정할 수도 있습니다. [OpenJDK JDK 25 HotSpot 컴파일 정책](https://github.com/openjdk/jdk/blob/jdk-25-ga/src/hotspot/share/compiler/compilationPolicy.hpp) · [OpenJDK JDK 25 HotSpot 인터프리터의 OSR 진입 처리](https://github.com/openjdk/jdk/blob/jdk-25-ga/src/hotspot/share/interpreter/interpreterRuntime.cpp)

**꼬리 질문 · 메서드를 한 번만 호출했는데도 루프가 JIT 컴파일될 수 있나요?**

가능합니다. 한 번의 호출로도 루프의 백에지 카운터가 충분히 증가하고 OSR용 코드가 준비되면, 현재 실행 상태를 이어받아 루프의 남은 부분을 기계어로 실행할 수 있습니다. JFR에서 `jdk.Compilation` 이벤트를 기록해 해당 메서드의 `isOsr` 값과 컴파일 단계를 확인할 수 있습니다. [OpenJDK JDK 25 HotSpot 컴파일 정책](https://github.com/openjdk/jdk/blob/jdk-25-ga/src/hotspot/share/compiler/compilationPolicy.hpp) · [OpenJDK JDK 25 JFR의 `Compilation` 이벤트](https://github.com/openjdk/jdk/blob/jdk-25-ga/src/hotspot/share/jfr/metadata/metadata.xml)

## 8. JIT 코드 캐시가 가득 차면 어떤 일이 발생하나요?

**30–60초 답변**

> HotSpot의 코드 캐시는 JIT가 생성한 기계어와 JVM 내부 실행 코드를 저장하는 영역입니다. 새 코드를 할당할 공간을 확보하지 못하면 HotSpot은 새 JIT 컴파일을 중단할 수 있습니다. 유효한 기존 컴파일 코드는 계속 사용할 수 있고, 아직 컴파일되지 않은 경로는 인터프리터로 실행돼 처리량이나 응답 지연에 영향을 줄 수 있습니다. 예를 들어 HotSpot JDK 25에서는 코드 캐시 플러싱이 켜져 있으면 공간을 회수한 뒤 새 컴파일을 재개할 수 있습니다. 운영 중에는 경고가 발생한 시각과 `jcmd <PID> Compiler.codecache`의 사용량·컴파일 상태를 확인합니다. [HotSpot 코드 캐시 구조](https://docs.oracle.com/en/java/javase/25/vm/java-hotspot-virtual-machine-performance-enhancements.html) · [OpenJDK JDK 25 컴파일 중단 처리](https://github.com/openjdk/jdk/blob/jdk-25-ga/src/hotspot/share/compiler/compileBroker.cpp) · [OpenJDK JDK 25 컴파일 재개 처리](https://github.com/openjdk/jdk/blob/jdk-25-ga/src/hotspot/share/code/codeCache.cpp) · [Oracle `jcmd`](https://docs.oracle.com/en/java/javase/25/docs/specs/man/jcmd.html)

**꼬리 질문 · 전체 코드 캐시에 여유 공간이 있어 보이면 무엇을 확인하나요?**

HotSpot은 JDK 9부터 분할 코드 캐시를 지원합니다. 분할이 활성화된 경우 `non-method`, `profiled`, `non-profiled` 코드 힙별 사용량과 여유 공간을 확인합니다. `jcmd <PID> Compiler.codecache`와 JVM 경고, 기록을 켠 경우 JFR의 `jdk.CodeCacheFull`·`jdk.JITRestart` 이벤트를 응답 지연이 늘어난 시점과 대조합니다. 포화가 반복되면 `Compiler.CodeHeap_Analytics`로 사용 공간과 빈 공간을 살펴보고, 필요하면 `-XX:ReservedCodeCacheSize`나 해당 코드 힙 크기 옵션을 검토합니다. [Oracle JDK 9 변경 사항](https://docs.oracle.com/javase/9/whatsnew/) · [Oracle `jcmd` 진단 명령](https://docs.oracle.com/en/java/javase/25/docs/specs/man/jcmd.html) · [Oracle `java` 코드 캐시 옵션](https://docs.oracle.com/en/java/javase/25/docs/specs/man/java.html) · [OpenJDK JDK 25 JFR 이벤트 정의](https://github.com/openjdk/jdk/blob/jdk-25-ga/src/hotspot/share/jfr/metadata/metadata.xml)

## 9. JVM 서버를 배포한 직후에 요청이 느린 이유는 무엇인가요?

**30–60초 답변**

> 새 인스턴스의 첫 요청에서 해당 경로의 클래스를 처음 로딩하고 초기화할 수 있습니다. 자주 쓰는 경로도 아직 충분히 프로파일링되거나 JIT로 최적화되지 않았을 수 있습니다. 같은 요청에서 DB 풀의 첫 연결이나 캐시 채우기 같은 애플리케이션 초기화 비용도 발생할 수 있습니다. 원인을 확인하려면 새 인스턴스의 엔드포인트별 지연이 언제 안정되는지 보고, 같은 구간의 JFR 클래스 로딩·컴파일·GC 기록과 요청 추적의 외부 호출 시간을 대조합니다. 대표 경로를 미리 실행해 필요한 준비를 마친 뒤 새 인스턴스로 보내는 트래픽을 점진적으로 늘릴 수 있습니다. [HotSpot 계층형 컴파일](https://docs.oracle.com/en/java/javase/25/vm/java-hotspot-virtual-machine-performance-enhancements.html) · [Oracle JFR 진단 도구](https://docs.oracle.com/en/java/javase/25/troubleshoot/diagnostic-tools.html) · [Kubernetes의 readiness probe](https://kubernetes.io/docs/concepts/workloads/pods/probes/#readiness-probe)

**꼬리 질문 · 헬스 체크가 통과했는데 주문 조회만 느리면 어떻게 확인하나요?**

배포 직후 새 인스턴스에서 부작용 없는 대표 주문 조회를 반복하고, 첫 요청부터 안정화될 때까지 응답 시간과 DB 풀 대기·쿼리 시간을 기록합니다. 다음 재현에서는 `-XX:StartFlightRecording`으로 시작 시점부터 수집해 지연 구간에서 클래스 로딩과 컴파일이 얼마나 발생하는지 확인합니다. 예를 들어 첫 요청에서 DB 연결 시간이 대부분이라면 연결 풀 준비를 조정한 뒤 같은 부하에서 초기 p95/p99가 개선됐는지 비교합니다. [Oracle `java`의 `StartFlightRecording` 옵션](https://docs.oracle.com/en/java/javase/25/docs/specs/man/java.html) · [Oracle JFR 성능 진단 가이드](https://docs.oracle.com/en/java/javase/25/troubleshoot/troubleshoot-performance-issues-using-jfr.html)
