# Building and Versioning Evaluation Datasets

평가셋은 같은 케이스를 여러 후보에 실행할 수 있게 질문, 허용 근거, 기대 행위와 분류 태그를 저장한다. [NIST · TREC Overview](https://trec.nist.gov/overview.html) · [pytest · Parametrize](https://docs.pytest.org/en/stable/how-to/parametrize.html) · [scikit-learn · Cross-Validation](https://scikit-learn.org/stable/modules/cross_validation.html)

## 1. 케이스의 재현과 해석에 필요한 필드를 남긴다

고정 case_id, 입력, 근거 집합의 버전, 기대 답변 또는 보류 조건, 위험군 태그를 저장한다. 라벨의 변경 이유와 적용된 루브릭을 기록하고, 중복·오표기·근거 누락은 샘플 검수한다. 아래 케이스와 문서 이름은 실습용이다. [NIST · TREC Overview](https://trec.nist.gov/overview.html) · [pytest · Parametrize](https://docs.pytest.org/en/stable/how-to/parametrize.html) · [Liu et al. · G-Eval](https://arxiv.org/abs/2303.16634)

```json
{
  "case_id": "ops-check-001",
  "input": "승인 대기 주문은 얼마나 자주 확인하나요?",
  "source_revision": "runbook-v3",
  "expected": {"decision": "answer", "minutes": 5, "source_ids": ["OPS-1"]},
  "tags": ["ko", "numeric", "evidence-required"]
}
```

## 2. 튜닝용과 결과 확인용 평가를 분리한다

개발용 세트는 수정에 반복 사용하고, 별도 홀드아웃은 사전에 정한 시점에서 사용한다. 같은 원문·템플릿의 변형 질문이 두 집합에 퍼지지 않도록 그룹으로 분리한다. 실행 기록에는 평가셋, 기준 출처, Judge, 루브릭과 모델 설정을 함께 남긴다. [scikit-learn · Cross-Validation](https://scikit-learn.org/stable/modules/cross_validation.html) · [Zheng et al. · Judging LLM-as-a-Judge](https://arxiv.org/abs/2306.05685) · [NIST · TREC Overview](https://trec.nist.gov/overview.html)
