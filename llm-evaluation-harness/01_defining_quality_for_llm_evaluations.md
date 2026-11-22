# Defining Quality for LLM Evaluations

평가할 대상을 업무 단위로 정한다. 예로 업무 위키 질문에 정책과 근거를 제시하고, 자료가 부족하면 답변을 보류하는 시스템을 다룬다. [NIST · TREC Overview](https://trec.nist.gov/overview.html) · [Zheng et al. · Judging LLM-as-a-Judge](https://arxiv.org/abs/2306.05685) · [Liu et al. · G-Eval](https://arxiv.org/abs/2303.16634)

## 1. 판정에 쓸 수 있는 정답과 근거를 구분한다

| 질문 유형 | 판정 기준 | 채점기 | 근거 |
| --- | --- | --- | --- |
| 정확한 단일값 | 승인 대기 주문의 확인 주기처럼 출처에 규정된 값 | 정규화 후 정확 일치 또는 단위까지 포함한 수치 체크 | [scikit-learn · Metrics and Scoring](https://scikit-learn.org/stable/modules/model_evaluation.html) · [Python 3.12 · re](https://docs.python.org/3.12/library/re.html) |
| 정답 표현이 여러 개 | 등록 조건을 설명하고 근거를 제시하는 서술 | 필수 사실과 인용을 검사한 뒤 모호한 항목을 루브릭으로 평가 | [Liu et al. · G-Eval](https://arxiv.org/abs/2303.16634) · [Zheng et al. · Judging LLM-as-a-Judge](https://arxiv.org/abs/2306.05685) |
| 근거가 없는 질문 | 허용된 문서로는 결론을 지지할 수 없는 상황 | 근거 부족 판정이 기대되는지 라벨로 지정 | [Liu et al. · G-Eval](https://arxiv.org/abs/2303.16634) · [scikit-learn · Confusion Matrix](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.confusion_matrix.html) |

## 2. 평가 하네스가 저장할 결과를 정한다

케이스 ID, SUT 버전, 채점기 버전, 원시 결과와 항목별 판정을 연결한다. 포맷, 근거, 답변의 유용성을 분리하고 사람의 결론이 필요한 사례에는 검토 상태를 둔다. [pytest · Parametrize](https://docs.pytest.org/en/stable/how-to/parametrize.html) · [Liu et al. · G-Eval](https://arxiv.org/abs/2303.16634) · [Zheng et al. · Judging LLM-as-a-Judge](https://arxiv.org/abs/2306.05685)

## 3. 주제별로 이어 읽기

[결정적 채점기](02_grading_exact_matches_regex_and_json_schema.md), [Judge 루브릭](05_designing_rubrics_for_llm_judges.md), [평가셋](08_building_and_versioning_evaluation_datasets.md), [회귀 게이트](11_gating_regressions_in_ci.md), [운영 트레이싱](14_instrumenting_llm_requests_with_opentelemetry.md) 순서로 평가 경계를 확인한다. [JSON Schema 2020-12 · Validation](https://json-schema.org/draft/2020-12/json-schema-validation) · [Liu et al. · G-Eval](https://arxiv.org/abs/2303.16634) · [scikit-learn · Cross-Validation](https://scikit-learn.org/stable/modules/cross_validation.html) · [GitHub · Required Status Checks](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches) · [OpenTelemetry · Traces](https://opentelemetry.io/docs/concepts/signals/traces/)
