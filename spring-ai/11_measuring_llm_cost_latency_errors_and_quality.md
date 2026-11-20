# Measuring LLM Cost, Latency, Errors, and Quality

한 응답을 만드는 데 얼마를 썼는지, 얼마나 걸렸는지, 정상적으로 완료됐는지, 질문에 맞는 답이었는지를 각각 측정한다.

| 지표 | 측정 기준 | 확인할 변화 |
| --- | --- | --- |
| 비용 | 입력·출력 토큰과 모델 단가, 요청당 추정 비용 | 모델 변경, 긴 프롬프트, 재검색과 재호출 |
| 지연 | 사용자 요청 완료 시간의 p50·p95, 스트리밍 첫 응답까지의 시간 | 느린 사용자 요청, 공급자 지연, 검색 지연 |
| 오류 | 실패 건수 ÷ 전체 요청 수, 공급자 오류의 원인별 건수 | 제한 초과, 타임아웃, 잘못된 구조화 응답 |
| 품질 | 고정 질문에서 정답·근거 일치 여부, 근거 부족 시 보류 여부 | 엉뚱한 검색 결과나 근거 없는 응답 증가 |

사용자 응답 시간이 길어졌다면 HTTP 전체 시간과 모델 호출 시간을 비교한다. 모델 호출 시간에는 검색과 앱 내부의 후처리 시간이 포함되지 않는다. 스트리밍의 첫 토큰 지연이 필요하면 스트림을 구독한 시점에서 첫 텍스트가 도착할 때까지 별도로 기록한다. [Spring AI Observability](https://docs.spring.io/spring-ai/reference/2.0/observability/index.html)

## 실습 프로젝트 준비

[채팅 API 프로젝트](04_building_chat_apis_with_openai_and_ollama.md)에서 OpenAI 또는 Ollama를 선택한다. 같은 모델로 일반 호출 `POST /api/chat`을 몇 번 보내고 응답 본문과 HTTP 시간을 확인한다. 이후 Actuator를 붙여 같은 요청의 모델 관측값을 비교한다.

```bash
curl -sS -o /tmp/spring-ai-monitoring-answer.json \
  -w 'status=%{http_code} duration=%{time_total}s\n' \
  http://localhost:8080/api/chat \
  -H 'Content-Type: application/json' \
  --data '{"message":"반품과 교환의 차이를 한 문장으로 설명해 주세요."}'
cat /tmp/spring-ai-monitoring-answer.json
```

RAG를 평가할 때는 답이 원문에 있는 질문과 원문만으로 답할 수 없는 질문을 함께 준비한다. 프롬프트, 모델, 문서 버전, 기대 답변을 기록해 두면 검색 설정만 바꿨을 때 품질과 지연이 어떻게 달라졌는지 비교할 수 있다.
