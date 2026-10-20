# 03. Companion Agent 자주 묻는 질문 (FAQ)

---

### Q1. Companion Agent는 기존 Agent Assist 기능(Knowledge Assist, Smart Reply, AI Coach)과 어떻게 다른가요?

- **단일 통합 인터페이스 (Unified Experience)**: 기존에는 기능별로 패널이 분리되어 있었으나, Companion Agent는 능동형 코칭 카드(`Guidance agent`)와 대화형 검색(`Ask assistant`)을 하나의 통합된 화면으로 결합하여 상담원의 시선 분산과 인지 부하를 줄여줍니다.
- **양방향 상호작용 (Proactive + Reactive)**: 대화를 듣고 자동으로 제안을 푸시(Proactive)할 뿐만 아니라, 상담원이 필요한 순간에 직접 자연어로 질문하여 도구를 호출하거나 매뉴얼을 검색(Reactive)할 수 있습니다.
- **CX Agent Studio (CXAS) 도구 직접 재사용**: CX Agent Studio에서 구축한 Python Function Tool, OpenAPI Toolset, Data Store를 별도 재개발 없이 그대로 연결하여 사용할 수 있습니다.

---

### Q2. Companion Agent를 도입하기에 가장 효과적인 유스케이스는 무엇인가요?

1. **복잡한 요금/계약 조회 및 트러블슈팅 상담**: 상담원이 고객의 청구서를 비교 분석하면서 동시에 제품 매뉴얼이나 정책 문서를 검색해야 하는 복합 상담 환경
2. **표준화된 다단계 상담 절차 유도**: 전체 요약 안내 후 고객이 선택한 특정 기기나 항목에 대해 2단계 상세 조회를 수행하는 등 일관된 응대 흐름이 필요한 환경
3. **신규 상담원 조기 전력화 (Onboarding)**: 신입 상담원이 업무 처리 절차나 제품 사양을 모를 때 `Ask assistant` 창에 즉시 질문하여 실시간 가이드를 받을 수 있는 환경

---

### Q3. 지원되는 리전(Regions)과 권장 리전은 어디인가요?

- **권장 리전**: 별도의 엄격한 로컬 데이터 레지던시 규정이 없는 경우, 가장 빠른 응답 속도와 최신 기능 지원을 위해 Agent Assist 리전으로 **`global`**을 사용하는 것을 권장합니다.
- **연동 시 참고사항**: CX Agent Studio(CXAS) 앱이 `us` 또는 `global` 리전에 생성되어 있더라도 Agent Assist의 `global` 리전 Companion Agent에서 해당 CXAS 앱의 도구들을 정상적으로 불러와 연결할 수 있습니다.

---

### Q4. 한국어를 포함한 다국어를 지원하나요?

네, Companion Agent는 **한국어(ko-KR)**를 포함하여 영어, 일본어, 중국어, 스페인어, 독일어, 프랑스어 등 40개 이상의 언어를 지원합니다. 한국어 환경에서는 `Model Guidance`에 **"정중한 한국어(해요체)로 작성"** 및 **원화 금액 표기(`53,700원`)** 규칙을 지정하면 자연스러운 한국어 코칭 문구가 생성됩니다.

---

### Q5. 고객사의 기존 상담원 데스크톱(Salesforce, Genesys, 자체 웹 UI 등)에는 어떻게 연동하나요?

고객사 환경에 맞춰 다음 3가지 방식으로 통합할 수 있습니다:

1. **Agent Assist 콘솔 내장 시뮬레이터 (`Try it out`)**: 별도 프론트엔드 개발 없이 콘솔에서 즉시 실시간 대화 및 도구 호출을 테스트하고 시연할 수 있습니다.
2. **공식 UI Modules & UI Connector 활용**: Google Cloud에서 제공하는 오픈소스 [Agent Assist UI Modules](https://cloud.google.com/agent-assist/docs/ui-modules) 및 UI Connector(Cloud Run)를 사용하여 기존 웹 기반 상담원 데스크톱이나 CRM(Salesforce, Genesys 등)에 위젯 형태로 빠르게 임베드할 수 있습니다.
3. **자체 커스텀 UI 연동 (API 직접 호출)**: 백엔드에서 `AnalyzeContent` (Proactive 코칭 수신) 및 `StreamingReactiveCompanionSuggestions` (Reactive `Ask assistant` 양방향 스트리밍) gRPC/REST API를 직접 호출하여 자체 상담원 화면에 완벽히 맞춘 UI를 구현할 수 있습니다.
