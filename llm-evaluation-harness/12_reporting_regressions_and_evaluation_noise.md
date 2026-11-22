# Reporting Regressions and Evaluation Noise

평가 리포트에는 기준과 후보가 어떻게 달라졌는지와, 실행 변동을 고려해 그 차이를 얼마나 해석할 수 있는지 함께 남긴다. [SciPy 1.16.1 · Bootstrap](https://docs.scipy.org/doc/scipy-1.16.1/reference/generated/scipy.stats.bootstrap.html) · [Zheng et al. · Judging LLM-as-a-Judge](https://arxiv.org/abs/2306.05685) · [scikit-learn · Metrics and Scoring](https://scikit-learn.org/stable/modules/model_evaluation.html)

## 1. 비율의 분모와 케이스 전이를 보여 준다

총 대상·성공 실행·누락 건수와 지표별 기준, 후보, 절대 델타, 신뢰구간을 적는다. 통과→실패·실패→통과 케이스, 태그별 결과, 대표 실패 ID도 남긴다. 예를 들어 82%에서 79%로 바뀌면 절대 델타는 -3%p다. [scikit-learn · Confusion Matrix](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.confusion_matrix.html) · [scikit-learn · Metrics and Scoring](https://scikit-learn.org/stable/modules/model_evaluation.html) · [SciPy 1.16.1 · Bootstrap](https://docs.scipy.org/doc/scipy-1.16.1/reference/generated/scipy.stats.bootstrap.html)

## 2. 노이즈 원인을 비교 구성에서 찾는다

입력이나 모델, Judge 버전이 바뀌었는지 먼저 대조한다. 설정이 같아도 응답을 다시 생성하거나 Judge 판정을 반복하면 달라질 수 있다. 같은 산출물을 다시 채점하는 검증과 SUT를 다시 실행하는 검증을 구분한다. 근거가 불충분하면 불확실로 기록한다. [Zheng et al. · Judging LLM-as-a-Judge](https://arxiv.org/abs/2306.05685) · [Liu et al. · G-Eval](https://arxiv.org/abs/2303.16634) · [SciPy 1.16.1 · Bootstrap](https://docs.scipy.org/doc/scipy-1.16.1/reference/generated/scipy.stats.bootstrap.html)
