# Garbage Collection and Memory Diagnostics

## 11. 가비지 컬렉션 알고리즘에는 어떤 것들이 있나요?

**30–60초 답변**

> JVM 명세는 수집 알고리즘을 구현에 맡깁니다. HotSpot의 대표적인 수집기는 GC 루트에서 참조를 따라가며 살아 있는 객체를 찾는 추적 방식(tracing)을 사용합니다. Mark-Sweep은 살아 있는 객체를 표시한 뒤 나머지 객체의 공간을 회수해서 빈 공간이 흩어질 수 있습니다. Mark-Compact는 살아 있는 객체를 옮겨 빈 공간을 모으므로 단편화를 줄이는 대신 이동과 참조 갱신 비용이 듭니다. 복사 방식은 살아 있는 객체만 다른 공간으로 옮기고 원래 공간을 통째로 재사용합니다. 살아남는 객체가 적을 때 효율적이고, 옮길 대상 공간이 필요합니다. HotSpot은 수집기와 수집 단계에 따라 이 방식들을 조합합니다. 예를 들어 G1은 동시 마킹으로 생존 정보를 얻고, 선택한 영역에서 살아 있는 객체를 복사해 공간을 회수합니다. [JVM 명세 §2.5.3](https://docs.oracle.com/javase/specs/jvms/se8/html/jvms-2.html#jvms-2.5.3) · [Java 8 세대별 수집](https://docs.oracle.com/javase/8/docs/technotes/guides/vm/gctuning/generations.html) · [Java 8 CMS](https://docs.oracle.com/javase/8/docs/technotes/guides/vm/gctuning/cms.html) · [Java 11 G1](https://docs.oracle.com/en/java/javase/11/gctuning/garbage-first-g1-garbage-collector3.html)

**꼬리 질문 · 두 객체가 서로를 참조하면 GC가 회수할 수 있나요?**

두 객체로 이어지는 경로가 GC 루트에서 끊겼다면 회수 대상이 됩니다. 예를 들어 서로를 가리키는 노드 두 개를 만들고 외부에서 두 노드로 이어지는 참조가 모두 사라지면 추적 대상에서 빠집니다. 단순 참조 카운팅에서는 두 노드의 참조 수가 각각 1로 남으므로 순환을 별도로 처리해야 합니다. [Java 8 객체 도달 가능성과 세대별 수집](https://docs.oracle.com/javase/8/docs/technotes/guides/vm/gctuning/generations.html)

## 12. Java 8의 힙은 어떻게 구성되며 GC는 언제 일어나나요?

**30–60초 답변**

> Java 8 HotSpot의 Parallel GC를 예로 들면 힙은 Young과 Old 세대로 나뉘고, Young은 Eden과 두 Survivor 공간으로 구성됩니다. 대부분의 새 객체는 Eden에 할당됩니다. Eden에 새 객체를 할당할 공간이 부족하면 Young GC가 일어나고, 살아남은 객체를 다음 Survivor 공간으로 복사하거나 GC 생존 횟수와 공간 여유에 따라 Old로 승격합니다. Old에 승격할 공간을 확보하지 못하면 Full GC가 발생할 수 있습니다. CMS나 G1은 점유율과 같은 조건을 보고 공간이 고갈되기 전에 동시 수집 사이클을 시작할 수 있습니다. Java 8에서 PermGen이 제거되면서 클래스 메타데이터는 Java 힙 바깥의 네이티브 메모리인 Metaspace에 저장됩니다. [Java 8 세대별 수집](https://docs.oracle.com/javase/8/docs/technotes/guides/vm/gctuning/generations.html) · [Java 8 Parallel GC](https://docs.oracle.com/javase/8/docs/technotes/guides/vm/gctuning/parallel.html) · [Java 8 CMS 수집 시작 조건](https://docs.oracle.com/javase/8/docs/technotes/guides/vm/gctuning/cms.html) · [Java 8 G1 튜닝](https://docs.oracle.com/javase/8/docs/technotes/guides/vm/gctuning/g1_gc_tuning.html) · [PermGen 제거](https://docs.oracle.com/en/java/javase/25/gctuning/other-considerations.html)

**꼬리 질문 · 힙에 여유가 있는데도 클래스 로딩 때문에 GC가 발생할 수 있나요?**

발생할 수 있습니다. HotSpot은 클래스 메타데이터에 커밋한 메모리가 일정 임계값에 도달하면 GC를 유도해 클래스 언로딩으로 공간을 확보할 기회를 얻습니다. 살아 있는 클래스 로더가 계속 늘어난다면 Metaspace 사용량도 쌓일 수 있으므로, 로드된 클래스 수와 클래스 로더의 생존 경로를 함께 확인합니다. [Oracle 클래스 메타데이터 관리](https://docs.oracle.com/en/java/javase/25/gctuning/other-considerations.html) · [Oracle 메모리 누수 진단](https://docs.oracle.com/en/java/javase/11/troubleshoot/troubleshooting-memory-leaks.html)

## 13. GC에서 Root Space는 무엇인가요?

**30–60초 답변**

> 여기서 Root Space는 객체 그래프를 탐색할 때 출발점이 되는 GC 루트 집합(root set)을 뜻합니다. 루트 참조는 실행 스택이나 JVM 내부의 참조 테이블처럼 여러 곳에 분포합니다. 실행 중인 스레드의 스택 프레임에 남아 있는 유효한 객체 참조나 JNI의 강한 전역 참조가 예입니다. 살아 있는 클래스의 `static` 필드가 가리키는 객체도 클래스 쪽 참조 경로를 통해 도달할 수 있습니다. GC는 이 출발점에서 참조를 따라가며 어떤 객체를 유지할지 판단합니다. [HotSpot 힙 덤프의 루트 집합](https://docs.oracle.com/javase/7/docs/webnotes/tsg/TSG-VM/html/tooldescr.html) · [JNI 전역·지역 참조](https://docs.oracle.com/javase/8/docs/technotes/guides/jni/spec/functions.html#global_and_local_references)

**꼬리 질문 · 메서드가 끝났는데 그 메서드에서 만든 객체가 힙 덤프에 남아 있으면 무엇을 보나요?**

힙 덤프에서 해당 객체까지 이어지는 강한 참조 경로를 루트 쪽으로 추적합니다. 예를 들어 오래 살아 있는 클래스의 `static` 캐시에 객체를 넣고 제거하지 않았다면, 메서드가 반환돼도 캐시를 통해 객체에 도달할 수 있습니다. 객체를 붙잡는 컬렉션과 그 컬렉션을 유지하는 소유자를 확인하면 어떤 참조를 정리해야 할지 판단할 수 있습니다. [HotSpot 루트 참조 체인 조회](https://docs.oracle.com/javase/7/docs/webnotes/tsg/TSG-VM/html/tooldescr.html) · [Oracle 메모리 누수 진단](https://docs.oracle.com/en/java/javase/11/troubleshoot/troubleshooting-memory-leaks.html)

## 14. 힙을 Young과 Old 세대로 나누는 이유는 무엇인가요?

**30–60초 답변**

> 약한 세대 가설(weak generational hypothesis)은 많은 프로그램에서 대부분의 객체가 생성된 뒤 짧은 시간 안에 도달 불가능해진다는 경험적 관찰입니다. 예를 들어 요청을 처리하면서 만든 임시 객체는 요청이 끝나면 빠르게 사라지는 반면, 설정이나 캐시는 오래 살아남을 수 있습니다. 세대별 GC는 새 객체가 모인 Young을 자주 수집하고 오래 살아남은 객체를 Old로 승격합니다. Young에서 대부분의 객체가 이미 죽었다면 살아 있는 소수 객체만 복사해 넓은 공간을 빠르게 회수할 수 있습니다. 반대로 Young 수집 때 살아남는 객체가 많아지면 복사와 승격 비용도 커집니다. [Java 8 객체 수명 분포와 세대별 수집](https://docs.oracle.com/javase/8/docs/technotes/guides/vm/gctuning/generations.html)

**꼬리 질문 · Old에서 Young을 참조하면 Young만 수집할 때 놓치지 않나요?**

Young 바깥에서 Young을 가리킬 수 있는 위치도 탐색의 출발점에 포함합니다. 예를 들어 G1은 쓰기 배리어로 참조 변경을 기록하고, remembered set을 이용해 수집 대상 리전으로 들어오는 참조를 찾습니다. 오래된 캐시가 방금 생성한 객체를 담았을 때도 이 경로를 따라가 새 객체를 살려 두고, 이동했다면 참조를 갱신할 수 있습니다. [Java 8 G1의 쓰기 배리어와 remembered set](https://docs.oracle.com/javase/8/docs/technotes/guides/vm/gctuning/g1_gc_tuning.html) · [Java 11 G1의 remembered set](https://docs.oracle.com/en/java/javase/11/gctuning/garbage-first-garbage-collector-tuning1.html)

## 15. Stop-the-World는 무엇이고 왜 발생하나요?

**30–60초 답변**

> Stop-the-World(STW)는 JVM이 애플리케이션의 Java 실행을 일시 정지하고, 참조를 안전하게 다룰 수 있는 상태(safepoint)에서 작업을 수행하는 구간입니다. 참조가 바뀌지 않는 상태에서 루트를 확인하거나 객체를 이동시키고 참조를 갱신할 수 있습니다. Parallel GC는 여러 GC 스레드가 함께 일하는 동안 애플리케이션을 멈춥니다. G1은 전역 마킹의 상당 부분을 애플리케이션 실행과 겹쳐 처리하고, 마킹을 마무리하는 Remark와 Young·Mixed 수집에서 객체를 옮기는 단계에는 STW가 있습니다. 병렬(parallel)은 여러 작업 스레드를 사용한다는 뜻이고, 동시(concurrent)는 해당 GC 작업을 애플리케이션 실행과 겹쳐 수행한다는 뜻입니다. [Java 8 Parallel GC](https://docs.oracle.com/javase/8/docs/technotes/guides/vm/gctuning/parallel.html) · [Java 11 G1 수집 단계](https://docs.oracle.com/en/java/javase/11/gctuning/garbage-first-g1-garbage-collector3.html)

**꼬리 질문 · 응답 지연이 급증했을 때 STW를 어떻게 확인하나요?**

요청 지연과 GC 로그의 `Pause` 시작 시각과 지속 시간을 맞춰 봅니다. Java 11에서는 `-Xlog:gc*,safepoint`로 GC 단계와 safepoint 기록을 함께 볼 수 있습니다. GC pause가 짧아도 safepoint에 진입하는 데 오래 걸리거나 다른 VM 작업이 앱을 멈췄을 수 있으므로 safepoint 로그도 확인합니다. 동시 GC 구간의 지연은 같은 시간대의 CPU 포화 여부를 함께 봅니다. [Java 11 통합 로깅](https://docs.oracle.com/en/java/javase/11/tools/java.html) · [동시 수집과 CPU 사용](https://docs.oracle.com/javase/8/docs/technotes/guides/vm/gctuning/cms.html)

## 16. Java의 GC 종류와 각각의 장단점은 무엇인가요?

**30–60초 답변**

> HotSpot의 Serial GC는 한 스레드로 수집해 스레드 간 조율 비용이 작고, 작은 힙이나 CPU가 적은 환경에 적합합니다. Parallel GC는 멈춘 동안 여러 스레드로 수집해 처리량을 높이는 데 유리하지만 살아 있는 객체가 많은 큰 힙에서는 정지가 길어질 수 있습니다. CMS는 Old의 마킹과 회수를 주로 동시에 수행해 정지를 줄이지만, 평상시 압축 없이 회수해 단편화가 쌓일 수 있습니다. G1은 동시 마킹과 리전 단위 객체 이동으로 정지 시간을 관리하고, 동시 작업과 참조 추적에 CPU·메모리를 사용합니다. ZGC와 Shenandoah는 객체 이동도 동시 수행해 더 짧은 정지를 목표로 하며, 지원 여부는 JDK 버전과 배포판에 따라 달라집니다. [Java 8 수집기 비교](https://docs.oracle.com/javase/8/docs/technotes/guides/vm/gctuning/collectors.html) · [Java 11 G1 비교](https://docs.oracle.com/en/java/javase/11/gctuning/garbage-first-g1-garbage-collector3.html) · [Oracle JDK 15의 저지연 수집기](https://blogs.oracle.com/java/the-arrival-of-java-15)

**꼬리 질문 · Java 11에서 지연이 길어 GC를 바꾸려면 무엇을 비교하나요?**

먼저 정확한 JDK 배포판과 버전에서 지원하는 GC를 확인합니다. CMS는 Java 11에서 사용할 수 있지만 Java 14에서 제거됐습니다. ZGC는 JDK 11에 Linux/x64 대상 실험 기능으로 들어왔고, Shenandoah는 Red Hat OpenJDK 11처럼 별도 지원하는 배포판이 있습니다. 같은 부하와 CPU·메모리 제한에서 요청 p99, 처리량, GC 정지 시간, CPU와 RSS를 함께 비교합니다. [Oracle JDK 11 릴리스 노트](https://www.oracle.com/java/technologies/javase/11-relnote-issues.html) · [Oracle JDK 14 CMS 제거](https://www.oracle.com/java/technologies/javase/14all-relnotes.html) · [Red Hat OpenJDK 11 Shenandoah](https://docs.redhat.com/en/documentation/red_hat_build_of_openjdk/11/html/using_shenandoah_garbage_collector_with_red_hat_build_of_openjdk_11/running-application-with-shenandoah-gc)

## 17. Java 8과 Java 11의 기본 GC는 무엇이고 왜 달라졌나요?

**30–60초 답변**

> 서버급으로 판정된 HotSpot 환경에서 GC를 명시하지 않으면 Java 8은 Parallel GC, Java 11은 G1 GC가 기본입니다. 이 변경은 JEP 248이 적용된 Java 9부터 시작됐습니다. 응답이 오래 멈추는 일을 줄이기 위해 G1을 기본으로 채택했습니다. 자원이 적어 서버급으로 판정되지 않는 환경에서는 Serial GC가 선택될 수 있고, `-XX:+UseParallelGC`처럼 GC를 명시한 실행 옵션이나 JVM 배포판과 빌드에 따라서도 실제 선택이 달라집니다. [Java 8 기본값 선택](https://docs.oracle.com/javase/8/docs/technotes/guides/vm/gctuning/ergonomics.html) · [JDK 9 릴리스 노트의 JEP 248](https://docs.oracle.com/javase/9/whatsnew/toc.htm) · [OpenJDK 11u 기본 GC 선택 코드](https://github.com/openjdk/jdk11u/blob/master/src/hotspot/share/gc/shared/gcConfig.cpp#L100-L114)

**꼬리 질문 · 컨테이너에서 지금 실행 중인 JVM의 GC를 어떻게 확인하나요?**

같은 컨테이너의 JVM에 `jcmd <pid> VM.flags`를 실행해 실제 `UseG1GC`, `UseParallelGC`, `UseSerialGC` 옵션을 확인합니다. Java 11에서 시작 시 `-Xlog:gc`를 켜 두었다면 `Using G1` 같은 메시지도 확인할 수 있습니다. 컨테이너의 CPU·메모리 제한이나 배포 시 주입된 JVM 옵션에 따라 로컬과 같은 JDK 버전에서도 선택이 달라질 수 있습니다. [Java 11 `jcmd`](https://docs.oracle.com/en/java/javase/11/tools/jcmd.html) · [Java 11 `java` 옵션과 컨테이너 지원](https://docs.oracle.com/en/java/javase/11/tools/java.html)

## 18. G1 GC는 어떻게 동작하나요?

**30–60초 답변**

> G1은 힙을 같은 크기의 리전(region)으로 나누고 리전마다 Eden, Survivor, Old 등의 역할을 부여합니다. Young 수집에서는 선택한 리전의 생존 객체를 다른 리전으로 복사해 원래 공간을 비웁니다. Old 사용량이 마킹 시작 임계값에 이르면 Young 수집과 함께 동시 마킹을 시작해 Old 리전별 생존량을 계산합니다. STW인 Remark에서 마킹을 마무리하고 Cleanup에서 후속 수집 여부를 결정합니다. 이어지는 Mixed GC는 Young 리전과 회수 효율이 높은 일부 Old 리전을 함께 수집합니다. 객체 이동은 STW에서 일어나며 G1은 과거 수집 비용을 바탕으로 한 번에 수집할 리전 수를 조절해 정지 시간 목표를 맞추려 합니다. [Java 11 G1 구조와 수집 사이클](https://docs.oracle.com/en/java/javase/11/gctuning/garbage-first-g1-garbage-collector3.html)

**꼬리 질문 · G1을 쓰는데도 `To-space exhausted`나 긴 Full GC가 나오면 무엇을 보나요?**

`To-space exhausted`는 생존 객체를 옮길 대상 공간이 부족했음을 나타냅니다. GC 로그에서 직전의 할당·승격 속도, Old 점유율, 동시 마킹 시작 시점, 큰 객체를 담는 Humongous 리전 수를 확인합니다. 회수가 할당 속도를 따라가지 못해 할당을 계속할 공간을 확보하기 어려우면 G1이 STW Full GC로 전체 힙을 압축할 수 있습니다. `-XX:MaxGCPauseMillis`는 평소 G1이 수집 범위를 정할 때 사용하는 목표값입니다. [Java 11 G1 동작과 정지 시간 목표](https://docs.oracle.com/en/java/javase/11/gctuning/garbage-first-g1-garbage-collector3.html) · [Java 11 G1 Full GC 진단](https://docs.oracle.com/en/java/javase/11/gctuning/garbage-first-garbage-collector-tuning1.html)

## 19. GC 모니터링이 왜 필요하고 OutOfMemoryError는 어떻게 진단하나요?

**30–60초 답변**

> GC 모니터링은 응답 지연과 메모리 부족이 언제 시작됐는지 좁히는 데 필요합니다. JMX 지표와 GC 로그로 힙·Metaspace 사용량, GC 횟수와 정지 시간을 보고, 프로세스 RSS와 컨테이너 메모리 사용량도 함께 확인합니다. 비슷한 부하에서 Old를 회수한 뒤에도 힙 사용량이 계속 늘면 객체 누수를 의심합니다. Java 8은 `-XX:+PrintGCDetails`와 `-Xloggc:<path>`, Java 11은 `-Xlog:gc*`로 GC 기록을 남길 수 있습니다. OOM이 나면 오류 메시지와 종료 사유부터 확인합니다. `Java heap space`라면 힙 덤프에서 메모리를 오래 유지하는 객체와 루트까지의 참조 경로를 봅니다. `Metaspace`라면 로드된 클래스 수와 클래스 로더를 봅니다. 힙이 안정적인데 RSS가 늘어난다면 스레드 스택, 직접 버퍼, JNI 등 네이티브 메모리를 조사합니다. 컨테이너가 OOM으로 종료됐다면 컨테이너 종료 사유와 cgroup 메모리 이벤트를 확인합니다. [Java 8 GC 로그 옵션](https://docs.oracle.com/javase/8/docs/technotes/tools/unix/java.html) · [Java 11 통합 로깅](https://docs.oracle.com/en/java/javase/11/tools/java.html) · [Oracle JMX와 메모리 누수 진단](https://docs.oracle.com/en/java/javase/11/troubleshoot/troubleshooting-memory-leaks.html) · [Linux cgroup v2 메모리 이벤트](https://docs.kernel.org/admin-guide/cgroup-v2.html)

**꼬리 질문 · 재시작하면 증거가 사라지는 장애에 대비해 무엇을 설정하나요?**

파일 회전이 설정된 GC 로그와 JVM·컨테이너 메모리 지표를 보존합니다. Java 힙 OOM 분석을 위해 `-XX:+HeapDumpOnOutOfMemoryError`와 `-XX:HeapDumpPath=<path>`를 설정하고, 덤프를 쓸 수 있는 보존 경로와 디스크 여유를 확보합니다. 네이티브 메모리 증가를 비교하려면 JVM 시작 시 `-XX:NativeMemoryTracking=summary`를 켜고, 정상 시 `jcmd <pid> VM.native_memory baseline`을 남긴 뒤 `summary.diff`를 봅니다. NMT는 HotSpot이 추적하는 할당을 보여 주므로 외부 네이티브 라이브러리가 쓰는 메모리는 OS 지표도 함께 봅니다. 커널이 JVM을 종료하는 경우에는 컨테이너 종료 사유와 cgroup v2의 `memory.events` 중 `oom_kill` 증가가 근거가 됩니다. [Java 11 덤프 옵션](https://docs.oracle.com/en/java/javase/11/tools/java.html) · [Java 11 Native Memory Tracking](https://docs.oracle.com/en/java/javase/11/troubleshoot/diagnostic-tools.html) · [Linux cgroup v2 메모리 이벤트](https://docs.kernel.org/admin-guide/cgroup-v2.html)
