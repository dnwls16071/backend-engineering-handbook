# Designing Rubrics for LLM Judges

Judge는 사람이 정의한 평가 기준을 모델에 적용하는 방법이다. 판정마다 관찰할 증거와 실패 조건을 정한다. [Liu et al. · G-Eval](https://arxiv.org/abs/2303.16634) · [Zheng et al. · Judging LLM-as-a-Judge](https://arxiv.org/abs/2306.05685)

## 1. 루브릭을 실제로 관찰할 수 있는 항목으로 나눈다

| 기준 | 통과 | 실패 또는 보류 | 근거 |
| --- | --- | --- | --- |
| 정확성 | 질문의 핵심 값과 조건이 기준과 일치한다. | 승인 상태, 수치, 부정 등 핵심 사실이 다르면 실패 | [Liu et al. · G-Eval](https://arxiv.org/abs/2303.16634) · [Zheng et al. · Judging LLM-as-a-Judge](https://arxiv.org/abs/2306.05685) |
| 근거 충실도 | 주요 주장마다 제공된 근거가 지지한다. | 인용 문서가 존재해도 주장을 뒷받침하지 않으면 실패 | [Liu et al. · G-Eval](https://arxiv.org/abs/2303.16634) · [NIST · TREC Overview](https://trec.nist.gov/overview.html) |
| 적절한 보류 | 자료가 부족하면 부족한 범위를 설명하고 추정을 피한다. | 질문에 필요한 증거 자체가 누락됐는지 판단하기 어렵다면 판정 보류 | [Liu et al. · G-Eval](https://arxiv.org/abs/2303.16634) · [scikit-learn · Confusion Matrix](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.confusion_matrix.html) |

## 2. 사람이 합의한 앵커 사례로 먼저 점검한다

명확한 통과·실패와 서로 다른 표현의 같은 정답을 함께 넣는다. 사람이 독립적으로 라벨을 붙이고 불일치의 기준을 합의한다. Judge가 반복해서 빗나가는 기준은 항목 정의와 예시를 수정하고 별도 표본에서 다시 평가한다. [Liu et al. · G-Eval](https://arxiv.org/abs/2303.16634) · [Zheng et al. · Judging LLM-as-a-Judge](https://arxiv.org/abs/2306.05685) · [scikit-learn · Confusion Matrix](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.confusion_matrix.html)

## 3. 판정에 필요한 자료와 출력 경계를 정한다

Judge에 질문, 후보 답변, 허용된 근거, 평가 기준을 서로 구별해 입력한다. 후보와 근거는 판정할 데이터로 전달한다. 포맷과 존재 여부 같은 규칙으로 확인할 수 있는 제약은 별도 코드에서 검사한다. [Liu et al. · G-Eval](https://arxiv.org/abs/2303.16634) · [JSON Schema 2020-12 · Validation](https://json-schema.org/draft/2020-12/json-schema-validation) · [Zheng et al. · Judging LLM-as-a-Judge](https://arxiv.org/abs/2306.05685)
