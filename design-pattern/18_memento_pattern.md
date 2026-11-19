# Memento Pattern

객체의 내부 상태를 이전 시점으로 되돌려야 할 때, 객체 자신에게 상태를 저장하고 복원할 책임을 둔다. 상태를 보관하는 호출자는 불투명한 체크포인트만 가지고 있으므로, 복원에 필요한 내부 구조가 바뀌더라도 그 구조에 의존하지 않는다. [GoF의 Design Patterns](https://www.informit.com/store/design-patterns-elements-of-reusable-object-oriented-9780201633610)

## 편집기 체크포인트 만들기

```java
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.List;

public class MementoExample {
    static final class Editor {
        interface Checkpoint {}

        private static final class Snapshot implements Checkpoint {
            private final Object owner;
            private final List<String> lines;

            Snapshot(Object owner, List<String> lines) {
                this.owner = owner;
                this.lines = List.copyOf(lines);
            }
        }

        private final Object owner = new Object();
        private List<String> lines = new ArrayList<>();

        void append(String line) {
            lines.add(line);
        }

        Checkpoint save() {
            return new Snapshot(owner, lines);
        }

        void restore(Checkpoint checkpoint) {
            if (!(checkpoint instanceof Snapshot snapshot) || snapshot.owner != owner) {
                throw new IllegalArgumentException("Checkpoint belongs to another editor");
            }
            lines = new ArrayList<>(snapshot.lines);
        }

        List<String> lines() {
            return List.copyOf(lines);
        }
    }

    public static void main(String[] args) {
        var editor = new Editor();
        var history = new ArrayDeque<Editor.Checkpoint>();
        editor.append("first");
        history.push(editor.save());
        editor.append("second");
        editor.restore(history.peek());
        editor.append("third");
        editor.restore(history.pop());
        if (!editor.lines().equals(List.of("first"))) {
            throw new AssertionError("Checkpoint should keep the original lines");
        }
    }
}
```

첫 줄을 추가한 시점의 체크포인트를 두 번 사용한다. 중간에 둘째 줄과 셋째 줄을 편집해도 최종 결과는 `[first]`이다. 체크포인트는 현재 편집 목록과 별개로 복사되며, 복원 후 편집도 체크포인트를 변경하지 않는다. 이 예제는 같은 편집기에서 생성한 체크포인트만 사용한다.

## 적용할 때 확인할 점

상태가 크거나 자주 바뀐다면 체크포인트의 크기, 보존 개수, 복원 시간을 고려한다. 예제의 요소는 불변 문자열이다. 변경 가능한 요소를 저장하는 경우에는 목록의 복사에 더해 요소의 상태도 보존하는 방식이 필요하다. [Command](17_command_pattern.md)는 실행할 요청을 표현하고, Memento는 복원할 시점의 상태를 보관한다. 커맨드의 실행 취소에서 체크포인트를 이용할 수 있다.
