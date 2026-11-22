# Validating Pointwise Judge Results

Pointwise는 답변 하나를 루브릭에 맞춰 독립적으로 판정한다. JSON은 결과를 교환하는 형식이며 판정의 품질은 사람 기준과 비교한다. [Zheng et al. · Judging LLM-as-a-Judge](https://arxiv.org/abs/2306.05685) · [Liu et al. · G-Eval](https://arxiv.org/abs/2303.16634) · [JSON Schema 2020-12 · Validation](https://json-schema.org/draft/2020-12/json-schema-validation)

## 1. 응답 스키마와 근거 참조를 검증한다

각 항목은 pass, fail, uncertain 중 하나를 반환하도록 정한다. 근거 목록에는 입력으로 제공한 허용 ID만 들어갈 수 있다. 판정 설명은 확인 가능한 이유로 제한한다. 다음 예는 가상의 운영 위키 자료를 사용한다. [Liu et al. · G-Eval](https://arxiv.org/abs/2303.16634) · [JSON Schema 2020-12 · Validation](https://json-schema.org/draft/2020-12/json-schema-validation) · [python-jsonschema 4.25.1 · Validation](https://python-jsonschema.readthedocs.io/en/v4.25.1/validate/)

```json
{
  "criteria": {
    "accuracy": "fail",
    "evidence": "fail",
    "abstention": "pass"
  },
  "evidence_ids": ["OPS-1"],
  "reason": "OPS-1은 5분 간격 점검을 규정하지만 후보 답변은 15분이라고 답했다."
}
```

## 2. 실행 실패와 업무 판정을 따로 저장한다

판정 JSON의 문법·스키마와 근거 ID 참조를 확인한다. 파싱 실패, Judge 거절, 타임아웃은 실행 오류로 남기고 평가 불완전 비율에 포함한다. 근거가 부족하다고 실제로 판정한 uncertain과 구분한다. [Python 3.12 · json](https://docs.python.org/3.12/library/json.html) · [JSON Schema 2020-12 · Validation](https://json-schema.org/draft/2020-12/json-schema-validation) · [scikit-learn · Confusion Matrix](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.confusion_matrix.html)

케이스 ID와 SUT·Judge 모델 식별자, 두 프롬프트 버전, 루브릭 버전은 하네스가 붙인다. 기준이 바뀌었을 때 이전 판정과 구별하고 같은 사례로 사람 일치도를 다시 측정한다. [Zheng et al. · Judging LLM-as-a-Judge](https://arxiv.org/abs/2306.05685) · [Liu et al. · G-Eval](https://arxiv.org/abs/2303.16634) · [scikit-learn · Cross-Validation](https://scikit-learn.org/stable/modules/cross_validation.html)
