# Spring MVC Messages and Internationalization

## 1. 화면 문구를 메시지 코드로 관리하기

Spring Boot에서는 기본 이름이 `messages`인 리소스 번들을 `MessageSource`로 사용할 수 있다. 자동 설정을 사용하려면 클래스패스에 `messages.properties` 같은 기본 번들이 있어야 한다. 언어별 번들은 `messages_ko.properties`처럼 로케일 접미사를 사용한다. [Spring Boot 3.5 · 국제화](https://docs.spring.io/spring-boot/3.5/reference/features/internationalization.html)

| 번들 | 예 |
| --- | --- |
| `messages.properties` | `notes.title=Notes`, `notes.summary={0} notes` |
| `messages_ko.properties` | `notes.title=메모`, `notes.summary=메모 {0}개` |

Thymeleaf에서는 `#{notes.title}`로 메시지를 읽고, `#{notes.summary(${noteCount})}`로 메시지의 `{0}`에 값을 전달한다. Java 코드에서 같은 문구가 필요하면 `messageSource.getMessage("notes.title", null, locale)`로 조회한다. 기본 문구를 받는 오버로드를 사용하면 키를 찾지 못했을 때 지정한 기본 문구를 사용할 수 있다. [Thymeleaf 3.1 · 메시지 표현식](https://www.thymeleaf.org/doc/tutorials/3.1/usingthymeleaf.html#messages) · [Spring Framework 6.2 · MessageSource](https://docs.spring.io/spring-framework/reference/6.2/core/beans/context-introduction.html#context-functionality-messagesource)

```html
<h1 th:text="#{notes.title}">Notes</h1>
<p th:text="#{notes.summary(${noteCount})}">0 notes</p>
```

## 2. 요청에 적용할 로케일 결정하기

| 방식 | 로케일을 얻는 위치 |
| --- | --- |
| `AcceptHeaderLocaleResolver` | 브라우저가 보낸 `Accept-Language` 헤더 |
| `CookieLocaleResolver` | 사용자가 고른 언어를 저장한 쿠키 |
| `SessionLocaleResolver` | 현재 HTTP 세션의 로케일 속성 |

예를 들어 `ko-KR`로 조회하면 메시지 번들의 `messages_ko_KR.properties`, `messages_ko.properties`, 기본 번들 순으로 후보를 좁힐 수 있다. 서버의 시스템 로케일에 따라 달라지는 폴백을 끄려면 Boot에서 `spring.messages.fallback-to-system-locale=false`를 설정한다. [Spring Boot 3.5 · 국제화](https://docs.spring.io/spring-boot/3.5/reference/features/internationalization.html) · [Spring Framework 6.2 · LocaleResolver](https://docs.spring.io/spring-framework/reference/6.2/web/webmvc/mvc-servlet/localeresolver.html)

언어 선택 UI를 붙일 때는 쿠키 또는 세션 기반 리졸버와 `LocaleChangeInterceptor`를 구성할 수 있다. 예를 들어 `?lang=ko`를 해석해 선택을 다음 요청에 유지한다. 헤더 기반 리졸버에서는 브라우저가 보낸 값을 읽으며 서버에서 언어 설정을 갱신하려면 변경을 지원하는 리졸버를 사용한다. [Spring Framework 6.2 · LocaleResolver와 LocaleChangeInterceptor](https://docs.spring.io/spring-framework/reference/6.2/web/webmvc/mvc-servlet/localeresolver.html)
