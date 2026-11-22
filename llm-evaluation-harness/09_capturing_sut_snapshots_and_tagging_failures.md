# Capturing SUT Snapshots and Tagging Failures

SUT는 평가 대상 시스템이다. 원시 실행 결과와 사람이 승인한 기대 결과를 구분해 저장하고, 기준 스냅샷 변경은 리뷰 대상으로 둔다. [Jest 30 · Snapshot Testing](https://jestjs.io/docs/30.0/snapshot-testing) · [pytest · Parametrize](https://docs.pytest.org/en/stable/how-to/parametrize.html) · [Liu et al. · G-Eval](https://arxiv.org/abs/2303.16634)

## 1. 재현 가능한 산출물을 만든다

원시 응답, 추출한 필드, 형식·근거 판정, 도구 오류를 case_id로 묶는다. 커밋하는 스냅샷은 의미 없는 타임스탬프나 요청 ID를 제거하고 순서를 고정한다. 원시 로그는 필요 범위에서 접근과 보관을 제한한다. [Jest 30 · Snapshot Testing](https://jestjs.io/docs/30.0/snapshot-testing) · [pytest · Parametrize](https://docs.pytest.org/en/stable/how-to/parametrize.html) · [OpenTelemetry · Handling Sensitive Data](https://opentelemetry.io/docs/security/handling-sensitive-data/)

## 2. 원인 추적에 맞는 실패 이름을 붙인다

| 태그 예시 | 판정 조건 | 근거 |
| --- | --- | --- |
| parse_error / schema_error | 문법 오류인지 파싱 뒤 출력 계약 위반인지 구별한다. | [Python 3.12 · json](https://docs.python.org/3.12/library/json.html) · [JSON Schema 2020-12 · Validation](https://json-schema.org/draft/2020-12/json-schema-validation) |
| missing_evidence / unsupported_claim | 근거 ID가 없거나 존재하는 출처가 주장을 지지하지 않는다. | [NIST · TREC Overview](https://trec.nist.gov/overview.html) · [Liu et al. · G-Eval](https://arxiv.org/abs/2303.16634) |
| false_abstain / missing_abstention | 답변 가능 케이스를 보류하거나 보류 대상인데 근거 없이 답한다. | [scikit-learn · Confusion Matrix](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.confusion_matrix.html) · [scikit-learn · Metrics and Scoring](https://scikit-learn.org/stable/modules/model_evaluation.html) |
| infra_error / grader_error | 타임아웃, 실행 누락, Judge 응답을 처리할 수 없는 경우다. | [pytest · Parametrize](https://docs.pytest.org/en/stable/how-to/parametrize.html) · [Jest 30 · Snapshot Testing](https://jestjs.io/docs/30.0/snapshot-testing) |

실패 태그는 원인을 조사하는 단서다. 한 케이스에 여러 태그를 붙일 수 있으며, 필수 태그가 없거나 자동 분류가 틀리면 표본을 검토한다. 기준을 갱신할 때는 생성 시점의 출력이 의도한 정답인지 확인한다. [Jest 30 · Snapshot Testing](https://jestjs.io/docs/30.0/snapshot-testing) · [Liu et al. · G-Eval](https://arxiv.org/abs/2303.16634) · [scikit-learn · Confusion Matrix](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.confusion_matrix.html)
