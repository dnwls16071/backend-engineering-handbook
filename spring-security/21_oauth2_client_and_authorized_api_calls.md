# OAuth 2.0 Client and Authorized API Calls

## 1. 외부 API 호출에 승인된 클라이언트 사용하기

`OAuth2AuthorizedClientManager`는 클라이언트와 주체를 기준으로 토큰을 얻거나 다시 인가받는 흐름을 조정한다. 지원할 권한 부여 유형은 `OAuth2AuthorizedClientProvider`에 구성한다. 웹 요청에서 사용하는 `DefaultOAuth2AuthorizedClientManager`와, 스케줄러처럼 서블릿 요청 밖에서 쓸 수 있는 `AuthorizedClientServiceOAuth2AuthorizedClientManager`를 실행 범위에 맞춰 고른다. [Spring Security 6.5 · Core Interfaces and Classes](https://docs.spring.io/spring-security/reference/6.5/servlet/oauth2/client/core.html)

| API 호출 목적 | 요청에 사용할 권한 |
| --- | --- |
| 현재 사용자를 대신한 조회 | 그 사용자의 등록과 토큰을 선택한다. |
| 배치 작업이나 서비스 간 조회 | 기밀 클라이언트의 `client_credentials` 권한과 별도 주체 식별자를 사용한다. |
| 기존 권한으로 토큰 갱신 | 리프레시 토큰이 있고 제공자가 지원하면 재인가에 사용한다. |

## 2. RestClient에서 Bearer 헤더 사용하기

`OAuth2ClientHttpRequestInterceptor`는 지정한 등록 ID로 승인된 클라이언트를 찾아 외부 요청에 Bearer 헤더를 붙인다. 아래 클라이언트는 [등록 설정](19_oauth2_client_registration_and_authorized_client_storage.md)의 `catalog-ui`를 선택하고 목적지를 고정한다. [Spring Security 6.5 · Authorized Client Features](https://docs.spring.io/spring-security/reference/6.5/servlet/oauth2/client/authorized-clients.html)

```java
import org.springframework.security.oauth2.client.OAuth2AuthorizedClientManager;
import org.springframework.security.oauth2.client.web.client.OAuth2ClientHttpRequestInterceptor;
import org.springframework.web.client.RestClient;

import static org.springframework.security.oauth2.client.web.client.RequestAttributeClientRegistrationIdResolver.clientRegistrationId;

public class CatalogApiClient {

    private final RestClient client;

    public CatalogApiClient(RestClient.Builder builder, OAuth2AuthorizedClientManager manager) {
        this.client = builder.clone()
                .requestInterceptor(new OAuth2ClientHttpRequestInterceptor(manager))
                .build();
    }

    public String items() {
        return client.get()
                .uri("https://catalog-api.example.com/items")
                .attributes(clientRegistrationId("catalog-ui"))
                .retrieve()
                .body(String.class);
    }
}
```

컨트롤러에서 토큰과 부여 범위를 직접 사용해야 하면 `@RegisteredOAuth2AuthorizedClient`로 승인된 클라이언트를 받을 수 있다. 외부 API가 토큰 무효를 알리는 경우 처리 방식은 실패 핸들러에서 정할 수 있다. 갱신이나 재요청이 가능한 오류를 구분하고, 토큰이 전송되는 대상과 등록 ID를 함께 검증한다. [Spring Security 6.5 · Authorized Client Features](https://docs.spring.io/spring-security/reference/6.5/servlet/oauth2/client/authorized-clients.html)
