# Spring MVC Form Validation and Binding Errors

## 1. 타입 변환 오류와 값 검증 오류

Spring MVC는 요청 파라미터를 폼 객체에 바인딩하면서 문자열을 대상 타입으로 바꾼다. 숫자 필드에 `abc`를 넣으면 변환에 실패해 `typeMismatch` 오류가 생길 수 있다. 변환된 값이 허용 범위를 벗어나거나 두 필드의 조합이 규칙에 어긋나면 검증 오류를 추가한다. 컨트롤러가 이 오류를 받아 폼을 다시 렌더링하려면 `BindingResult`를 해당 `@ModelAttribute` 바로 뒤에 선언한다. [Spring Framework 6.2 · 모델 속성 바인딩](https://docs.spring.io/spring-framework/reference/6.2/web/webmvc/mvc-controller/ann-methods/modelattrib-method-args.html) · [Spring Framework 6.2 · MVC 검증](https://docs.spring.io/spring-framework/reference/6.2/web/webmvc/mvc-controller/ann-validation.html)

| 오류 범위 | 표현 | 처리 |
| --- | --- | --- |
| 필드 | `FieldError` | `rejectValue("minimum", "capacity.minimum")`로 해당 입력 옆에 표시 |
| 폼 전체 | `ObjectError` | `reject("capacity.order")`로 두 필드의 관계 등 공통 오류 표시 |

정원 폼에서 최소 인원이 최대 인원보다 크면 다음과 같이 폼 전체 오류를 등록한다. 숫자 변환에 실패한 필드가 있으면 교차 검증을 보류하고 해당 필드 오류를 그대로 표시한다.

```java
import org.springframework.validation.BindingResult;

public class CapacityChecks {

    public static void checkOrder(Integer minimum, Integer maximum, BindingResult errors) {
        if (errors.hasFieldErrors("minimum") || errors.hasFieldErrors("maximum")) {
            return;
        }

        if (minimum != null && maximum != null && minimum > maximum) {
            errors.reject("capacity.order", "Minimum capacity must not exceed maximum capacity.");
        }
    }
}
```

검증 오류가 있으면 같은 폼 뷰 이름을 반환하고, 검증을 통과한 경우에 데이터를 저장한 뒤 다른 URL로 리다이렉트한다. 여러 컨트롤러에서 같은 규칙을 사용하면 Spring `Validator`의 `supports()`와 `validate()`로 분리하고 `@InitBinder`에서 관련 바인더에 `addValidators()`로 등록할 수 있다. [Spring Framework 6.2 · Validator](https://docs.spring.io/spring-framework/reference/6.2/core/validation/validator.html) · [Spring Framework 6.2 · MVC 검증](https://docs.spring.io/spring-framework/reference/6.2/web/webmvc/mvc-controller/ann-validation.html)

## 2. 오류 코드를 사용자 메시지로 바꾸기

기본 `DefaultMessageCodesResolver`는 `bookingForm.minimum`에서 숫자 변환에 실패했을 때 아래 후보를 구체적인 순서대로 만든다. 화면 문구는 해당 코드 중 필요한 것만 [메시지 번들](09_spring_mvc_messages_and_internationalization.md)에 등록해 조정한다. [Spring Framework 6.2 · DefaultMessageCodesResolver](https://docs.spring.io/spring-framework/docs/6.2.x/javadoc-api/org/springframework/validation/DefaultMessageCodesResolver.html)

1. `typeMismatch.bookingForm.minimum`
2. `typeMismatch.minimum`
3. `typeMismatch.java.lang.Integer`
4. `typeMismatch`

Thymeleaf는 `th:field`로 연결한 입력에 거부된 값을 다시 표시할 수 있다. 필드 메시지는 `th:errors="*{minimum}"`으로, 폼 전체 메시지는 `th:errors="*{global}"`로 표시한다. [Thymeleaf 3.1 · 검증과 오류 메시지](https://www.thymeleaf.org/doc/tutorials/3.1/thymeleafspring.html#validation-and-error-messages)
