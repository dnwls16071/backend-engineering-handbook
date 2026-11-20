# Spring MVC Type Conversion and Formatting

## 1. 문자열 요청 값을 도메인 타입으로 변환하기

Spring MVC는 경로 변수, 쿼리 파라미터, 폼 필드에서 얻은 값을 컨트롤러가 선언한 타입으로 변환한다. 예를 들어 `/notes/12`의 `12`를 숫자나 `NoteId`로 받을 수 있다. `Converter<S, T>`는 소스 타입에서 대상 타입으로 값을 바꾸는 규칙을 정의한다. `ConversionService`는 등록된 변환 규칙에서 두 타입에 맞는 것을 선택한다. [Spring Framework 6.2 · 타입 변환](https://docs.spring.io/spring-framework/reference/6.2/core/validation/convert.html) · [Spring Framework 6.2 · MVC 변환 설정](https://docs.spring.io/spring-framework/reference/6.2/web/webmvc/mvc-config/conversion.html)

```java
import org.springframework.core.convert.converter.Converter;

public class NoteIdConverter implements Converter<String, NoteIdConverter.NoteId> {

    @Override
    public NoteId convert(String source) {
        if (!source.matches("[1-9][0-9]*")) {
            throw new IllegalArgumentException("Note ID must be a positive decimal integer.");
        }
        return new NoteId(Long.parseLong(source));
    }

    public record NoteId(long value) {
    }
}
```

`WebMvcConfigurer#addFormatters`에서 `registry.addConverter(new NoteIdConverter())`로 등록하면 `@PathVariable("id") NoteId id` 같은 인자에 사용할 수 있다. 범위를 벗어난 ID도 `Long.parseLong()`이 거부한다. 변환에 실패하면 폼에서는 바인딩 오류로 수집될 수 있고, 단독 경로 변수나 요청 파라미터에서는 기본 예외 처리로 `400 Bad Request`가 될 수 있다. [Spring Framework 6.2 · MVC 변환 설정](https://docs.spring.io/spring-framework/reference/6.2/web/webmvc/mvc-config/conversion.html) · [폼 바인딩 오류](10_spring_mvc_form_validation_and_binding_errors.md)

## 2. 로케일을 사용해 표시하고 다시 읽기

| 인터페이스 | 적합한 규칙 |
| --- | --- |
| `Converter<S, T>` | 문자열을 도메인 식별자로 바꾸는 것처럼 타입 간 단방향 변환 |
| `Formatter<T>` | 숫자나 날짜처럼 로케일에 맞춰 문자열로 표시하고 다시 타입으로 파싱 |

`Formatter`는 `parse(text, locale)`와 `print(value, locale)`를 제공한다. 예를 들어 숫자 `1234.5`는 로케일에 따라 `1,234.5` 또는 `1.234,5`로 표시할 수 있다. 폼의 특정 필드에 형식을 적용하려면 `@NumberFormat` 또는 `@DateTimeFormat`을 사용할 수 있다. 브라우저의 날짜 입력에 고정된 형식이 필요할 때는 `@DateTimeFormat(iso = DateTimeFormat.ISO.DATE)`를 사용할 수 있다. [Spring Framework 6.2 · 필드 포맷팅](https://docs.spring.io/spring-framework/reference/6.2/core/validation/format.html) · [Spring Framework 6.2 · 날짜와 시간 변환](https://docs.spring.io/spring-framework/reference/6.2/web/webmvc/mvc-config/conversion.html)

## 3. JSON 변환과 폼 변환의 적용 위치

경로, 쿼리, 폼의 문자열 변환과 Thymeleaf 폼의 필드 출력에는 Spring의 변환 및 포맷팅 설정이 사용된다. JSON 요청과 응답의 형식은 [HTTP 메시지 컨버터](06_spring_mvc_request_binding_and_http_responses.md)가 결정한다. 예를 들어 Jackson이 JSON 본문을 읽는 경우 날짜의 JSON 형식은 Jackson 쪽에서 설정한다. [Thymeleaf 3.1 · 변환 서비스](https://www.thymeleaf.org/doc/tutorials/3.1/thymeleafspring.html) · [Spring Framework 6.2 · @RequestBody](https://docs.spring.io/spring-framework/reference/6.2/web/webmvc/mvc-controller/ann-methods/requestbody.html)
