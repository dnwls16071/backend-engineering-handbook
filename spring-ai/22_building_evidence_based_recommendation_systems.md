# Building Evidence-Based Recommendation Systems

문서 Q&A는 사실을 설명하고, 추천 시스템은 조건과 평가 기준을 적용해 후보를 비교한다. 평가 결과에는 적용한 루브릭 버전, 판정, 이용한 근거 ID를 함께 남긴다.

## 1. 예제로 보는 추천 흐름

팀이 두 가지 내부 문서 검색 도구를 비교한다고 가정한다.

1. 평가 기준인 권한 필터, 데이터 갱신, 내보내기 지원과 각 후보의 가상 문서를 적재한다.
2. 후보별로 동일한 검색 조건을 적용하고, 각 기준에서 근거가 발견됐는지 확인한다.
3. 모델에는 입증된 장점, 문서에 명시된 제약, 확인할 수 없는 항목을 구조화해 반환하도록 한다.
4. 앱은 필수 조건을 정책대로 검사하고, 근거가 부족하거나 서로 충돌하면 담당자 검토로 보낸다.

예시 구조에서 `doc-search-b#permissions`는 실제로 검색하고 호출자에게 공개할 수 있는 청크 ID여야 한다.

```json
{
  "candidateId": "doc-search-b",
  "decision": "REVIEW_REQUIRED",
  "rubricVersion": "tool-selection-v1",
  "findings": [
    {
      "criterion": "access_filter",
      "status": "SUPPORTED",
      "evidenceIds": ["doc-search-b#permissions"]
    },
    {
      "criterion": "export",
      "status": "INSUFFICIENT_EVIDENCE",
      "evidenceIds": []
    }
  ]
}
```

## 2. 구조와 근거를 따로 확인하기

스키마로 누락된 필드와 허용되지 않는 상태 값을 검출한다. 각 근거 ID가 실제 검색 집합에 있는지와, 인용한 청크가 해당 항목을 지지하는지를 따로 확인한다. 모델이 제안한 점수를 쓰는 경우 점수의 집계, 필수 조건의 우선순위, 검토 전환은 버전이 있는 업무 정책으로 구현한다. [Spring AI · Structured Output](https://docs.spring.io/spring-ai/reference/2.0/api/structured-output/converters.html) · [Spring AI · Evaluation Testing](https://docs.spring.io/spring-ai/reference/2.0/api/testing.html)

후보 누락, 오래된 루브릭, 검색 결과 없음, 같은 기준에 대한 상충 근거를 평가 데이터에 넣는다. 보고서에서 추천 정확도와 검토 전환 비율을 함께 보면 입력 데이터나 정책 변경의 영향을 비교할 수 있다.

관련 문서 [Tuning and Evaluating RAG Systems](21_tuning_and_evaluating_rag_systems.md)
