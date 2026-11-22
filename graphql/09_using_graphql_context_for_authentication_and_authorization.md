# Using GraphQL Context for Authentication and Authorization

Apollo의 요청 컨텍스트는 확인된 사용자와 요청마다 생성한 로더를 resolver에 전달한다. 실제로 읽거나 수정할 수 있는 리소스의 범위는 서비스 쿼리에서 강제한다. [Apollo Server · Context](https://www.apollographql.com/docs/apollo-server/data/context) · [GraphQL · Authorization](https://graphql.org/learn/authorization/) · [GraphQL · DataLoader](https://github.com/graphql/dataloader/tree/v2.2.3)

## 1. 인증 경계에서 확인한 신원만 넘긴다

다음은 인증 어댑터를 주입하는 모듈이다. 실제 어댑터는 토큰 서명·만료 등 필요한 조건을 검증한 뒤 사용자 ID를 반환한다. 헤더가 없으면 공개 조회를 허용하고, 유효하지 않은 인증 헤더는 거절한다. [Apollo Server · Context](https://www.apollographql.com/docs/apollo-server/data/context) · [GraphQL · Authorization](https://graphql.org/learn/authorization/) · [Apollo Server · Error Handling](https://www.apollographql.com/docs/apollo-server/data/errors)

```javascript
// blog-context.mjs
import { GraphQLError } from "graphql";
import { createAuthorLoader } from "./author-loader.mjs";

export function requestContext(prisma, viewer = null) {
  return { prisma, viewer, authorLoader: createAuthorLoader(prisma) };
}

export function httpContext(prisma, verifyToken) {
  return async ({ req }) => {
    const header = req.headers.authorization;
    if (header === undefined) return requestContext(prisma);

    const token = typeof header === "string" && /^Bearer ([^\s]+)$/i.exec(header)?.[1];
    const viewer = token ? await verifyToken(token) : null;
    if (!viewer?.id) throw new GraphQLError("인증을 확인할 수 없습니다.", {
      extensions: { code: "UNAUTHENTICATED", http: { status: 401 } },
    });
    return requestContext(prisma, viewer);
  };
}
```

## 2. 스키마와 resolver에 요청 컨텍스트를 연결한다

아래는 로컬 공개 조회 서버다. 파일을 저장한 뒤 프로젝트 루트에서 DATABASE_URL을 설정하고 node blog-server.mjs를 실행한다. 공개 조회 예제의 인증 어댑터는 토큰을 승인하지 않는다. 로그인 흐름을 테스트하는 방법은 [테스트 문서](14_testing_graphql_services_and_operations.md)에 있다. [Apollo Server · Getting Started](https://www.apollographql.com/docs/apollo-server/getting-started) · [Apollo Server · Standalone API](https://www.apollographql.com/docs/apollo-server/api/standalone) · [Apollo Server · Context](https://www.apollographql.com/docs/apollo-server/data/context) · [Apollo Server · Integration Testing](https://www.apollographql.com/docs/apollo-server/testing/testing)

```javascript
// blog-server.mjs
import { readFileSync } from "node:fs";
import { ApolloServer } from "@apollo/server";
import { startStandaloneServer } from "@apollo/server/standalone";
import { PrismaClient } from "@prisma/client";
import { resolvers } from "./blog-resolvers.mjs";
import { httpContext } from "./blog-context.mjs";
import { formatBlogError } from "./blog-errors.mjs";

const prisma = new PrismaClient();
const typeDefs = readFileSync(new URL("./blog.graphql", import.meta.url), "utf8");
const server = new ApolloServer({
  typeDefs, resolvers, formatError: formatBlogError, includeStacktraceInErrorResponses: false,
});
const { url } = await startStandaloneServer(server, {
  listen: { host: "127.0.0.1", port: 4000 },
  context: httpContext(prisma, async () => null),
});
console.log(url);
```

소유권 검사는 mutation의 WHERE 조건에 포함한다. 여러 진입점에서 같은 업무를 호출한다면 서비스 계층에 정책을 모으고, 공개 필드와 제한 필드도 스키마·resolver에서 일관되게 검증한다. [GraphQL · Authorization](https://graphql.org/learn/authorization/) · [Prisma ORM 6 · CRUD](https://www.prisma.io/docs/orm/v6/prisma-client/queries/crud) · [GraphQL · Security](https://graphql.org/learn/security/)
