# Tuning and Evaluating RAG Systems

검색 품질과 답변 품질을 나눠 측정한다. 답변 오류가 있으면 관련 청크가 검색되지 않았는지, 검색됐지만 답변이 청크에 없는 내용을 추가했는지부터 구별한다.

## 1. 검색 튜닝과 하이브리드 검색

| 변경 | 확인할 내용 |
| --- | --- |
| 청크 크기와 겹침 | 표 제목과 값, 규칙과 예외가 같은 청크에 남는지 확인한다. |
| `topK`와 최소 유사도 | 검색 누락, 입력 토큰, 지연이 어떻게 변하는지 측정한다. |
| 벡터 + 전문 검색 | 의미가 비슷한 표현과 정확한 상품명·오류 코드가 포함된 요청을 각각 측정한다. |
| Reranking | 후보 집합을 다시 정렬한 뒤 검색 누락과 지연을 함께 비교한다. |

PostgreSQL에서 pgvector 검색 결과와 전문 검색 순위는 Reciprocal Rank Fusion 등으로 합칠 수 있다. 한국어 문서에서 토큰화와 표기 변형이 검색 순위에 미치는 영향은 별도의 평가 데이터로 측정한다. [pgvector · Hybrid Search](https://github.com/pgvector/pgvector#hybrid-search)

## 2. Spring AI Evaluator로 답변 평가하기

`EvaluationRequest`에 질문, 검색 맥락, 생성 응답을 담는다. `RelevancyEvaluator`로 질문과 맥락에 비춰 답변이 관련 있는지 확인한다. `FactCheckingEvaluator`로 답변이 제공된 근거에 의해 지지되는지 평가한다. 모델 심판의 합격 여부는 평가 모델과 프롬프트에도 영향을 받으므로, 근거 ID 대조 같은 결정적 검사와 사람이 검토한 사례를 함께 사용한다. [Spring AI · Evaluation Testing v2.0.2](https://github.com/spring-projects/spring-ai/blob/v2.0.2/spring-ai-docs/src/main/antora/modules/ROOT/pages/api/testing.adoc)

## 3. 변경 전후 비교 리포트

질문별로 기대 근거 ID와 답변 가능 여부를 저장한다. 정상, 철자·표현 변형, 답변 불가, 권한 제외, 오래된 버전 사례를 포함한다. 같은 모델과 데이터에서 검색 설정 하나씩 바꾸고, 아래처럼 결과를 남긴다.

| 지표 | 계산 또는 기록 |
| --- | --- |
| Recall@k | 해당 질문의 관련 청크 중 상위 k개에 포함된 비율을 질문별로 계산한다. 정답 청크가 있는 질문의 평균을 기록한다. |
| 근거 충족률 | 실제 답변 중 제공한 청크로 핵심 주장을 뒷받침한 비율을 구한다. |
| 올바른 답변 보류율 | 답변 불가 질문 중 보류한 비율을 구한다. |
| 지연·토큰 | p95 지연과 요청당 입력 토큰을 같은 부하·샘플 조건에서 비교한다. |

예를 들어 기대 청크가 `R1`, `R2`이고 상위 세 건이 `R1`, `X`, `Y`면 해당 질문의 Recall@3은 `0.5`다. 단위 테스트에서 순위·근거 ID 계산은 고정 데이터로 검증하고, 모델을 호출하는 통합 평가는 모델 및 데이터 버전을 포함한 비교 리포트로 남긴다.

관련 문서 [Building Spring AI RAG with pgvector](20_building_spring_ai_rag_with_pgvector.md) · [Analyzing and Controlling RAG Token Costs](14_analyzing_and_controlling_rag_token_costs.md)
