# Managing GraphQL Errors and Codes

GraphQL 응답의 errors에는 메시지와 선택적으로 path·extensions를 둘 수 있다. 클라이언트가 분기할 업무 코드는 사람이 읽는 메시지와 분리한다. [GraphQL · September 2025 Specification](https://spec.graphql.org/September2025/) · [Apollo Server · Error Handling](https://www.apollographql.com/docs/apollo-server/data/errors)

## 1. 예상한 오류와 내부 예외를 분리한다

아래를 blog-errors.mjs로 저장한다. 인증 실패·입력 오류·존재하지 않는 리소스는 명시적 코드를 사용한다. 예기치 않은 오류는 서버 로그에 필요한 정보만 남기고 응답에는 내부 구현을 드러내지 않는다. [Apollo Server · Error Handling](https://www.apollographql.com/docs/apollo-server/data/errors) · [Apollo Server · Context](https://www.apollographql.com/docs/apollo-server/data/context) · [GraphQL · Security](https://graphql.org/learn/security/)

```javascript
// blog-errors.mjs
const known = new Set([
  "BAD_USER_INPUT", "UNAUTHENTICATED", "NOT_FOUND",
  "GRAPHQL_PARSE_FAILED", "GRAPHQL_VALIDATION_FAILED",
]);

export function formatBlogError(error) {
  const code = error.extensions?.code;
  if (known.has(code)) return { ...error, extensions: { code } };
  return {
    message: "요청 처리 중 오류가 발생했습니다.",
    ...(error.path ? { path: error.path } : {}),
    extensions: { code: "INTERNAL_SERVER_ERROR" },
  };
}
```

## 2. 실행 오류와 HTTP 상태를 함께 읽는다

검증 단계 오류와 실행 중 필드 오류를 구분한다. 실행 오류 뒤 다른 필드의 data가 함께 올 수 있고 Non-Null 오류가 전파되면 결과가 null이 될 수 있다. HTTP 상태 처리에는 전송 방식과 응답 미디어 타입의 계약도 반영한다. [GraphQL · September 2025 Specification](https://spec.graphql.org/September2025/) · [GraphQL over HTTP · Draft](https://graphql.github.io/graphql-over-http/draft/) · [Apollo Server · Error Handling](https://www.apollographql.com/docs/apollo-server/data/errors)
