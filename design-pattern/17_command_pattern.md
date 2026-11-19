# Command Pattern

실행할 요청과 입력을 객체로 표현하면 호출자에게 구체적인 처리 방법을 숨기고, 그 요청을 예약하거나 이력에 보관할 수 있다. 커맨드는 실행에 필요한 대상과 데이터를 기억하고, 호출자는 정해진 인터페이스로 요청을 실행한다. [GoF의 Design Patterns](https://www.informit.com/store/design-patterns-elements-of-reusable-object-oriented-9780201633610)

## 메모 제목 변경과 실행 취소

```java
import java.util.ArrayDeque;
import java.util.Deque;

public class CommandExample {
    interface Command {
        Runnable execute();
    }

    static final class Note {
        private String title;

        Note(String title) {
            this.title = title;
        }

        void rename(String newTitle) {
            title = newTitle;
        }
    }

    record RenameNote(Note note, String newTitle) implements Command {
        public Runnable execute() {
            String previousTitle = note.title;
            note.rename(newTitle);
            return () -> note.rename(previousTitle);
        }
    }

    static final class History {
        private final Deque<Runnable> undoActions = new ArrayDeque<>();

        void perform(Command command) {
            undoActions.push(command.execute());
        }

        void undo() {
            Runnable action = undoActions.peek();
            if (action == null) {
                return;
            }
            action.run();
            undoActions.pop();
        }
    }

    public static void main(String[] args) {
        var note = new Note("Draft");
        var history = new History();
        history.perform(new RenameNote(note, "Pack order"));
        history.perform(new RenameNote(note, "Ship order"));
        if (!note.title.equals("Ship order")) {
            throw new AssertionError("Latest command should be visible");
        }
        history.undo();
        if (!note.title.equals("Pack order")) {
            throw new AssertionError("First undo should restore Pack order");
        }
        history.undo();
        if (!note.title.equals("Draft")) {
            throw new AssertionError("Second undo should restore Draft");
        }
    }
}
```

두 요청이 실행되면 제목은 `Ship order`가 된다. `History`가 마지막에 성공한 변경부터 실행 취소하므로 제목은 `Pack order`를 거쳐 `Draft`로 돌아온다. 커맨드는 실행 시점의 이전 제목을 되돌리기 동작에 캡처한다.

## 적용할 때 확인할 점

큐, 배치, 실행 이력처럼 요청의 수명 주기를 관리해야 할 때 유용하다. 실행 취소는 작업 전 상태를 캡처하고 역동작을 안전하게 실행할 수 있는지에 달려 있다. 예제는 같은 메모의 변경을 한 이력에서 순서대로 처리한다. 외부 결제나 발송이 완료된 작업은 취소나 보상 요청을 별도로 정의하고 실패와 재시도를 다룬다. [Strategy](02_strategy_pattern.md)는 같은 목적을 달성하는 알고리즘을 교체하는 데 적합하다.
