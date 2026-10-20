"""고객 렌탈 멤버십 계약 정보 및 잔액 조회 Python Function Tool (lookup_customer).

CX Agent Studio (CXAS) 및 Agent Assist Companion Agent 연동용 코드입니다.
"""

DEFAULT_ACCOUNT_ID = "ACC-2026-001"


# === Entrypoint ===
def lookup_customer(customer_id: str = DEFAULT_ACCOUNT_ID) -> dict:
    """고객 ID를 기반으로 해당 고객의 렌탈 계정 및 서비스 활성화 세부 정보를 조회합니다.

    Args:
        customer_id: 조회할 고객의 계정 ID (기본값: 'ACC-2026-001').

    Returns:
        dict: 가입 상품 정보, 계정 상태, 잔액을 포함한 계정 정보 또는 에러 정보.
    """
    state = getattr(context, "state", {}) if "context" in globals() else {}
    auth_status = state.get("auth_status") or "authenticated"
    if auth_status != "authenticated":
        return {
            "status": "error",
            "error": "Account lookup requires an authenticated session.",
            "agent_action": "Inform the customer that you cannot access account details without verification.",
        }

    customer_id = customer_id or state.get("account_id") or DEFAULT_ACCOUNT_ID

    return {
        "status": "success",
        "account": {
            "customer_id": customer_id,
            "plan": "Purifier Care Membership",
            "balance": "0원",
            "next_billing_date": "2026-04-15",
            "service_status": "active",
        },
    }
