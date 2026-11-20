# Spring MVC Bean Validation

## 1. 요청 DTO에 제약 선언하기

Jakarta Bean Validation은 `@NotBlank`, `@NotNull`, `@Min` 등의 애너테이션으로 규칙을 표현한다. Spring Boot에서는 `spring-boot-starter-validation`으로 구현체를 추가할 수 있다. `@Min`은 `null`을 허용하므로 필수 숫자에는 `@NotNull`도 적용한다. 중첩 객체의 제약까지 평가하려면 해당 위치에 `@Valid`를 붙인다. [Jakarta Bean Validation 3.0](https://jakarta.ee/specifications/bean-validation/3.0/) · [Spring Boot 3.5 · Validation](https://docs.spring.io/spring-boot/3.5/reference/io/validation.html)

```java
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;

public record BookingRequest(
        @NotBlank String title,
        @NotNull @Min(1) Integer seats
) {
}
```

여러 속성의 관계를 반복해서 검증해야 하면 클래스 수준 제약을 만들 수 있다. 생성과 수정에서 요구하는 필드가 다르면 각각의 DTO에 제약을 선언하거나 `@Validated(Create.class)`처럼 검증 그룹을 선택한다. 오류 메시지는 제약의 기본 문구나 `message`로 지정한다. 폼 바인딩에서는 `NotBlank.bookingForm.title`처럼 구체적인 오류 코드도 메시지 번들에 등록할 수 있다. [Jakarta Bean Validation 3.0](https://jakarta.ee/specifications/bean-validation/3.0/) · [Spring Framework 6.2 · DefaultMessageCodesResolver](https://docs.spring.io/spring-framework/docs/6.2.x/javadoc-api/org/springframework/validation/DefaultMessageCodesResolver.html)

## 2. 폼과 JSON 요청의 처리 차이

| 요청 | 처리 흐름 |
| --- | --- |
| `@Valid @ModelAttribute` | 폼 값 바인딩 뒤 객체 검증. 바로 뒤의 `BindingResult`에서 폼 오류 처리 가능. |
| `@Valid @RequestBody` | 메시지 컨버터가 JSON을 객체로 읽은 뒤 객체 검증. 일반적으로 오류 시 `MethodArgumentNotValidException`. |
| 메서드 인자에 직접 붙인 `@Min` 등의 제약 | Spring MVC의 내장 메서드 검증이 적용되면 `HandlerMethodValidationException`. |

`{"seats":0}`처럼 객체를 만들 수 있는 입력은 제약 검증에서 걸린다. `{"seats":[1,2]}`처럼 DTO 타입에 맞게 읽을 수 없는 JSON은 메시지 컨버터 단계에서 `HttpMessageNotReadableException`이 발생할 수 있다. Spring MVC의 내장 메서드 검증을 사용하려면 컨트롤러 클래스 수준의 `@Validated`를 두어 프록시 기반 검증으로 전환하는 구성을 피한다. `@Valid`는 중첩 검증을 지시하므로 그 자체로 메서드 제약을 선언하지 않는다. [Spring Framework 6.2 · MVC 검증](https://docs.spring.io/spring-framework/reference/6.2/web/webmvc/mvc-controller/ann-validation.html) · [Spring Framework 6.2 · @RequestBody](https://docs.spring.io/spring-framework/reference/6.2/web/webmvc/mvc-controller/ann-methods/requestbody.html)

폼 오류는 [폼 검증 문서](10_spring_mvc_form_validation_and_binding_errors.md), JSON 오류 응답의 공통 형식은 [API 예외 처리 문서](15_spring_mvc_api_exception_handling.md)에서 다룬다.
