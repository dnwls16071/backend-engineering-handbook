# Singleton Pattern

싱글턴은 정해진 범위에서 인스턴스 생성을 하나로 제한하고, 그 인스턴스에 접근할 지점을 제공하는 생성 패턴이다. 공유 자원의 수명과 개수를 함께 관리할 필요가 있을 때 사용한다. [GoF의 Singleton](https://www.informit.com/store/design-patterns-elements-of-reusable-object-oriented-9780201633610)

## 어떤 문제를 푸는가

한 실행 환경에서 여러 호출자가 같은 일련번호 발급기를 써야 한다고 하자. 호출자마다 새 발급기를 만들면 카운터가 따로 증가한다. Java에서 열거형 상수를 하나만 두면 해당 타입의 인스턴스를 그 상수로 제한할 수 있다. JVM은 클래스 초기화를 동기화하므로 여러 스레드가 처음 접근해도 초기화 경합을 직접 처리할 필요가 줄어든다. [Java 클래스 초기화 절차](https://docs.oracle.com/javase/specs/jls/se17/html/jls-12.html#jls-12.4.2) · [Java 열거형](https://docs.oracle.com/javase/specs/jls/se17/html/jls-8.html#jls-8.9)

## Java 17 예제

```java
import java.util.concurrent.atomic.AtomicLong;

public class SingletonExample {
    enum RequestSequence {
        INSTANCE;

        private final AtomicLong counter = new AtomicLong();

        long next() {
            return counter.incrementAndGet();
        }
    }

    public static void main(String[] args) {
        RequestSequence firstCaller = RequestSequence.INSTANCE;
        RequestSequence secondCaller = RequestSequence.INSTANCE;
        long first = firstCaller.next();
        long second = secondCaller.next();

        if (firstCaller != secondCaller || first != 1 || second != 2) {
            throw new AssertionError(first + ", " + second);
        }
        System.out.println(first + ", " + second);
    }
}
```

실행 결과는 `1, 2`다. 두 호출자가 같은 객체의 카운터를 사용한다. 초기화 동기화와 카운터 갱신의 동시성은 따로 다룬다. 여기서는 `AtomicLong`으로 증가 연산을 처리한다. [Java AtomicLong](https://docs.oracle.com/en/java/javase/17/docs/api/java.base/java/util/concurrent/atomic/AtomicLong.html)

## 적용할 때 볼 점

- 예제의 한 인스턴스 범위는 해당 타입을 정의한 클래스 로더다. 다른 클래스 로더가 같은 이름의 타입을 별도로 정의하거나 프로세스가 추가되면 각자 인스턴스를 가진다. 분산 환경의 전역 일련번호가 필요하다면 저장소나 별도 발급 체계로 범위를 넓혀야 한다. [JVM 명세의 클래스 생성과 로딩](https://docs.oracle.com/javase/specs/jvms/se17/html/jvms-5.html#jvms-5.3)
- 여러 호출부가 전역 접근 지점에 직접 의존하면 수명 관리와 테스트 격리가 어려워진다. 객체를 하나만 구성하고 필요한 곳에 주입하는 방식도 검토할 수 있다. 이 방식은 인스턴스 개수를 구성 코드에서 결정한다.
