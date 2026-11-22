# Building an AI Search API with Express

Express는 검색어를 검사하고, Ollama에서 질의 벡터를 만든 뒤 Chroma에 검색을 요청한다. 응답에는 인용에 사용할 청크 ID와 출처를 포함한다. [Express 5 · API](https://expressjs.com/en/5x/api/) · [Node.js 24.5 · Global APIs](https://nodejs.org/download/release/v24.5.0/docs/api/globals.html) · [Ollama · Generate Embeddings](https://docs.ollama.com/api/embed) · [Chroma · Query Collection REST API](https://docs.trychroma.com/reference/chroma-api/record/query-collection)

## 1. 검색 API에 입력과 권한 경계를 둔다

Node.js 24의 빈 실습 디렉터리에서 npm init -y와 npm install --save-exact express@5.1.0을 실행한다. 아래를 search.cjs로 저장한다. 컬렉션 ID는 [인제스트 실습](21_building_a_rag_ingestion_pipeline.md)에서 얻으며, 이 예제는 요청자가 바꿀 수 없는 공개 범위만 검색한다. [Express 5 · API](https://expressjs.com/en/5x/api/) · [Chroma · Query Collection REST API](https://docs.trychroma.com/reference/chroma-api/record/query-collection) · [Chroma · Metadata Filtering](https://docs.trychroma.com/docs/querying-collections/metadata-filtering) · [OWASP · RAG Security](https://cheatsheetseries.owasp.org/cheatsheets/RAG_Security_Cheat_Sheet.html)

```javascript
// search.cjs
const express = require("express");

const chroma = process.env.CHROMA_URL ?? "http://127.0.0.1:8000";
const ollama = process.env.OLLAMA_URL ?? "http://127.0.0.1:11434";

async function postJson(base, route, payload, timeout = 10_000) {
  const response = await fetch(new URL(route, base), {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(payload),
    signal: AbortSignal.timeout(timeout),
  });
  if (!response.ok) throw new Error("upstream response " + response.status);
  return response.json();
}

async function searchPublic(query, topK) {
  const id = process.env.CHROMA_COLLECTION_ID;
  if (!id) throw new Error("collection ID is required");
  const { embeddings } = await postJson(ollama, "/api/embed", {
    model: "embeddinggemma", input: [query], truncate: false,
  });
  const path = "/api/v2/tenants/default_tenant/databases/default_database/collections/"
    + encodeURIComponent(id) + "/query";
  const found = await postJson(chroma, path, {
    query_embeddings: embeddings, n_results: topK,
    where: { visibility: "public" },
    include: ["documents", "metadatas", "distances"],
  });
  return found.ids[0].map((chunkId, index) => ({
    chunkId,
    text: found.documents[0][index],
    source: found.metadatas[0][index].source,
    distance: found.distances[0][index],
  }));
}

function createApp({ answerFromHits } = {}) {
  const app = express();
  app.use(express.json({ limit: "16kb" }));

  const handle = (makeResponse) => async (req, res) => {
    const query = typeof req.body?.query === "string" ? req.body.query.trim() : "";
    const topK = req.body?.topK ?? 3;
    if (!query || query.length > 400 || !Number.isInteger(topK) || topK < 1 || topK > 10) {
      return res.status(400).json({ error: "invalid query or topK" });
    }
    const hits = await searchPublic(query, topK);
    return res.json(await makeResponse(query, hits));
  };

  app.post("/search", handle((_query, hits) => ({ hits })));
  if (answerFromHits) app.post("/rag/answer", handle(answerFromHits));

  app.use((error, _req, res, next) => {
    if (res.headersSent) return next(error);
    if (error.status === 400) return res.status(400).json({ error: "invalid JSON" });
    if (error.status === 413) return res.status(413).json({ error: "body too large" });
    return res.status(502).json({ error: "upstream unavailable or invalid" });
  });
  return app;
}

if (require.main === module) createApp().listen(3000, "127.0.0.1");

module.exports = { createApp, postJson };
```

## 2. 앱과 검색 의존성의 실패를 구분한다

서버 환경의 주소를 써서 Ollama와 Chroma에 연결하며, 사용자 요청에는 외부 주소나 권한 조건을 받지 않는다. 검색 실패는 빈 성공 결과로 바꾸지 않는다. 400·413 및 업스트림 실패를 구별하고, 운영에서 원인·지연은 비공개 메타데이터로 관측한다. [Express 5 · API](https://expressjs.com/en/5x/api/) · [Express 5 · Error Handling](https://expressjs.com/en/guide/error-handling/) · [Node.js 24.5 · Global APIs](https://nodejs.org/download/release/v24.5.0/docs/api/globals.html) · [OWASP · RAG Security](https://cheatsheetseries.owasp.org/cheatsheets/RAG_Security_Cheat_Sheet.html)
