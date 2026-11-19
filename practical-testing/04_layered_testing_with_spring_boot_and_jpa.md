# Layered Testing with Spring Boot and JPA

계층마다 관찰할 계약이 다르다. 저장 계층은 실제 저장과 조회 규칙을, 비즈니스 계층은 정책과 상태 전이를, 프레젠테이션 계층은 HTTP 입출력을 검증한다. 오류가 발생할 가능성이 있는 경계가 테스트에 포함되도록 실행 범위를 정한다.

| 계층 | 검증할 계약 | 실행 범위 예시 |
| --- | --- | --- |
| Persistence | JPA 매핑, 조회 조건과 정렬, 데이터베이스 제약 | `@DataJpaTest` |
| Business | 업무 규칙, 저장과 재고 변경의 일관성, 트랜잭션 | 순수 JUnit 테스트 또는 `@SpringBootTest` |
| Presentation | 요청 바인딩, 검증, 상태·헤더·JSON 응답 | `@WebMvcTest`와 `MockMvc` |

아래 코드는 Spring Boot 3.5, JUnit Jupiter, Spring Data JPA와 Spring MVC를 사용하는 주문 프로젝트의 테스트 예시다. 주문 엔티티와 저장소, 주문 서비스, 컨트롤러는 프로젝트에 있는 타입을 가정한다. [Spring Boot 애플리케이션 테스트](https://docs.spring.io/spring-boot/3.5/reference/testing/spring-boot-applications.html)

## 1. Persistence Layer에서 조회와 매핑 검증하기

`@DataJpaTest`는 JPA 관련 빈을 구성하고 기본적으로 테스트마다 트랜잭션을 열어 종료 시 롤백한다. 조회 조건을 검사할 때는 조건을 만족하는 행과 제외할 행을 함께 저장한다. 아래 예시는 같은 회원의 취소 주문과 다른 회원의 결제 주문을 포함해 회원 조건과 상태 조건을 함께 검증한다. 자동 생성된 ID의 내림차순이 계약이므로 반환 순서도 확인한다. [Spring Boot의 Data JPA 테스트 슬라이스](https://docs.spring.io/spring-boot/3.5/reference/testing/spring-boot-applications.html#testing.spring-boot-applications.autoconfigured-spring-data-jpa)

```java
import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.orm.jpa.DataJpaTest;
import org.springframework.boot.test.autoconfigure.orm.jpa.TestEntityManager;

@DataJpaTest
class PurchaseOrderRepositoryTest {
    @Autowired PurchaseOrderRepository orders;
    @Autowired TestEntityManager entities;

    @Test
    void findsPaidOrdersForOneMemberInIdOrder() {
        var first = orders.save(new PurchaseOrder(10L, OrderStatus.PAID));
        orders.save(new PurchaseOrder(10L, OrderStatus.CANCELLED));
        orders.save(new PurchaseOrder(20L, OrderStatus.PAID));
        var second = orders.save(new PurchaseOrder(10L, OrderStatus.PAID));
        entities.flush();
        entities.clear();

        var found = orders.findByMemberIdAndStatusOrderByIdDesc(10L, OrderStatus.PAID);

        assertThat(found)
                .extracting(PurchaseOrder::getId)
                .containsExactly(second.getId(), first.getId());
    }
}
```

`flush`는 영속성 컨텍스트의 변경을 DB에 동기화한다. 이어서 `clear`를 호출해 관리 중인 엔티티를 분리하면 새 조회에서 매핑된 값을 다시 확인할 수 있다. 커밋 시점에 검사되는 제약을 검증하려면 실제 트랜잭션 종료까지 포함한다. 운영 DB의 방언이나 제약에 의존하는 쿼리는 같은 엔진의 테스트용 DB에서 실행하고, 그 데이터소스를 유지해야 한다면 `@AutoConfigureTestDatabase(replace = Replace.NONE)`을 사용한다. Spring Boot 3.5의 기본 교체 정책은 테스트용으로 인식된 연결의 교체를 피하는 `NON_TEST`다. [Spring 트랜잭션 테스트와 flush](https://docs.spring.io/spring-framework/reference/6.2/testing/testcontext-framework/tx.html) · [Spring Boot 테스트 데이터베이스 교체 정책](https://docs.spring.io/spring-boot/3.5/api/java/org/springframework/boot/test/autoconfigure/jdbc/AutoConfigureTestDatabase.html)

## 2. Business Layer에서 정책과 트랜잭션 검증하기

수량 검사나 가격 계산처럼 스프링 환경과 독립적인 규칙은 대상을 직접 생성한 JUnit 테스트로 확인한다. 여러 빈이 협업하고 JPA 변경 감지나 선언적 트랜잭션까지 확인해야 한다면 스프링 컨텍스트에서 서비스의 공개 메서드를 호출한다. 아래 예시는 빈 테스트 데이터베이스에서 상품 재고를 준비하고, 주문 서비스가 반환된 뒤 주문과 재고를 각각 다시 읽는다. 서비스 메서드가 실제 트랜잭션을 관리한다는 전제를 사용한다.

```java
import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;

@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.NONE)
class OrderCheckoutServiceTest {
    @Autowired OrderCheckoutService checkout;
    @Autowired PurchaseOrderRepository orders;
    @Autowired StockRepository stocks;

    @Test
    void commitsOrderAndUpdatedStock() {
        stocks.save(new Stock("MUG-01", 2));

        long orderId = checkout.placeOrder(new CheckoutOrderCommand(10L, "MUG-01", 1));

        assertThat(orders.findById(orderId).orElseThrow().getStatus())
                .isEqualTo(OrderStatus.CONFIRMED);
        assertThat(stocks.findById("MUG-01").orElseThrow().getQuantity()).isEqualTo(1);
    }
}
```

예시처럼 테스트 메서드에 별도 트랜잭션을 열지 않으면, 서비스 호출이 반환된 뒤 저장소를 통해 커밋 결과를 읽을 수 있다. 이런 테스트는 독립된 데이터베이스나 실행 후 정리 절차가 필요하다. 롤백 계약을 확인할 때는 일부 쓰기가 시작된 뒤 실패하는 입력을 고르고, 예외와 함께 새 주문이 남았는지와 재고가 원래대로인지 확인한다. 실제 서버를 띄운 `RANDOM_PORT` 테스트에서 HTTP 요청을 처리하는 서버 트랜잭션은 테스트 스레드의 롤백과 별개다. [Spring의 테스트 트랜잭션](https://docs.spring.io/spring-framework/reference/6.2/testing/testcontext-framework/tx.html) · [Spring Boot의 서버 실행 범위](https://docs.spring.io/spring-boot/3.5/reference/testing/spring-boot-applications.html)

## 3. Presentation Layer에서 HTTP 계약 검증하기

`@WebMvcTest`는 MVC 인프라와 지정한 컨트롤러를 대상으로 실행한다. `MockMvc`는 HTTP 서버를 띄우지 않고 요청 매핑, JSON 바인딩, 검증, 응답 변환을 거친다. 비즈니스 서비스의 응답은 `@MockitoBean`으로 지정해 이 테스트의 범위를 웹 계층에 맞춘다. 아래 예시는 주문 생성에 필요한 JSON을 받고 `201 Created`와 `Location`, 생성된 ID를 반환하는 API를 가정한다. [Spring Boot의 MVC 테스트 슬라이스](https://docs.spring.io/spring-boot/3.5/reference/testing/spring-boot-applications.html#testing.spring-boot-applications.autoconfigured-spring-mvc) · [Spring Framework의 MockitoBean](https://docs.spring.io/spring-framework/reference/6.2/testing/annotations/integration-spring/annotation-mockitobean.html)

```java
import static org.mockito.BDDMockito.given;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.http.MediaType;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.MockMvc;

@WebMvcTest(OrderController.class)
class OrderControllerTest {
    @Autowired MockMvc mvc;
    @MockitoBean OrderCheckoutService checkout;

    @Test
    void returnsCreatedOrderLocation() throws Exception {
        given(checkout.placeOrder(new CheckoutOrderCommand(10L, "MUG-01", 1)))
                .willReturn(21L);

        mvc.perform(post("/orders")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {"memberId": 10, "sku": "MUG-01", "quantity": 1}
                                """))
                .andExpect(status().isCreated())
                .andExpect(header().string("Location", "/orders/21"))
                .andExpect(jsonPath("$.id").value(21));
    }

    @Test
    void rejectsInvalidQuantityBeforeCallingService() throws Exception {
        mvc.perform(post("/orders")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {"memberId": 10, "sku": "MUG-01", "quantity": 0}
                                """))
                .andExpect(status().isBadRequest());

        verifyNoInteractions(checkout);
    }
}
```

두 번째 테스트는 컨트롤러가 요청 본문에 `@Valid`를 적용하고 수량 필드에 양수 제약을 두는 계약을 확인한다. 인증과 인가도 API의 계약에 포함되면 해당 필터와 테스트 인증을 함께 구성한다. 웹에서 관찰할 실패, 서비스에서 지킬 상태 변화, 저장소에서 확인할 조회 결과를 알맞은 경계에서 검증하면 실패 위치를 좁히기 쉽다. [Spring Framework의 MockMvc](https://docs.spring.io/spring-framework/reference/6.2/testing/mockmvc.html)
