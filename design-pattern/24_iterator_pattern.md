# Iterator Pattern

호출자가 컬렉션을 순회할 때는 내부 저장 구조와 현재 탐색 위치를 알 필요가 없다. Iterator는 순회 상태와 다음 원소를 얻는 방법을 객체로 캡슐화한다. 순회할 컬렉션은 필요할 때 새로운 반복자를 만든다. [GoF의 Iterator 패턴](https://www.informit.com/store/design-patterns-elements-of-reusable-object-oriented-9780201633610)

## 저장 방식과 탐색 상태 나누기

예제의 최근 내역 컬렉션은 항목을 들어온 순서로 보관하고, 반복자는 최신 항목부터 반환한다. 반복자가 둘이면 각자 독립적으로 위치를 유지한다. Java에서 소진된 반복자에 `next()`를 호출하면 `NoSuchElementException`이 발생한다. [Java 17 Iterator](https://docs.oracle.com/en/java/javase/17/docs/api/java.base/java/util/Iterator.html)

```java
import java.util.Iterator;
import java.util.List;
import java.util.NoSuchElementException;

class IteratorExample {
    static final class RecentOrders implements Iterable<String> {
        private final List<String> orders;

        RecentOrders(List<String> orders) {
            this.orders = List.copyOf(orders);
        }

        @Override
        public Iterator<String> iterator() {
            return new Iterator<>() {
                private int index = orders.size() - 1;

                @Override
                public boolean hasNext() {
                    return index >= 0;
                }

                @Override
                public String next() {
                    if (!hasNext()) {
                        throw new NoSuchElementException();
                    }
                    return orders.get(index--);
                }
            };
        }
    }

    public static void main(String[] args) {
        var orders = new RecentOrders(List.of("A", "B"));
        var first = orders.iterator();
        var second = orders.iterator();
        if (!first.next().equals("B") || !first.next().equals("A")
                || first.hasNext() || !second.next().equals("B")) {
            throw new AssertionError("Iterators should navigate independently");
        }
        try {
            first.next();
            throw new AssertionError("Exhausted iterator should fail");
        } catch (NoSuchElementException expected) {
            // 소진된 반복자의 계약이다.
        }
    }
}
```

첫 번째 반복자는 `B`, `A`를 반환해 소진된다. 두 번째 반복자는 여전히 첫 항목인 `B`를 반환한다. 예제는 복사한 불변 목록을 탐색한다. 가변 컬렉션을 탐색한다면 순회 중 변경을 허용하는지, 변경을 어떻게 반영하는지 문서화한다. 여러 순회 방식이 필요하면 같은 컬렉션에서 서로 다른 반복자를 제공할 수 있다.
