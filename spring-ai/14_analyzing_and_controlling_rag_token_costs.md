# Analyzing and Controlling RAG Token Costs

`topK`를 4에서 20으로 올리면 검색기가 반환할 수 있는 청크 상한이 커진다. 실제 입력 토큰은 필터와 유사도 조건을 통과한 청크 수, 각 청크의 길이, 프롬프트 구성에 따라 달라진다. 동일한 질문과 문서에서 청크 수만 바꿔 비용과 답변 품질을 비교한다.

## 1. 비교용 문서와 엔드포인트

[인메모리 RAG 프로젝트](07_building_rag_chatbots_with_elasticsearch.md)에 다음 클래스를 추가한다. `cost-lab` 프로파일은 인메모리 저장소에 테스트용 청크 24개를 적재한다. 두 요청에서 검색 필터, 시스템 프롬프트, 모델, 질문을 고정한다. 응답에는 Advisor가 선택한 청크 수와 모델이 보고한 토큰 사용량을 담는다. [Spring AI RAG](https://docs.spring.io/spring-ai/reference/2.0/api/retrieval-augmented-generation.html) · [Spring AI ChatClient](https://docs.spring.io/spring-ai/reference/2.0/api/chatclient.html)

```java
package demo.ai;

import java.util.List;
import java.util.Objects;
import java.util.stream.IntStream;

import org.springframework.ai.chat.client.ChatClient;
import org.springframework.ai.chat.client.advisor.vectorstore.QuestionAnswerAdvisor;
import org.springframework.ai.document.Document;
import org.springframework.ai.vectorstore.SearchRequest;
import org.springframework.ai.vectorstore.VectorStore;
import org.springframework.boot.ApplicationRunner;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Profile;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;

@RestController
@Profile("rag & cost-lab & !elastic")
class RagCostLabController {

    private final ChatClient client;
    private final VectorStore store;

    RagCostLabController(ChatClient.Builder builder, VectorStore store) {
        this.client = builder
                .defaultSystem("제공된 정책 문서를 근거로만 답하세요. 근거가 없으면 확인할 수 없다고 답하세요.")
                .build();
        this.store = store;
    }

    @PostMapping("/api/lab/rag-cost")
    Result compare(@RequestBody Question question) {
        int topK = question.topK();
        if (topK != 4 && topK != 20) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Use topK 4 or 20");
        }

        var search = SearchRequest.builder()
                .topK(topK)
                .similarityThreshold(SearchRequest.SIMILARITY_THRESHOLD_ACCEPT_ALL)
                .filterExpression("category == 'rag-cost-lab'")
                .build();
        var retrieval = QuestionAnswerAdvisor.builder(store).searchRequest(search).build();

        var response = client.prompt().user(question.text()).advisors(retrieval)
                .call().chatClientResponse();
        var chat = Objects.requireNonNull(response.chatResponse());
        Object documents = response.context().get(QuestionAnswerAdvisor.RETRIEVED_DOCUMENTS);
        int retrieved = documents instanceof List<?> chunks ? chunks.size() : 0;
        var usage = chat.getMetadata().getUsage();

        return new Result(topK, retrieved,
                usage == null ? null : usage.getPromptTokens(),
                usage == null ? null : usage.getCompletionTokens(),
                chat.getResult().getOutput().getText());
    }

    record Question(String text, int topK) {}
    record Result(int topK, int retrieved, Integer inputTokens, Integer outputTokens, String answer) {}
}

@Configuration
@Profile("rag & cost-lab & !elastic")
class RagCostLabData {

    @Bean
    ApplicationRunner loadRagCostLabData(VectorStore store) {
        return args -> store.add(documents());
    }

    List<Document> documents() {
        return IntStream.rangeClosed(1, 24)
                .mapToObj(id -> Document.builder()
                        .id("rag-cost-" + id)
                        .text("""
                                배송 및 반품 정책 부록 %d
                                단순 변심에 의한 반품은 상품 수령일부터 7일 이내에 신청할 수 있습니다.
                                반품 신청 전 주문 번호와 수령일을 확인해 주세요.
                                상품 재포장과 배송 상태는 주문 내역에서 확인할 수 있습니다.
                                """.formatted(id))
                        .metadata("category", "rag-cost-lab")
                        .metadata("policySection", id)
                        .build())
                .toList();
    }
}
```

## 2. 동일한 질문으로 재현

Ollama에 [채팅 모델](04_building_chat_apis_with_openai_and_ollama.md)과 [RAG 임베딩 모델](07_building_rag_chatbots_with_elasticsearch.md)을 내려받고 앱을 호스트에서 실행한다. 프로파일 순서를 아래와 같이 두면 `rag` 설정이 `ollama`의 임베딩 설정을 덮어쓴다. 13번 Compose의 앱을 실행 중이면 8080번 포트를 비우고 실행한다.

```bash
./gradlew bootRun --args='--spring.profiles.active=ollama,rag,cost-lab,monitoring'
```

```bash
for top_k in 4 20; do
  printf '{"text":"단순 변심 반품은 언제까지 신청할 수 있나요? 한 문장으로 답하세요.","topK":%s}' "$top_k" \
    | curl -fsS http://localhost:8080/api/lab/rag-cost \
        -H 'Content-Type: application/json' -d @-
  printf '\n'
done
```

두 경우에서 `retrieved`와 `inputTokens`, `outputTokens`를 기록하고 답변에 ‘7일 이내’가 들어가는지 확인한다. 토큰 값이 `null`이거나 모델에서 사용량을 보고하지 않으면 비용 비교에서 제외한다. 실습 문서는 반품 기한을 반복해 추가 청크가 토큰에 미치는 영향을 보기 쉽게 구성했다. 품질을 평가할 때는 중복이 적은 실제 문서와 고정 질문 세트를 사용한다.

캐시를 제외한 비교용 단가를 입력 100만 토큰당 $0.50, 출력 100만 토큰당 $1.50으로 가정하면 다음과 같다. 아래 토큰 수는 계산 예시다.

| topK | 입력 토큰 | 출력 토큰 | 요청당 추정 비용 |
| --- | ---: | ---: | ---: |
| 4 | 900 | 120 | $0.00063 |
| 20 | 3,300 | 120 | $0.00183 |

비용은 각각 `입력 토큰 × 입력 단가 ÷ 1,000,000`과 `출력 토큰 × 출력 단가 ÷ 1,000,000`을 더해 구한다. OpenAI 실측값을 계산할 때는 실제 모델과 캐시 단가를 사용한다. [OpenAI API 가격표](https://developers.openai.com/api/docs/pricing)

## 3. 운영 설정으로 옮기기

- 검색 후보 수와 최종 프롬프트에 첨부할 청크 수를 별도로 제한한다. 청크 수와 함께 총 컨텍스트 토큰 한도를 둔다.
- 동일한 모델과 질문 세트로 검색 설정별 답변 품질, p95 지연, 입력 토큰을 비교한다. 관련 근거와 보류 판단이 유지되는 값부터 적용한다.
- 요청당 토큰 증가와 시간당 사용량 증가를 구분해 알림을 설정한다. 전자는 과도한 컨텍스트를, 후자는 트래픽이나 재시도 증가를 조사하는 단서다.
