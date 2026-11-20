# Building Spring AI RAG Chatbots with Elasticsearch

RAG는 질문과 관련된 문서를 검색해 모델에 전달한다. 배송 정책이 바뀌면 원문과 검색 인덱스를 갱신할 수 있다. 답변 품질은 원문, 청크, 임베딩, 검색 조건에 함께 영향을 받는다.

## 1. 문서 적재와 질문 처리

| 단계 | 처리 |
| --- | --- |
| Extract | `TextReader`가 원문을 `Document`로 변환한다. |
| Transform | `TokenTextSplitter`가 원문을 분할한다. 각 청크에 원문 ID와 분할 순서를 기록한다. |
| Load | `VectorStore.add`가 청크를 임베딩하고 저장한다. |
| Retrieve and generate | `QuestionAnswerAdvisor`가 질문과 유사한 청크를 찾고 채팅 요청에 넣는다. |

[채팅 API 예제](04_building_chat_apis_with_openai_and_ollama.md)에 다음 의존성을 추가한다. 먼저 인메모리 저장소로 같은 흐름을 실행한다.

```groovy
implementation 'org.springframework.ai:spring-ai-vector-store-advisor'
```

한국어 정책 검색에 사용할 임베딩 모델을 Ollama에 추가하고 `src/main/resources/application-rag.properties`에 설정한다. 적재와 검색에 같은 모델을 사용한다.

```bash
docker exec spring-ai-ollama ollama pull nomic-embed-text-v2-moe
```

```properties
spring.ai.model.embedding=ollama
spring.ai.ollama.embedding.model=nomic-embed-text-v2-moe
```

`src/main/resources/policies/shipping.txt`에 다음 실습 데이터를 저장한다.

```text
배송 정책
결제가 완료되면 영업일 기준 2일 이내에 상품을 발송합니다.
단순 변심에 의한 반품은 상품을 받은 날부터 7일 이내에 신청할 수 있습니다.
```

## 2. ETL과 벡터 저장소

```java
package demo.ai;

import java.util.List;
import java.util.stream.IntStream;

import org.springframework.ai.document.Document;
import org.springframework.ai.embedding.EmbeddingModel;
import org.springframework.ai.reader.TextReader;
import org.springframework.ai.transformer.splitter.TokenTextSplitter;
import org.springframework.ai.vectorstore.SimpleVectorStore;
import org.springframework.ai.vectorstore.VectorStore;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.ApplicationRunner;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Profile;
import org.springframework.core.annotation.Order;
import org.springframework.core.io.Resource;

@Configuration
@Profile("rag")
class RagIndexConfiguration {

    @Bean
    @Profile("!elastic")
    VectorStore policyStore(EmbeddingModel embeddingModel) {
        return SimpleVectorStore.builder(embeddingModel).build();
    }

    @Bean
    @Profile("index")
    @Order(0)
    ApplicationRunner indexPolicies(VectorStore store, @Value("classpath:policies/shipping.txt") Resource resource) {
        return args -> store.add(policyChunks(resource));
    }

    List<Document> policyChunks(Resource resource) {
        List<Document> documents = new TextReader(resource).get();
        List<Document> chunks = TokenTextSplitter.builder().build().apply(documents);

        return IntStream.range(0, chunks.size())
                .mapToObj(index -> Document.builder()
                        .id("shipping-policy-" + index)
                        .text(chunks.get(index).getText())
                        .metadata(chunks.get(index).getMetadata())
                        .metadata("category", "shipping")
                        .metadata("locale", "ko-KR")
                        .metadata("chunk", index)
                        .build())
                .toList();
    }
}
```

