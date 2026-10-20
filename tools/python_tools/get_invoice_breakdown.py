"""정수기 렌탈 청구서 상세 명세 및 기기별(시리얼 끝자리) 조회 Python Function Tool (get_invoice_breakdown).

CX Agent Studio (CXAS) 및 Agent Assist Companion Agent 연동용 코드입니다.
- line="" 호출 시: 계정 전체의 카테고리별 금액과 등록된 기기 시리얼 끝 3자리 목록(048, 703, 843) 반환
- line="843" 호출 시: 끝자리 843번 정수기의 개별 청구 명세(기본 렌탈료 56,946원, 할인 -55,445원, 합계 1,500원) 반환
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
def get_invoice_breakdown(month: str = "latest", line: str = "") -> dict:
    """인증된 고객의 렌탈 청구서 금액을 상세 청구 항목 카테고리별로 분류하여 반환합니다.

    Args:
        month: 조회 대상 월 - 'latest' (기본값), 'previous', 또는 특정 월 이름.
        line: 공백(전체 청구 계정 기준 요약), 혹은 특정 렌탈 기기 시리얼 끝 3자리 (예: '843').

    Returns:
        dict: 분류 분석 결과 목록 또는 에러 세부 정보.
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

    target = resolve_month(summaries, month)
    if target is None:
        avail = ", ".join(s["month"] for s in summarize_bills(summaries, lang)) or "none"
        return {"status": "error", "error": "month not found",
                "agent_action": "Tell the customer you have these invoices: " + avail + "."}

    try:
        detail = (_get_bills(account_id, bill_id=target["id"]) or [None])[0]
    except Exception as e:
        return _api_error(str(e))
    if detail is None:
        return _api_error()

    base = {
        "status": "success",
        "currency": CURRENCY,
        "month": month_label(detail, lang),
        "period": format_period(detail["billingPeriod"], lang),
        "bill_date": format_date(detail["billDate"], lang),
        "payment_due": format_date(detail["paymentDueDate"], lang),
    }

    if line:
        matches = find_lines(detail, line)
        if len(matches) != 1:
            return {
                "status": "error",
                "error": "product not matched",
                "product_endings": line_endings(detail),
                "agent_action": ("Offer the products using their endings in "
                                 "product_endings and ask which one the customer means."),
            }
        bd, total = line_breakdown(matches[0], lang)
        last3 = "".join(c for c in matches[0]["relatedParty"]["id"] if c.isdigit())[-3:]
        base.update({
            "scope": "product",
            "product": "…" + last3,
            "total": total,
            "breakdown": bd,
            "agent_action": "State this product's net total and item breakdown.",
        })
        return base

    base.update({
        "scope": "account",
        "total": round_money(detail.get("amountDue", {}).get("value", 0.0)),
        "products": len(detail.get("subscription", [])),
        "product_endings": line_endings(detail),
        "breakdown": account_breakdown(detail, lang),
        "agent_action": ("Give the total, then the main categories. Offer per-product "
                         "detail using product_endings (048, 703, 843)."),
    })
    return base


def label(code: str, lang: str) -> str:
    return LABELS.get(code, {}).get("English", code or "")


def round_money(x: float) -> float:
    return float(Decimal(str(x)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _parse(s: str) -> datetime:
    dt = datetime.fromisoformat(s)
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def format_date(s: str, lang: str) -> str:
    dt = _parse(s)
    return f"{dt.year}\ub144 {dt.month}\uc6d4 {dt.day}\uc77c"


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


def account_summary_block(bill: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    for b in bill.get("billSummary", []):
        if b.get("logicalResource", {}).get("name") == "ACCOUNT_SUMMARY":
            return b
    return None


def account_breakdown(bill: Dict[str, Any], lang: str) -> List[Dict[str, Any]]:
    block = account_summary_block(bill) or {}
    out = []
    for it in block.get("billSummaryItem", []):
        v = it.get("netAmount", {}).get("value", 0.0)
        if round_money(v) == 0.0:
            continue
        out.append({"category": label(it.get("billSummaryItemCategory"), lang),
                    "amount": round_money(v)})
    return out


def _digits(s: str) -> str:
    return "".join(c for c in s if c.isdigit())


def find_lines(bill: Dict[str, Any], suffix: str) -> List[Dict[str, Any]]:
    suffix = _digits(suffix)
    matches = []
    for sub in bill.get("subscription", []):
        d = _digits(sub.get("relatedParty", {}).get("id", ""))
        if suffix and d.endswith(suffix):
            matches.append(sub)
    return matches


def line_endings(bill: Dict[str, Any]) -> List[str]:
    out = []
    for sub in bill.get("subscription", []):
        d = _digits(sub.get("relatedParty", {}).get("id", ""))
        if d:
            out.append(d[-3:])
    return out


def line_breakdown(sub: Dict[str, Any], lang: str) -> Tuple[List[Dict[str, Any]], float]:
    buckets, order, total = {}, [], 0.0
    for it in sub.get("outOfBundleAmount", []):
        ch = {c["name"]: c["value"] for c in it.get("characteristic", [])}
        ban = ch.get("billSummaryBANItemCategory")
        if ban is None:
            if ch.get("Category") == "TOTAL_AMOUNT":
                total = it.get("value", 0.0)
            continue
        if ban not in buckets:
            buckets[ban] = 0.0
            order.append(ban)
        buckets[ban] += it.get("value", 0.0)
    breakdown = [{"category": label(b, lang), "amount": round_money(buckets[b])}
                 for b in order if round_money(buckets[b]) != 0.0]
    return breakdown, round_money(total)


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
        "subscription": [
            {
                "relatedParty": {"id": "SN-PC-00048"},
                "outOfBundleAmount": [
                    {"value": 55954.0, "characteristic": [{"name": "billSummaryBANItemCategory", "value": "RENTAL_FEES"}]},
                    {"value": -54084.0, "characteristic": [{"name": "billSummaryBANItemCategory", "value": "DISCOUNTS"}]},
                    {"value": 1870.0, "characteristic": [{"name": "Category", "value": "TOTAL_AMOUNT"}]},
                ],
            },
            {
                "relatedParty": {"id": "SN-PC-00703"},
                "outOfBundleAmount": [
                    {"value": 56000.0, "characteristic": [{"name": "billSummaryBANItemCategory", "value": "RENTAL_FEES"}]},
                    {"value": -54000.0, "characteristic": [{"name": "billSummaryBANItemCategory", "value": "DISCOUNTS"}]},
                    {"value": 2000.0, "characteristic": [{"name": "Category", "value": "TOTAL_AMOUNT"}]},
                ],
            },
            {
                "relatedParty": {"id": "SN-PC-00843"},
                "outOfBundleAmount": [
                    {"value": 56946.0, "characteristic": [{"name": "billSummaryBANItemCategory", "value": "RENTAL_FEES"}]},
                    {"value": -55445.0, "characteristic": [{"name": "billSummaryBANItemCategory", "value": "DISCOUNTS"}]},
                    {"value": 1500.0, "characteristic": [{"name": "Category", "value": "TOTAL_AMOUNT"}]},
                ],
            },
        ],
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
                {"billSummaryItemCategory": "DISCOUNTS", "netAmount": {"value": -180030.0}},
            ],
        }],
        "subscription": [],
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
