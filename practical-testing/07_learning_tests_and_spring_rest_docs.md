# Learning Tests and Spring REST Docs

학습 테스트는 사용하는 라이브러리의 동작을 작은 예제로 확인한다. Spring REST Docs는 API 테스트가 실행한 요청과 응답으로 문서 조각을 만든다. 앞의 테스트는 외부 코드에 기대하는 동작을, 뒤의 테스트는 API 소비자에게 제공할 계약을 검증한다.

## 1. 학습 테스트로 라이브러리 계약 확인하기

처음 보는 API를 쓸 때는 결과를 예상하기 어려운 경계부터 확인한다. 예를 들어 청구일 계산에서 `LocalDate.plusMonths`를 쓰려면 1월 31일에 한 달을 더하는 경우를 살펴볼 수 있다. Java는 계산한 월에 같은 일자가 없으면 해당 월의 마지막 유효 일자로 조정한다. [Java 17 LocalDate.plusMonths](https://docs.oracle.com/en/java/javase/17/docs/api/java.base/java/time/LocalDate.html#plusMonths(long))

```java
import java.time.LocalDate;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;

class MonthEndLearningTest {
    @Test
    void movesToTheLastValidDayOfTheFollowingMonth() {
        LocalDate januaryEnd = LocalDate.of(2024, 1, 31);

        LocalDate followingMonth = januaryEnd.plusMonths(1);

        assertEquals(LocalDate.of(2024, 2, 29), followingMonth);
    }
}
```

매월 말일에 청구해야 한다는 업무 규칙은 별도로 확인한다. 2월 29일에 다시 `plusMonths(1)`을 적용하면 3월 29일이므로, 연속 청구에서 말일을 유지해야 한다면 초기 기준일이나 말일 정책을 모델에 둔다. 테스트의 목적을 이름으로 드러내면 라이브러리 업그레이드 때 어떤 가정을 확인하는지 알 수 있다.

## 2. API 테스트에서 문서 조각 생성하기

Spring REST Docs는 MockMvc 등으로 실행한 요청과 응답을 바탕으로 스니펫을 생성한다. 테스트의 단언으로 상태 코드와 대표 응답값을 확인하고, 문서 기술자로 경로 변수와 응답 필드의 의미를 설명한다. 기본 `responseFields`를 쓰면 문서화하지 않은 응답 필드가 추가되거나 필수로 설명한 필드가 빠졌을 때 테스트가 실패한다. 요구사항에 맞게 선택 필드나 생략 범위를 지정할 수 있다. [Spring REST Docs의 요청·응답 필드 문서화](https://docs.spring.io/spring-restdocs/reference/documenting-your-api/request-response-payloads.html)

다음 예제는 Java 17, JUnit 5와 Spring REST Docs 3.0의 MockMvc 지원을 사용한다. 테스트용 컨트롤러는 같은 HTTP 계약을 보여 주기 위한 고정 응답을 반환한다. 운영 컨트롤러의 검증이나 요청 필터까지 문서화하려면 실제 웹 테스트 컨텍스트에서 그 경로를 실행한다. [Spring Boot의 웹 계층 테스트](https://docs.spring.io/spring-boot/3.5/reference/testing/spring-boot-applications.html)

```java
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.RegisterExtension;
import org.springframework.restdocs.RestDocumentationContextProvider;
import org.springframework.restdocs.RestDocumentationExtension;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RestController;

import static org.springframework.restdocs.mockmvc.MockMvcRestDocumentation.document;
import static org.springframework.restdocs.mockmvc.MockMvcRestDocumentation.documentationConfiguration;
import static org.springframework.restdocs.mockmvc.RestDocumentationRequestBuilders.get;
import static org.springframework.restdocs.payload.PayloadDocumentation.fieldWithPath;
import static org.springframework.restdocs.payload.PayloadDocumentation.responseFields;
import static org.springframework.restdocs.request.RequestDocumentation.parameterWithName;
import static org.springframework.restdocs.request.RequestDocumentation.pathParameters;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

class OrderHttpDocumentationTest {
    @RegisterExtension
    final RestDocumentationExtension restDocs =
            new RestDocumentationExtension("target/generated-snippets");

    private MockMvc mockMvc;

    @BeforeEach
    void setUp(RestDocumentationContextProvider context) {
        mockMvc = MockMvcBuilders.standaloneSetup(new DocumentationOrderController())
                .apply(documentationConfiguration(context))
                .build();
    }

    @Test
    void documentsOrderLookup() throws Exception {
        mockMvc.perform(get("/orders/{id}", 42))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.id").value(42))
                .andExpect(jsonPath("$.status").value("PAID"))
                .andDo(document("orders/get",
                        pathParameters(parameterWithName("id").description("주문 식별자")),
                        responseFields(
                                fieldWithPath("id").description("주문 식별자"),
                                fieldWithPath("status").description("주문 상태"))));
    }
}

@RestController
class DocumentationOrderController {
    @GetMapping("/orders/{id}")
    public DocumentationOrderResponse find(@PathVariable("id") long id) {
        return new DocumentationOrderResponse(id, "PAID");
    }
}

record DocumentationOrderResponse(long id, String status) {}
```

테스트는 스니펫을 `target/generated-snippets/orders/get/`에 생성한다. 그중 `path-parameters.adoc`는 요청 경로의 `id`를, `response-fields.adoc`는 응답의 `id`와 `status`를 설명한다. AsciiDoc의 `snippets` 속성이 출력 디렉터리를 가리키면 `include::{snippets}/orders/get/response-fields.adoc[]`로 응답 필드 표를 포함할 수 있다. 중요한 성공과 오류 응답은 각각 테스트로 실행한다. [Spring REST Docs의 경로 변수 문서화](https://docs.spring.io/spring-restdocs/reference/documenting-your-api/path-parameters.html) · [생성한 스니펫 사용하기](https://docs.spring.io/spring-restdocs/tutorial/getting-started/index.html)
