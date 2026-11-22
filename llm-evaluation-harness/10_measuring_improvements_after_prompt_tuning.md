# Measuring Improvements After Prompt Tuning

프롬프트만 바꾼 효과를 측정하려면 구성을 고정한 후보를 같은 케이스로 비교한다. 오프라인 지표의 개선은 측정한 분포와 항목의 범위 안에서 해석한다. [scikit-learn · Cross-Validation](https://scikit-learn.org/stable/modules/cross_validation.html) · [Zheng et al. · Judging LLM-as-a-Judge](https://arxiv.org/abs/2306.05685) · [SciPy 1.16.1 · Bootstrap](https://docs.scipy.org/doc/scipy-1.16.1/reference/generated/scipy.stats.bootstrap.html)

## 1. 어떤 요소를 바꿨는지 기록한다

기준과 후보에 같은 모델 식별자·샘플링 설정·검색 문서 버전·Judge 루브릭을 사용한다. 인덱스나 모델이 동시에 바뀌었다면 각 변경의 영향을 구분하는 비교를 추가한다. 변동이 큰 경우 같은 조건에서 반복 실행하고 반복 관측은 케이스에 묶는다. [scikit-learn · Cross-Validation](https://scikit-learn.org/stable/modules/cross_validation.html) · [Zheng et al. · Judging LLM-as-a-Judge](https://arxiv.org/abs/2306.05685) · [SciPy 1.16.1 · Bootstrap](https://docs.scipy.org/doc/scipy-1.16.1/reference/generated/scipy.stats.bootstrap.html)

## 2. 평균 외에 업무에 중요한 위험군을 본다

형식 통과율, 근거 없는 답변 비율, 부적절한 보류, 지연과 비용을 따로 비교한다. 평균이 좋아져도 숫자·출처처럼 실패 비용이 큰 유형에서 나빠지면 배포 조건을 다시 검토한다. 홀드아웃 결과와 테스트 수를 함께 남긴다. [scikit-learn · Metrics and Scoring](https://scikit-learn.org/stable/modules/model_evaluation.html) · [scikit-learn · Cross-Validation](https://scikit-learn.org/stable/modules/cross_validation.html) · [Liu et al. · G-Eval](https://arxiv.org/abs/2303.16634)
