# Test Doubles and Mockito

테스트 대역(Test Double)은 테스트에서 실제 협력 객체 자리를 대신한다. 협력 객체가 돌려줄 값을 제어해야 하는지, 외부로 보낸 요청을 확인해야 하는지에 따라 대역의 역할을 정한다.

## 1. 대역의 역할 고르기

| 대역 | 하는 일 | 예시 |
| --- | --- | --- |
| Dummy | 인자 자리를 채운다. | 이 시나리오에서 호출할 일이 없는 의존 객체 |
| Stub | 정해 둔 응답을 돌려준다. | 주문 ID가 일치하면 수신자 이메일을 반환한다. |
| Fake | 동작하는 간단한 구현을 제공한다. | 주문을 메모리의 Map에 저장한다. |
| Spy | 호출이나 인자를 기록해 나중에 확인할 수 있게 한다. | 전송을 요청한 이메일을 목록에 기록한다. |
| Mock | 협력 객체와의 상호작용이 기대와 맞는지 검증한다. | 영수증 발송 요청이 지정된 수신자에게 한 번 전달됐는지 확인한다. |

같은 Mockito 객체를 응답 제어와 호출 검증에 함께 사용할 수 있다. 대역의 역할은 테스트에서 어떤 일을 하는지에 따라 읽는다. [Martin Fowler의 테스트 대역 분류](https://martinfowler.com/articles/mocksArentStubs.html#TheDifferenceBetweenMocksAndStubs)

## 2. 스터빙과 호출 검증

스터빙은 테스트가 사용할 협력 객체의 응답을 정한다. Mockito의 `when(...).thenReturn(...)`과 `given(...).willReturn(...)`은 같은 용도로 쓴다. `verify(mock)`와 `then(mock).should()`는 실행한 뒤 기록된 호출을 확인한다. `BDDMockito`의 별칭을 사용하면 Given에서 응답을 준비하고 Then에서 상호작용을 확인하는 구조를 드러낼 수 있다.

영수증 발송 예제에서 수신자 조회 결과는 스터빙으로 제어한다. 발송 여부를 반환값으로 확인하고, 발송 요청은 이 기능의 관찰 가능한 결과이므로 수신자와 주문 ID를 검증한다. 첫 테스트는 한 번의 발송을, 둘째 테스트는 수신자가 없는 주문의 처리 방식을 검증한다. 예제는 Java 17, JUnit Jupiter 5, Mockito 5의 `mockito-junit-jupiter`를 사용한다. [Mockito의 BDDMockito API](https://github.com/mockito/mockito/blob/v5.20.0/mockito-core/src/main/java/org/mockito/BDDMockito.java)

```java
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.BDDMockito.given;
import static org.mockito.BDDMockito.then;

import java.util.Optional;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

interface MockitoReceiptRecipients {
    Optional<String> findRecipient(String orderId);
}

interface MockitoReceiptSender {
    void send(String orderId, String recipient);
}

final class MockitoReceiptService {
    private final MockitoReceiptRecipients recipients;
    private final MockitoReceiptSender sender;

    MockitoReceiptService(MockitoReceiptRecipients recipients, MockitoReceiptSender sender) {
        this.recipients = recipients;
        this.sender = sender;
    }

    boolean sendReceipt(String orderId) {
        var recipient = recipients.findRecipient(orderId);
        recipient.ifPresent(address -> sender.send(orderId, address));
        return recipient.isPresent();
    }
}

@ExtendWith(MockitoExtension.class)
class MockitoReceiptServiceTest {
    @Mock
    MockitoReceiptRecipients recipients;

    @Mock
    MockitoReceiptSender sender;

    @InjectMocks
    MockitoReceiptService service;

    @Test
    void sendsOneReceiptToTheRegisteredRecipient() {
        given(recipients.findRecipient("ORD-1")).willReturn(Optional.of("buyer@example.com"));

        boolean sent = service.sendReceipt("ORD-1");

        assertTrue(sent);
        then(sender).should().send("ORD-1", "buyer@example.com");
        then(sender).shouldHaveNoMoreInteractions();
    }

    @Test
    void leavesTheSenderUnusedWhenThereIsNoRecipient() {
        given(recipients.findRecipient("ORD-2")).willReturn(Optional.empty());

        boolean sent = service.sendReceipt("ORD-2");

        assertFalse(sent);
        then(sender).shouldHaveNoInteractions();
    }
}
```

## 3. Mockito 애너테이션의 역할

| 애너테이션 | 실제 동작 |
| --- | --- |
| `@Mock` | Mockito가 제어하고 호출을 기록할 대역을 만든다. |
| `@Spy` | 기본적으로 실제 메서드를 실행하는 부분 대역을 만든다. 일부 동작만 제어해야 할 때 사용한다. |
| `@InjectMocks` | 테스트 대상에 준비된 대역을 주입한다. Mockito는 생성자, 세터, 필드 주입을 순서대로 시도한다. |

`MockitoExtension`이 JUnit 테스트에서 애너테이션을 처리한다. 위 예제에서는 생성자에 두 대역을 전달한다. 조립 규칙을 시험하거나 주입할 대상을 명시해야 하면 테스트에서 생성자를 직접 호출하는 방법도 있다. [MockitoExtension](https://github.com/mockito/mockito/blob/v5.20.0/mockito-extensions/mockito-junit-jupiter/src/main/java/org/mockito/junit/jupiter/MockitoExtension.java) · [Mockito InjectMocks](https://raw.githubusercontent.com/mockito/mockito/v5.20.0/mockito-core/src/main/java/org/mockito/InjectMocks.java)

대역 분류에서 Spy는 기록하는 역할을 뜻한다. Mockito의 `@Spy`는 실제 동작을 일부 실행한다는 특성이 있다. `when(spy.method())`를 평가하는 중에 실제 메서드가 호출될 수 있으므로, 준비 중 실행을 피해야 하는 동작에는 `doReturn(value).when(spy).method()` 같은 형식을 사용한다. [Mockito Spy](https://raw.githubusercontent.com/mockito/mockito/v5.20.0/mockito-core/src/main/java/org/mockito/Spy.java)

## 4. Classicist와 Mockist 관점

Classicist 스타일은 제어하기 쉬운 실제 협력 객체와 함께 실행하고 결과 상태를 검증하는 데 무게를 둔다. Mockist 스타일은 협력 객체의 대역을 두고 객체 사이의 호출 계약을 검증하는 데 무게를 둔다. 외부 발송처럼 호출 자체가 계약이면 호출을 확인하고, 주문 합계처럼 결과 값으로 충분한 규칙은 공개 결과를 단언한다. 호출 순서나 내부 헬퍼 사용을 고정하기 전에 그 순서나 협력이 업무에서 요구되는지 확인한다. [Martin Fowler의 Classical and Mockist Testing](https://martinfowler.com/articles/mocksArentStubs.html#ClassicalAndMockistTesting)