같은 문서를 다시 적재할 때 동일한 청크 ID를 쓴다. 원문이 짧아져 청크 수가 줄면 예전 청크를 명시적으로 삭제하거나 새 인덱스를 만들어 교체한다. 인메모리 저장소는 앱을 종료하면 사라지므로 실행 시 `index` 프로파일을 활성화한다. [Spring AI ETL Pipeline](https://docs.spring.io/spring-ai/reference/2.0/api/etl-pipeline.html)

## 3. RAG 서비스와 CLI·REST 호출

```java
package demo.ai;

import org.springframework.ai.chat.client.ChatClient;
import org.springframework.ai.chat.client.advisor.vectorstore.QuestionAnswerAdvisor;
import org.springframework.ai.chat.model.ChatModel;
import org.springframework.ai.vectorstore.SearchRequest;
import org.springframework.ai.vectorstore.VectorStore;
import org.springframework.stereotype.Service;

import org.springframework.context.annotation.Profile;

@Service
@Profile("rag")
class RagChat {

    private final ChatClient client;

    RagChat(ChatModel model, VectorStore store) {
        var search = SearchRequest.builder()
                .topK(4)
                .similarityThreshold(0.7)
                .filterExpression("category == 'shipping' && locale == 'ko-KR'")
                .build();

        client = ChatClient.builder(model)
                .defaultSystem("검색된 정책을 근거로만 답하세요. 근거가 부족하면 확인할 수 없다고 답하세요.")
                .defaultAdvisors(QuestionAnswerAdvisor.builder(store).searchRequest(search).build())
                .build();
    }

    String answer(String question) {
        return client.prompt().user(question).call().content();
    }
}
```

```java
package demo.ai;

import org.springframework.boot.ApplicationRunner;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Profile;
import org.springframework.core.annotation.Order;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

@RestController
@Profile("rag")
class PolicyController {

    private final RagChat chat;

    PolicyController(RagChat chat) {
        this.chat = chat;
    }

    @PostMapping("/api/policy")
    Answer answer(@RequestBody Question request) {
        return new Answer(chat.answer(request.text()));
    }

    record Question(String text) {}
    record Answer(String answer) {}
}

@Configuration
@Profile("rag & rag-cli")
class RagCliConfiguration {

    @Bean
    @Order(100)
    ApplicationRunner askPolicy(RagChat chat) {
        return args -> {
            var questions = args.getOptionValues("policy.question");
            if (questions == null || questions.size() != 1) {
                throw new IllegalArgumentException("Use --policy.question=<question>");
            }
            System.out.println(chat.answer(questions.get(0)));
        };
    }
}
```

```bash
# CLI
./gradlew bootRun --args='--spring.profiles.active=ollama,rag,index,rag-cli --spring.main.web-application-type=none --policy.question="반품은 언제까지 신청할 수 있나요?"'

# REST 서버
./gradlew bootRun --args='--spring.profiles.active=ollama,rag,index'

curl http://localhost:8080/api/policy \
  -H 'Content-Type: application/json' \
  -d '{"text":"반품은 언제까지 신청할 수 있나요?"}'
```

검색 결과와 모델 답변을 따로 확인한다. 먼저 반품 질문에 원문 청크가 검색되는지 확인하고, 다음으로 원문에 없는 수리비 질문에 답변을 보류하는지 확인한다. `0.7`은 실습 시작값이다. 검색 모델과 문서가 바뀌면 실제 질문과 관련 청크를 기준으로 다시 조정한다. [Spring AI RAG](https://docs.spring.io/spring-ai/reference/2.0/api/retrieval-augmented-generation.html)

## 4. Elasticsearch로 전환

```groovy
implementation 'org.springframework.ai:spring-ai-starter-vector-store-elasticsearch'
```

공통 `application.properties`에 `spring.ai.vectorstore.type=none`을 추가한다. 아래 `elastic` 프로파일에서 Elasticsearch 저장소의 자동 설정을 켠다.

```bash
docker run -d --name spring-ai-elasticsearch \
  -p 127.0.0.1:9200:9200 \
  -e discovery.type=single-node \
  -e xpack.security.enabled=false \
  docker.elastic.co/elasticsearch/elasticsearch:9.4.8

curl http://127.0.0.1:9200
```

위 명령은 루프백에 바인딩한 로컬 실습용이다. `src/main/resources/application-elastic.properties`를 작성한다.

```properties
spring.elasticsearch.uris=http://127.0.0.1:9200
spring.ai.vectorstore.type=elasticsearch
spring.ai.vectorstore.elasticsearch.initialize-schema=true
spring.ai.vectorstore.elasticsearch.index-name=shipping-policies-v1
spring.ai.vectorstore.elasticsearch.similarity=cosine
spring.ai.vectorstore.elasticsearch.dimensions=768
```

```bash
./gradlew bootRun --args='--spring.profiles.active=ollama,rag,elastic,index'
```

적재 후 새 문서가 검색될 때까지 인덱스가 새로고침될 시간을 준다. 동일한 Elasticsearch 인스턴스에서 자료가 이미 적재되어 있으면 이후 서버 실행에서 `index` 프로파일을 생략할 수 있다. 임베딩 차원이나 모델을 바꿀 때는 인덱스를 새로 만들고 원문을 다시 임베딩한다. [Spring AI Elasticsearch Vector Store](https://docs.spring.io/spring-ai/reference/2.0/api/vectordbs/elasticsearch.html), [Ollama nomic-embed-text-v2-moe](https://www.ollama.com/library/nomic-embed-text-v2-moe), [Elastic Docker 이미지](https://www.docker.elastic.co/r/elasticsearch/elasticsearch)
