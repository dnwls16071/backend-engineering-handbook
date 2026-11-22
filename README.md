# Lounge

💻 백엔드 시스템의 설계·구현·운영을 정리한 학습·실무 위키입니다.

Java·Spring, 데이터베이스, 분산 시스템, 클라우드 운영, LLM 애플리케이션을 다룹니다. 업무 중에 생긴 질문과 가까운 문서부터 시작하세요.

## 문제별로 찾아보기

| 지금 해결하려는 문제 | 먼저 읽을 문서 |
| --- | --- |
| 시스템 설계를 어디서 시작할까? | [요구사항에서 실패 시나리오까지](system-design/03_applying_a_system_design_framework.md) · [문제와 트레이드오프로 패턴 선택하기](architecture-pattern/01_design_solutions_through_problems_and_tradeoffs.md) |
| Spring에서 트랜잭션이 기대대로 동작하지 않는다 | [Spring 트랜잭션 프록시와 롤백 규칙](spring-db/14_spring_transaction_proxies_and_rollback_rules.md) · [트랜잭션 전파 모드](spring-db/15_spring_transaction_propagation_modes.md) |
| API가 느려졌는데 병목을 어디서 찾을까? | [관측 데이터로 장애 조사하기](observability/09_investigating_incidents_with_observability_data_and_ai.md) · [Span 워터폴 읽기](distributed-tracing/03_trace_data_model_and_waterfall_visualization.md) · [부하 테스트에서 병목 찾기](load-testing-guideline/02_bottleneck_identification.md) |
| 느린 SQL의 원인을 찾고 싶다 | [MySQL 슬로우 쿼리와 기준선](database-performance/15_mysql_slow_query_logging_and_workload_baselines.md) · [MySQL 실행 계획과 쿼리 튜닝](database-performance/16_mysql_execution_plans_indexes_and_query_tuning.md) · [PostgreSQL 실행 계획과 쿼리 진단](postgresql/11_postgresql_execution_plans_and_query_diagnostics.md) |
| 캐시의 오래된 값을 어떻게 관리할까? | [캐시 무효화와 버전 키](cache/12_cache_invalidation_versioned_keys_and_consistency_windows.md) · [Valkey의 TTL과 무효화](valkey/02_valkey_caching_ttl_and_invalidation.md) |
| 타임아웃 뒤 중복 결제나 이벤트 유실을 막고 싶다 | [결제 승인 멱등성과 재시도](payment-system/03_confirming_payments_with_idempotency_retries_and_timeouts.md) · [Transactional Outbox로 이벤트 발행하기](distributed-transaction/40_publishing_order_events_with_a_transactional_outbox.md) |
| DB에 접수한 송금을 외부 시스템의 결과와 어떻게 대조할까? | [일관성을 갖춘 시스템 설계](payment-consistency/README.md) |
| 서비스와 DB를 안전하게 배포하고 싶다 | [서비스와 DB의 무중단 배포](architecture-design-for-operations/05_designing_zero_downtime_deployments_for_services_and_databases.md) · [Blue-Green과 Canary 배포](microservice-architecture/17_container_deployment_and_progressive_delivery.md) |
| 변경을 검증하려면 어떤 테스트를 써야 할까? | [TDD의 피드백 루프](test-driven-development/01_tdd_fundamentals_and_feedback_loops.md) · [분산 시스템의 테스트 전략](distributed-environment/03_choosing_testing_strategies_for_distributed_systems.md) · [Pact로 서비스 계약 검증하기](distributed-environment/06_verifying_service_contracts_with_pact.md) |
| RAG 검색 품질과 응답 회귀를 어떻게 확인할까? | [의미 기반 검색과 임베딩](llm-rag/01_understanding_semantic_search_and_embeddings.md) · [2단계 검색의 품질과 비용 평가](llm-rag/28_evaluating_two_stage_retrieval_and_cost.md) · [CI에서 LLM 회귀 검사하기](llm-evaluation-harness/11_gating_regressions_in_ci.md) |

## 로컬에서 검색하기

저장소 루트에서 검색어를 넣어 실행하면 관련 문서와 줄 번호가 나옵니다. 주제를 알고 있다면 `--scope`로 범위를 좁힐 수 있습니다.

```bash
python3 wiki/wiki.py search "멱등" --limit 5
python3 wiki/wiki.py search "결제 승인" --scope payment-system --limit 3
```

업무에 적용할 때는 문서의 버전과 전제를 확인하고, 현재 프로젝트에 적용되는 동작은 해당 버전의 공식 문서와 대조합니다. Codex에서 위키를 참고하는 방법, Context7으로 공식 근거를 확인하는 절차, 문서 검증과 수정 규칙은 [위키 운영 가이드](wiki/README.md)와 [AGENTS.md](AGENTS.md)에 정리돼 있습니다.
