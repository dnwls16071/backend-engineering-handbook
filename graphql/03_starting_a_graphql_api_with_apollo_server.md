# Starting a GraphQL API with Apollo Server

첫 서버는 SDL과 resolver만으로 GraphQL 실행을 확인한다. Apollo Server 5의 Node와 GraphQL.js 요구 버전에 맞춰 설치한다. [Apollo Server · Getting Started](https://www.apollographql.com/docs/apollo-server/getting-started) · [Apollo Server 5 · Migration](https://www.apollographql.com/docs/apollo-server/migration)

## 1. 로컬 서버를 실행한다

빈 실습 디렉터리에서 패키지를 설치하고 코드를 hello.mjs에 저장한 뒤 node hello.mjs를 실행한다. 4000번 포트는 루프백에만 바인딩한다. [Apollo Server · Getting Started](https://www.apollographql.com/docs/apollo-server/getting-started) · [Apollo Server 5 · Migration](https://www.apollographql.com/docs/apollo-server/migration) · [Apollo Server · Standalone API](https://www.apollographql.com/docs/apollo-server/api/standalone) · [Apollo Server 5.5.2 · Release](https://github.com/apollographql/apollo-server/releases/tag/%40apollo%2Fserver%405.5.2)

```bash
npm init -y
npm install --save-exact @apollo/server@5.5.2 graphql@16.15.0
```

```javascript
// hello.mjs
import { ApolloServer } from "@apollo/server";
import { startStandaloneServer } from "@apollo/server/standalone";

const server = new ApolloServer({
  typeDefs: `
    type Query {
      """받은 이름으로 인사합니다."""
      greeting(name: String!): String!
    }
  `,
  resolvers: { Query: { greeting: (_root, { name }) => "안녕하세요, " + name } },
});
const { url } = await startStandaloneServer(server, {
  listen: { host: "127.0.0.1", port: 4000 },
});
console.log(url);
```

## 2. 쿼리 문자열과 Variables를 함께 전달한다

별도 셸에서 POST 요청을 보내 data.greeting을 확인한다. 필드 이름이나 인자 타입을 바꿔 검증 오류와 resolver 오류가 어디서 발생하는지 구분한다. [GraphQL over HTTP · Draft](https://graphql.github.io/graphql-over-http/draft/) · [GraphQL · Queries](https://graphql.org/learn/queries/) · [Apollo Server · Error Handling](https://www.apollographql.com/docs/apollo-server/data/errors)

```bash
curl -fsS http://127.0.0.1:4000/ -H 'Content-Type: application/json' \
  --data-binary '{"query":"query Greet($name: String!) { greeting(name: $name) }","variables":{"name":"개발자"}}'
```
