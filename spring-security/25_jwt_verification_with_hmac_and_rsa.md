# JWT Verification with HMAC and RSA

## 1. 서명에 사용하는 키와 검증에 사용하는 키

| 방식 | 발급 시 키 | 검증 시 키 |
| --- | --- | --- |
| HMAC `HS256` | 공유 비밀 키 | 동일한 비밀 키 |
| RSA `RS256` | RSA 개인 키 | 대응 공개 키 |

HMAC 비밀 키를 가진 서버는 검증과 생성 모두 가능하므로 비밀을 공유할 범위를 정한다. `HS256`에는 최소 256비트 키를 사용한다. RSA에서는 발급자에 개인 키를 두고 리소스 서버에는 공개 키를 배포할 수 있다. `RS256`에 사용하는 RSA 키는 2048비트 이상이어야 한다. [RFC 7518 · JSON Web Algorithms](https://www.rfc-editor.org/rfc/rfc7518.html)

## 2. 알고리즘을 서버 설정에서 고정하기

아래 예제는 두 배포 방식의 디코더 팩터리다. 각각 신뢰한 경로에서 받은 키를 넣고 [issuer와 audience 검증](24_jwt_validation_fundamentals.md)을 연결한다. 서비스는 인가 서버와 합의한 구성 하나를 사용한다. [RFC 8725 · Algorithm Verification](https://www.rfc-editor.org/rfc/rfc8725.html) · [Spring Security 6.5 · Trusted Algorithms and Keys](https://docs.spring.io/spring-security/reference/6.5/servlet/oauth2/resource-server/jwt.html)

```java
import java.security.interfaces.RSAPublicKey;
import javax.crypto.SecretKey;

import org.springframework.security.oauth2.jose.jws.MacAlgorithm;
import org.springframework.security.oauth2.jose.jws.SignatureAlgorithm;
import org.springframework.security.oauth2.jwt.JwtDecoder;
import org.springframework.security.oauth2.jwt.NimbusJwtDecoder;

public class CatalogJwtDecoders {

    public static JwtDecoder rsa(RSAPublicKey key, String issuer, String audience) {
        var decoder = NimbusJwtDecoder.withPublicKey(key)
                .signatureAlgorithm(SignatureAlgorithm.RS256)
                .build();
        decoder.setJwtValidator(CatalogJwtValidation.claims(issuer, audience));
        return decoder;
    }

    public static JwtDecoder hmac(SecretKey key, String issuer, String audience) {
        var decoder = NimbusJwtDecoder.withSecretKey(key)
                .macAlgorithm(MacAlgorithm.HS256)
                .build();
        decoder.setJwtValidator(CatalogJwtValidation.claims(issuer, audience));
        return decoder;
    }
}
```

공개 키를 교체해야 할 때는 신뢰한 JWK Set에서 `kid`에 해당하는 키를 선택할 수 있다. 새 키를 공개하고 구 키로 발급한 토큰의 유효 기간을 고려해 공개 키를 제거한다. JWK Set 엔드포인트를 통해 공개할 값은 공개 키로 제한한다. [RFC 7517 · JSON Web Key](https://www.rfc-editor.org/rfc/rfc7517.html) · [Spring Security 6.5 · JWK Set and Key Rotation](https://docs.spring.io/spring-security/reference/6.5/servlet/oauth2/resource-server/jwt.html)
