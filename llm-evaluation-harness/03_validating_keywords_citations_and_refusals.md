# Validating Keywords, Citations, and Refusals

키워드·인용·답변 보류는 근거 확인과 실패 진단에 쓸 수 있는 신호다. 각 검사가 증명하는 범위를 정한다. [Python 3.12 · re](https://docs.python.org/3.12/library/re.html) · [NIST · TREC Overview](https://trec.nist.gov/overview.html) · [scikit-learn · Confusion Matrix](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.confusion_matrix.html) · [Liu et al. · G-Eval](https://arxiv.org/abs/2303.16634)

## 1. 키워드와 인용을 근거 확인에 사용한다

핵심 용어와 식별자는 단어 경계와 허용 표기를 명시한다. 예를 들어 문장에 5분이 있는 것만으로 “5분마다 확인하면 안 된다”와 “5분마다 확인한다”를 구별할 수 없다. 정책 ID와 정확한 구절의 원문 존재를 먼저 확인하고 연결된 주장과 인용의 의미 일치는 별도 항목으로 본다. [Python 3.12 · re](https://docs.python.org/3.12/library/re.html) · [Liu et al. · G-Eval](https://arxiv.org/abs/2303.16634) · [NIST · TREC Overview](https://trec.nist.gov/overview.html)

출처 ID와 원문 버전이 결합된 데이터에서 인용 위치를 대조한다. 인용의 표시 줄이 같아도 버전이 다르면 근거를 확인할 수 없으므로 버전 불일치를 별도 실패로 남긴다. [NIST · TREC Overview](https://trec.nist.gov/overview.html) · [pytest · Parametrize](https://docs.pytest.org/en/stable/how-to/parametrize.html)

## 2. 답변 보류의 정답과 출력 오류를 구분한다

정답 라벨은 답변 가능과 근거 부족을 나눈다. 출력의 보류 여부는 구조화된 decision을 우선 사용한다. 표현으로 감지하는 규칙은 보조로 두고, 답변할 수 있는 경우의 보류와 보류해야 하는 경우의 근거 없는 응답을 각각 집계한다. 제공자 거절, 타임아웃, 스키마 오류는 별도 상태로 기록한다. [JSON Schema 2020-12 · Validation](https://json-schema.org/draft/2020-12/json-schema-validation) · [scikit-learn · Confusion Matrix](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.confusion_matrix.html) · [scikit-learn · Metrics and Scoring](https://scikit-learn.org/stable/modules/model_evaluation.html)

답변 가능 집합에서는 보류한 케이스 비율을, 근거 부족 집합에서는 답한 케이스 비율을 본다. 실행 오류의 건수와 유효 판정 분모도 같이 보여 준다. [scikit-learn · Confusion Matrix](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.confusion_matrix.html) · [scikit-learn · Metrics and Scoring](https://scikit-learn.org/stable/modules/model_evaluation.html)
