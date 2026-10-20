"""월별 렌탈 청구서 발행 목록 조회 Python Function Tool (list_invoices).

CX Agent Studio (CXAS) 및 Agent Assist Companion Agent 연동용 코드입니다.
"""
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Dict, Any

CURRENCY = "KRW"
DEFAULT_ACCOUNT_ID = "ACC-2026-001"


# === Entrypoint ===
def list_invoices() -> dict:
    """인증된 고객에게 발급된 렌탈 요금 고지서 목록을 최신순으로 정렬하여 조회합니다.

    Returns:
        dict: 고지서 요약 목록 리스트 결과 또는 에러 세부 정보.
    """
    state = getattr(context, "state", {}) if "context" in globals() else {}
    auth_status = state.get("auth_status") or "authenticated"
    if auth_status != "authenticated":
        return {
            "status": "error",
            "error": "unauthenticated",
            "agent_action": "Explain you cannot share billing details without verification.",
        }

    account_id = state.get("account_id") or DEFAULT_ACCOUNT_ID
    lang = state.get("active_language") or "Korean"

    try:
        summaries = _get_bills(account_id)
    except Exception as e:
        return {
            "status": "error",
            "error": "billing system unavailable",
            "detail": str(e),
            "agent_action": "Apologise and offer to connect them to a specialist.",
        }

    return {
        "status": "success",
        "currency": CURRENCY,
        "invoices": summarize_bills(summaries, lang),
        "agent_action": "Tell the customer which invoices you can discuss; ask which they'd like.",
    }


def round_money(x: float) -> float:
    return float(Decimal(str(x)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _parse(s: str) -> datetime:
    dt = datetime.fromisoformat(s)
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def format_period(bp: Dict[str, Any], lang: str) -> str:
    s, e = _parse(bp["startDateTime"]), _parse(bp["endDateTime"])
    if s.year == e.year:
        return f"{s.year}\ub144 {s.month}\uc6d4 {s.day}\uc77c ~ {e.month}\uc6d4 {e.day}\uc77c"
    return f"{s.year}\ub144 {s.month}\uc6d4 {s.day}\uc77c ~ {e.year}\ub144 {e.month}\uc6d4 {e.day}\uc77c"


def month_label(bill: Dict[str, Any], lang: str) -> str:
    e = _parse(bill["billingPeriod"]["endDateTime"])
    return f"{e.year}\ub144 {e.month}\uc6d4"


def sort_desc(bills: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return sorted(bills, key=lambda b: _parse(b["billDate"]), reverse=True)


def summarize_bills(bills: List[Dict[str, Any]], lang: str) -> List[Dict[str, Any]]:
    return [{"month": month_label(b, lang),
             "period": format_period(b["billingPeriod"], lang),
             "total": round_money(b.get("amountDue", {}).get("value", 0.0))}
            for b in sort_desc(bills)]


_SAMPLE_BILLS = [
    {
        "id": "BILL-2026-03",
        "billDate": "2026-03-28T00:00:00Z",
        "paymentDueDate": "2026-04-15T00:00:00Z",
        "billingPeriod": {"startDateTime": "2026-02-28T00:00:00Z", "endDateTime": "2026-03-27T00:00:00Z"},
        "amountDue": {"value": 5370.0},
    },
    {
        "id": "BILL-2026-02",
        "billDate": "2026-02-28T00:00:00Z",
        "paymentDueDate": "2026-03-15T00:00:00Z",
        "billingPeriod": {"startDateTime": "2026-01-28T00:00:00Z", "endDateTime": "2026-02-27T00:00:00Z"},
        "amountDue": {"value": 3870.0},
    },
]


def _unwrap(resp):
    if hasattr(resp, "json") and callable(getattr(resp, "json")):
        try:
            resp = resp.json()
        except Exception:
            return []
    for _ in range(5):
        if isinstance(resp, list):
            return resp
        if not isinstance(resp, dict):
            return []
        for k in ("output", "result", "response", "results", "data", "body"):
            if k in resp:
                resp = resp[k]
                break
        else:
            return []
    return resp if isinstance(resp, list) else []


def _get_bills(account_id: str) -> List[Dict[str, Any]]:
    if "tools" in globals() and hasattr(tools, "purifier_billing_getInvoices"):
        args = {
            "customer_id": account_id,
            "fields": "id,billDate,billingPeriod,amountDue,paymentDueDate",
        }
        res = _unwrap(tools.purifier_billing_getInvoices(args))
        if res:
            return res
    return _SAMPLE_BILLS
