# WebFlux Controllers, Server-Sent Events, and WebSockets

## 1. 애너테이션 컨트롤러에서 상태와 본문 결정하기

Spring WebFlux에서도 `@RestController`와 `@GetMapping`을 사용한다. 조회 결과가 있어야 상태를 정할 수 있다면 `Mono<ResponseEntity<T>>`를 반환한다. `ResponseEntity<Flux<T>>`는 상태와 헤더를 먼저 결정하고 본문을 여러 값으로 제공하는 형태다. [Spring Framework 6.2 · Return Values](https://docs.spring.io/spring-framework/reference/6.2/web/webflux/controller/ann-methods/return-types.html) · [Spring Framework 6.2 · ResponseEntity](https://docs.spring.io/spring-framework/reference/6.2/web/webflux/controller/ann-methods/responseentity.html)

아래 컨트롤러에는 상품 ID를 입력받아 상품을 리액티브 타입으로 조회하는 구성 요소를 주입한다. 빈 조회는 `404 Not Found`로 변환한다. 조회 실패는 오류 정책에 따라 처리할 수 있도록 흐름에 남긴다.

```java
import java.time.Duration;
import java.util.function.Function;

import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.http.codec.ServerSentEvent;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RestController;
import reactor.core.publisher.Flux;
import reactor.core.publisher.Mono;

@RestController
public class CatalogHttpController {

    public record Item(String id, String name) {
    }

    private final Function<String, Mono<Item>> lookup;

    public CatalogHttpController(Function<String, Mono<Item>> lookup) {
        this.lookup = lookup;
    }

    @GetMapping("/items/{id}")
    public Mono<ResponseEntity<Item>> item(@PathVariable("id") String id) {
        return lookup.apply(id)
                .map(ResponseEntity::ok)
                .defaultIfEmpty(ResponseEntity.notFound().build());
    }

    @GetMapping(path = "/catalog/events", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    public Flux<ServerSentEvent<String>> events() {
        return Flux.interval(Duration.ofSeconds(15))
                .map(tick -> ServerSentEvent.builder("catalog connection alive")
                        .event("heartbeat")
                        .build());
    }
}
```

## 2. Server-Sent Events로 서버 이벤트 전달하기

SSE는 HTTP 응답을 `text/event-stream`으로 열어 놓고 서버에서 브라우저로 이벤트를 전달한다. 브라우저의 `EventSource`는 연결이 끊기면 다시 연결을 시도할 수 있다. 응용 이벤트에 `id`를 보내면 재접속 시 브라우저가 `Last-Event-ID`를 전달할 수 있다. 누락분을 재전송하는 정책과 이벤트 보관은 서버에서 구현한다. 위 예제는 주기적 연결 확인 메시지만 보내므로 재생 ID를 부여하지 않는다. [WHATWG HTML · Server-Sent Events](https://html.spec.whatwg.org/multipage/server-sent-events.html) · [Spring Framework 6.2 · WebFlux Return Values](https://docs.spring.io/spring-framework/reference/6.2/web/webflux/controller/ann-methods/return-types.html)

## 3. WebSocket으로 양방향 메시지 교환하기

HTTP/1.1 WebSocket 연결은 HTTP 업그레이드 요청과 `101 Switching Protocols` 결과로 수립된다. 연결된 뒤에는 클라이언트와 서버가 각각 메시지를 보낼 수 있다. 서버에서 브라우저로 알림을 전달하는 용도에는 SSE, 하나의 연결에서 양쪽이 메시지를 주고받는 용도에는 WebSocket을 사용할 수 있다. [RFC 6455 · Opening Handshake](https://www.rfc-editor.org/rfc/rfc6455.html#section-4) · [Spring Framework 6.2 · WebFlux WebSockets](https://docs.spring.io/spring-framework/reference/6.2/web/webflux-websocket.html)

`WebSocketHandler`에서 `session.receive()`는 수신 스트림을, `session.send(...)`는 발신 스트림을 연결한 완료 신호를 제공한다. 아래 Echo 예제는 수신한 텍스트를 그대로 돌려보낸다. `SimpleUrlHandlerMapping`에 `/ws/catalog` 경로와 핸들러를 등록하고, WebFlux의 `WebSocketHandlerAdapter`가 이 매핑을 처리하도록 구성한다. [Spring Framework 6.2 · WebSocketHandler](https://docs.spring.io/spring-framework/reference/6.2/web/webflux-websocket.html)

```java
import org.springframework.web.reactive.socket.WebSocketHandler;
import org.springframework.web.reactive.socket.WebSocketMessage;
import org.springframework.web.reactive.socket.WebSocketSession;
import reactor.core.publisher.Mono;

public class CatalogSocket implements WebSocketHandler {

    @Override
    public Mono<Void> handle(WebSocketSession session) {
        return session.send(session.receive()
                .filter(message -> message.getType() == WebSocketMessage.Type.TEXT)
                .map(message -> session.textMessage(message.getPayloadAsText())));
    }
}
```

장시간 연결에서는 클라이언트가 느리거나 연결이 끊겼을 때 상류 발행자와 연결별 대기 데이터를 어떻게 정리할지 정한다. HTTP 응답으로 이미 본문을 전송하기 시작했다면 스트림 중간 오류는 상태 코드를 바꾸는 방식으로 전달하기 어렵다. [Spring Framework 6.2 · WebFlux WebSocket Handling](https://docs.spring.io/spring-framework/reference/6.2/web/webflux-websocket.html) · [Spring Framework 6.2 · WebFlux Return Values](https://docs.spring.io/spring-framework/reference/6.2/web/webflux/controller/ann-methods/return-types.html)
