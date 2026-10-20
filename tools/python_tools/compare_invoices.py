"""정수기 렌탈 청구서 비교 분석 Python Function Tool (compare_invoices).

CX Agent Studio (CXAS) 및 Agent Assist Companion Agent 연동용 코드입니다.
- Agent Assist에서 직접 호출될 때를 대비해 세션 변수(context.state) 기본값 Fallback이 적용되어 있습니다.
- 외부 청구서 OpenAPI 도구(purifier_billing_getInvoices)가 연결되지 않은 환경에서도
  즉시 시뮬레이터 테스트가 가능하도록 내장 샘플 청구서 데이터(_SAMPLE_BILLS) Fallback을 포함합니다.
"""
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, List, Dict, Tuple, Any

CURRENCY = "KRW"
DEFAULT_ACCOUNT_ID = "ACC-2026-001"

LABELS = {
    "RENTAL_FEES": {"English": "Rental Fees"},
    "SERVICE_FEES": {"English": "Service Fees"},
    "DISCOUNTS": {"English": "Discounts"},
    "OTHER_FEES": {"English": "Other Fees"},
    "REGISTRATION_FEES": {"English": "Registration Fees"},
    "MOBILE_PAYMENTS": {"English": "Mobile Payments"},
    "BALANCE_TRANSFERS": {"English": "Balance Transfers"},
}


# === Entrypoint ===
def compare_invoices(month: str = "latest", compare_to: str = "previous") -> dict:
    """두 청구서의 금액을 비교하고 차이점과 상세 변동 요인을 설명합니다.

    Args:
        month: 분석 대상 월 - 'latest' (기본값), 'previous', 또는 특정 월 이름.
        compare_to: 비교 대상 월 - 'previous' (기본값) 또는 특정 월 이름.

    Returns:
        dict: 비교 분석 결과 정보 또는 에러 세부 정보.
    """
    state = getattr(context, "state", {}) if "context" in globals() else {}
    auth_status = state.get("auth_status") or "authenticated"
    if auth_status != "authenticated":
        return _auth_error()

    account_id = state.get("account_id") or DEFAULT_ACCOUNT_ID
    lang = state.get("active_language") or "Korean"

    try:
        summaries = _get_bills(account_id)
    except Exception as e:
        return _api_error(str(e))

    current = resolve_month(summaries, month)
    if current is None:
        avail = ", ".join(s["month"] for s in summarize_bills(summaries, lang)) or "none"
        return {"status": "error", "error": "month not found",
                "agent_action": "Tell the customer you have these invoices: " + avail + "."}

    if (compare_to or "previous").strip().lower() in ("previous", "prior", "last", ""):
        other = older_than(summaries, current)
    else:
        other = resolve_month(summaries, compare_to)

    if other is None:
        return {"status": "error", "error": "no comparison invoice",
                "agent_action": "Say you only have the February and March invoices."}
    if other["id"] == current["id"]:
        return {"status": "error", "error": "same invoice",
                "agent_action": "Those are the same invoice — ask for two different months."}

    try:
        cur_d = (_get_bills(account_id, bill_id=current["id"]) or [None])[0]
        oth_d = (_get_bills(account_id, bill_id=other["id"]) or [None])[0]
    except Exception as e:
        return _api_error(str(e))
    if cur_d is None or oth_d is None:
        return _api_error()

    result = compare(cur_d, oth_d, lang)
    result["status"] = "success"
    result["currency"] = CURRENCY
    result["agent_action"] = "State the difference and name the top one or two drivers."
    return result


def label(code: str, lang: str) -> str:
    return LABELS.get(code, {}).get("English", code or "")


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


_NAME_TO_NUM = {
    "january": 1, "jan": 1, "february": 2, "feb": 2, "march": 3, "mar": 3,
    "april": 4, "apr": 4, "may": 5, "june": 6, "jun": 6, "july": 7, "jul": 7,
    "august": 8, "aug": 8, "september": 9, "sep": 9, "october": 10, "oct": 10,
    "november": 11, "nov": 11, "december": 12, "dec": 12,
}


