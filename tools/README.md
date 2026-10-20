# CX Agent Studio (CXAS) 샘플 도구 구성 가이드

본 폴더(`tools/`)에는 **Agent Assist Companion Agent**에서 불러와 사용하는 **CX Agent Studio (CES / CXAS)** 도구들의 샘플 코드와 OpenAPI 스키마가 포함되어 있습니다.

이미 CXAS 앱에 도구가 구성되어 있다면 [메인 가이드(`README.md`)의 2장](../README.md#2-사전-점검-cx-agent-studio-cxas-도구-확인-및-준비)만 확인하시고, 새로운 GCP 프로젝트에서 처음부터 도구를 생성하려는 경우 아래 절차를 따라 등록하세요.

---

## 1. 구성 파일 목록

| 경로 | 도구 유형 | CXAS 도구 이름 (`Display Name`) | 설명 |
| :--- | :--- | :--- | :--- |
| [`python_tools/compare_invoices.py`](python_tools/compare_invoices.py) | Custom Tool (`Python function`) | `compare_invoices` | 당월(`latest`)과 전월(`previous`) 청구서 총액, 차액, 주요 변동 요인(`top_drivers`) 비교 분석 *(내장 샘플 데이터 Fallback 포함)* |
| [`python_tools/get_invoice_breakdown.py`](python_tools/get_invoice_breakdown.py) | Custom Tool (`Python function`) | `get_invoice_breakdown` | 당월 전체 청구 명세(`line=""`) 및 보유 기기 시리얼 끝 3자리 지정(`line="843"`) 개별 명세 조회 *(내장 샘플 데이터 Fallback 포함)* |
| [`python_tools/list_invoices.py`](python_tools/list_invoices.py) | Custom Tool (`Python function`) | `list_invoices` | 고객 계정에 발행된 월별 청구서 요약 목록 조회 *(내장 샘플 데이터 Fallback 포함)* |
| [`python_tools/lookup_customer.py`](python_tools/lookup_customer.py) | Custom Tool (`Python function`) | `lookup_customer` | 고객 계정(`ACC-2026-001`)의 렌탈 케어 멤버십 상품명, 정상 상태, 미납 잔액 조회 |
| [`openapi_schemas/manual_search_openapi.yaml`](openapi_schemas/manual_search_openapi.yaml) | OpenAPI Toolset | `custom_layout_search_2` (`searchManual`) | 정수기 제품 사용 설명서(PDF) 본문 및 출처 페이지 검색 API 스키마 |
| [`openapi_schemas/purifier_billing_openapi.yaml`](openapi_schemas/purifier_billing_openapi.yaml) | OpenAPI Toolset *(선택)* | `purifier_billing` (`getInvoices`) | 외부 청구서 백엔드 서버 연동 시 사용하는 OpenAPI 3.0 스키마 *(미연동 시 Python 도구 내장 샘플 데이터로 자동 동작)* |

---

## 2. CX Agent Studio (CXAS)에서 Python 도구 등록하기

1. [CX Agent Studio 콘솔](https://ces.cloud.google.com/)에 접속하여 대상 앱(예: `purecare-gecx-agent`)을 선택하거나 새로 생성합니다.
2. 좌측 메뉴에서 **Tools**를 클릭하고 상단의 **+ Create**를 클릭합니다.
3. 아래 4개의 Python 도구를 각각 생성합니다:
   - **Tool Name / Display Name**: 파일명과 동일하게 입력 (`compare_invoices`, `get_invoice_breakdown`, `list_invoices`, `lookup_customer`)
   - **Type**: **`Python function`** 선택
   - **Execution Type**: 반드시 **`Synchronous` (동기식)**으로 설정
   - **Python Code**: [`python_tools/`](python_tools/) 폴더 내 각 `.py` 파일의 전체 코드를 복사하여 붙여넣고 **Save**를 클릭합니다.

> [!TIP]
> **외부 백엔드 API 서버 없이도 즉시 테스트 가능!**
> `python_tools/` 폴더의 Python 코드에는 외부 OpenAPI 도구(`purifier_billing_getInvoices`)가 연결되어 있지 않을 때 자동으로 동작하는 **내장 샘플 청구서 데이터(`_SAMPLE_BILLS`)**와 **Agent Assist 호환용 세션 변수 Fallback(`ACC-2026-001`)**이 함께 포함되어 있습니다. 따라서 별도의 백엔드 서버를 배포하지 않고 Python 코드만 붙여넣어도 시뮬레이터의 모든 청구서 테스트 케이스(TC-01 ~ TC-03, TC-06, TC-08, TC-09)가 즉시 정상 동작합니다.

---

## 3. 매뉴얼 검색 도구 등록하기 (`OpenAPI` 또는 `Data Store`)

정수기 매뉴얼 및 필터 교환 방법 검색을 위해 다음 두 가지 방식 중 하나를 선택하여 CXAS의 **Tools**에 등록합니다:

1. **방식 A — OpenAPI 검색 프록시 사용 (`custom_layout_search_2`)**:
   - CXAS 콘솔 > **Tools** > **+ Create** > **Type: `OpenAPI`** 선택
   - Tool Name: `custom_layout_search_2` 입력
   - [`openapi_schemas/manual_search_openapi.yaml`](openapi_schemas/manual_search_openapi.yaml) 내용을 붙여넣고 `servers.url`을 배포된 매뉴얼 검색 서비스 엔드포인트로 지정한 뒤 저장합니다.
2. **방식 B — Vertex AI Search `Data Store` 도구 사용**:
   - CXAS 콘솔 > **Tools** > **+ Create** > **Type: `Data store`** 선택
   - 정수기 사용 설명서 PDF가 색인된 Vertex AI Search Data Store를 연결하고 저장합니다.
   - *(참고: Data Store 도구 이름을 사용하는 경우, Companion Agent의 Guidance 카드 3 및 Model Guidance 내 도구 이름만 해당 Data Store 도구 이름으로 변경하면 동일하게 작동합니다.)*