def sort_desc(bills: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return sorted(bills, key=lambda b: _parse(b["billDate"]), reverse=True)


def _parse_month_year(text: str) -> Tuple[Optional[int], Optional[int]]:
    month_num, year = None, None
    for tok in text.lower().replace(",", " ").replace("/", " ").replace("-", " ").split():
        tok = tok.rstrip(".")
        if month_num is None and tok in _NAME_TO_NUM:
            month_num = _NAME_TO_NUM[tok]
        elif year is None and len(tok) == 4 and tok.isdigit():
            year = int(tok)
    return month_num, year


def match_month_name(bills: List[Dict[str, Any]], name: str) -> Optional[Dict[str, Any]]:
    month_num, year = _parse_month_year(name)
    if month_num is None:
        return None
    for b in sort_desc(bills):
        e = _parse(b["billingPeriod"]["endDateTime"])
        if e.month == month_num and (year is None or e.year == year):
            return b
    return None


def resolve_month(bills: List[Dict[str, Any]], month: str) -> Optional[Dict[str, Any]]:
    bills = sort_desc(bills)
    if not bills:
        return None
    m = (month or "latest").strip().lower()
    if m in ("latest", "newest", ""):
        return bills[0]
    if m in ("previous", "prior", "last"):
        return bills[1] if len(bills) > 1 else None
    return match_month_name(bills, m)


def older_than(bills: List[Dict[str, Any]], bill: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    bills = sort_desc(bills)
    ids = [b["id"] for b in bills]
    if bill["id"] not in ids:
        return None
    idx = ids.index(bill["id"])
    return bills[idx + 1] if idx + 1 < len(bills) else None


def account_summary_block(bill: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    for b in bill.get("billSummary", []):
        if b.get("logicalResource", {}).get("name") == "ACCOUNT_SUMMARY":
            return b
    return None


def _driver_note(prev: float, cur: float, lang: str) -> str:
    if abs(prev) < 0.005 <= abs(cur):
        return "new this month"
    if prev < 0 and cur < 0 and abs(cur) < abs(prev):
        return "smaller credit"
    if cur > prev:
        return "higher"
    return "lower"


def _cat_nets(bill: Dict[str, Any]) -> Dict[str, float]:
    block = account_summary_block(bill) or {}
    return {it.get("billSummaryItemCategory"): it.get("netAmount", {}).get("value", 0.0)
            for it in block.get("billSummaryItem", [])}


def compare(current: Dict[str, Any], previous: Dict[str, Any], lang: str) -> Dict[str, Any]:
    cur, prev = _cat_nets(current), _cat_nets(previous)
    rows = []
    for code in set(cur) | set(prev):
        change = cur.get(code, 0.0) - prev.get(code, 0.0)
        if round_money(change) == 0.0:
            continue
        rows.append((abs(change), change, code,
                     {"category": label(code, lang), "change": round_money(change),
                      "note": _driver_note(prev.get(code, 0.0), cur.get(code, 0.0), lang)}))
    rows.sort(key=lambda r: (-r[0], -r[1], r[2]))
    ct = current.get("amountDue", {}).get("value", 0.0)
    pt = previous.get("amountDue", {}).get("value", 0.0)
    diff = round_money(ct - pt)
    direction = "higher" if diff > 0 else ("lower" if diff < 0 else "the same")
    return {
        "current": {"month": month_label(current, lang), "total": round_money(ct)},
        "previous": {"month": month_label(previous, lang), "total": round_money(pt)},
        "difference": {"amount": abs(diff), "direction": direction},
        "top_drivers": [r[3] for r in rows[:3]],
    }


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
        "billSummary": [{
            "logicalResource": {"name": "ACCOUNT_SUMMARY"},
            "billSummaryItem": [
                {"billSummaryItemCategory": "RENTAL_FEES", "netAmount": {"value": 168900.0}},
                {"billSummaryItemCategory": "SERVICE_FEES", "netAmount": {"value": 15000.0}},
                {"billSummaryItemCategory": "OTHER_FEES", "netAmount": {"value": 12000.0}},
                {"billSummaryItemCategory": "DISCOUNTS", "netAmount": {"value": -190530.0}},
            ],
        }],
    },
    {
        "id": "BILL-2026-02",
        "billDate": "2026-02-28T00:00:00Z",
        "paymentDueDate": "2026-03-15T00:00:00Z",
        "billingPeriod": {"startDateTime": "2026-01-28T00:00:00Z", "endDateTime": "2026-02-27T00:00:00Z"},
        "amountDue": {"value": 3870.0},
        "billSummary": [{
            "logicalResource": {"name": "ACCOUNT_SUMMARY"},
            "billSummaryItem": [
                {"billSummaryItemCategory": "RENTAL_FEES", "netAmount": {"value": 168900.0}},
                {"billSummaryItemCategory": "SERVICE_FEES", "netAmount": {"value": 15000.0}},
                {"billSummaryItemCategory": "OTHER_FEES", "netAmount": {"value": 0.0}},
                {"billSummaryItemCategory": "DISCOUNTS", "netAmount": {"value": -180030.0}},
            ],
        }],
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


def _get_bills(account_id: str, bill_id: str = "") -> List[Dict[str, Any]]:
    if "tools" in globals() and hasattr(tools, "purifier_billing_getInvoices"):
        args = {"customer_id": account_id}
        if bill_id:
            args["bill_id"] = bill_id
        else:
            args["fields"] = "id,billDate,billingPeriod,amountDue,paymentDueDate"
        res = _unwrap(tools.purifier_billing_getInvoices(args))
        if res:
            return res
    if bill_id:
        return [b for b in _SAMPLE_BILLS if b["id"] == bill_id]
    return _SAMPLE_BILLS


def _auth_error():
    return {"status": "error", "error": "unauthenticated",
            "agent_action": "Explain you cannot share billing details without verification."}


def _api_error(detail: str = ""):
    return {"status": "error", "error": "billing system unavailable", "detail": detail,
            "agent_action": "Apologise and offer to connect them to a specialist."}
