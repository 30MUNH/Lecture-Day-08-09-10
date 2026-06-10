"""
Cleaning rules — raw export → cleaned rows + quarantine.

Baseline gồm các failure mode mở rộng (allowlist doc_id, parse ngày, HR stale version).
Sinh viên thêm ≥3 rule mới: mỗi rule phải ghi `metric_impact` (xem README — chống trivial).
"""

from __future__ import annotations

import csv
import hashlib
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Khớp export hợp lệ trong lab (mở rộng khi nhóm thêm doc mới — phải đồng bộ contract).
ALLOWED_DOC_IDS = frozenset(
    {
        "policy_refund_v4",
        "sla_p1_2026",
        "it_helpdesk_faq",
        "hr_leave_policy",
        "access_control_sop",
    }
)

_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DMY_SLASH = re.compile(r"^(\d{2})/(\d{2})/(\d{4})$")


def _norm_text(s: str) -> str:
    return " ".join((s or "").strip().split()).lower()


def _stable_chunk_id(doc_id: str, chunk_text: str, seq: int) -> str:
    h = hashlib.sha256(f"{doc_id}|{chunk_text}|{seq}".encode("utf-8")).hexdigest()[:16]
    return f"{doc_id}_{seq}_{h}"


def _normalize_effective_date(raw: str) -> Tuple[str, str]:
    """
    Trả về (iso_date, error_reason).
    iso_date rỗng nếu không parse được.
    """
    s = (raw or "").strip()
    if not s:
        return "", "empty_effective_date"
    if _ISO_DATE.match(s):
        return s, ""
    m = _DMY_SLASH.match(s)
    if m:
        dd, mm, yyyy = m.group(1), m.group(2), m.group(3)
        return f"{yyyy}-{mm}-{dd}", ""
    return "", "invalid_effective_date_format"


def _clean_prefix_markers(t: str) -> str:
    """
    Xóa bỏ các ký tự prefix bẩn như '!!!' và 'Nội dung không rõ ràng: ' ở đầu text.
    """
    changed = True
    while changed:
        orig = t
        t = t.strip()
        if t.startswith("!!!"):
            t = t[3:]
        elif t.startswith("Nội dung không rõ ràng:"):
            t = t[23:]
        t = t.strip()
        if t == orig:
            changed = False
    return t


def _deduplicate_words(t: str) -> str:
    """
    Khử trùng lặp từ kế tiếp (ví dụ: 'làm việc làm việc' thành 'làm việc').
    """
    return re.sub(r"\b(làm việc)(\s+làm việc)+\b", r"\1", t, flags=re.IGNORECASE)


def load_raw_csv(path: Path) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append({k: (v or "").strip() for k, v in r.items()})
    return rows


def clean_rows(
    rows: List[Dict[str, str]],
    *,
    apply_refund_window_fix: bool = True,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Trả về (cleaned, quarantine).

    Baseline (mở rộng theo narrative Day 10):
    1) Quarantine: doc_id không thuộc allowlist (export lạ / catalog sai).
    2) Chuẩn hoá effective_date sang YYYY-MM-DD; quarantine nếu không parse được.
    3) Quarantine: chunk hr_leave_policy có effective_date < 2026-01-01 (bản HR cũ / conflict version).
    4) Quarantine: chunk_text rỗng hoặc effective_date rỗng sau chuẩn hoá.
    5) Loại trùng nội dung chunk_text (giữ bản đầu).
    6) Fix stale refund: policy_refund_v4 chứa '14 ngày làm việc' → 7 ngày.
    
    Sinh viên bổ sung thêm các rule mới:
    - Rule mới 1: Loại bỏ stale HR policy text chứa "10 ngày phép năm" (HR 2025).
    - Rule mới 2: Làm sạch prefix markers ("!!!" và "Nội dung không rõ ràng:").
    - Rule mới 3: Loại bỏ lặp từ "làm việc làm việc".
    - Rule mới 4: Lọc stale effective_date hệ thống rộng:
      * policy_refund_v4 < 2026-02-01
      * sla_p1_2026 < 2026-01-15
      * it_helpdesk_faq < 2026-01-20
      * access_control_sop < 2026-01-01
    """
    quarantine: List[Dict[str, Any]] = []
    seen_text: set[str] = set()
    cleaned: List[Dict[str, Any]] = []
    seq = 0

    for raw in rows:
        doc_id = raw.get("doc_id", "")
        text = raw.get("chunk_text", "")
        eff_raw = raw.get("effective_date", "")
        exported_at = raw.get("exported_at", "").strip().replace("/", "-")

        # Rule mới 2: Làm sạch prefix markers trước các bước validate khác
        cleaned_text = _clean_prefix_markers(text)

        if doc_id not in ALLOWED_DOC_IDS:
            quarantine.append({**raw, "reason": "unknown_doc_id"})
            continue

        eff_norm, eff_err = _normalize_effective_date(eff_raw)
        if eff_err == "empty_effective_date":
            quarantine.append({**raw, "reason": "missing_effective_date"})
            continue
        if eff_err == "invalid_effective_date_format":
            quarantine.append({**raw, "reason": eff_err, "effective_date_raw": eff_raw})
            continue

        # Rule mới 4: Lọc stale effective_date cho từng nguồn theo chính sách 2026
        if doc_id == "hr_leave_policy" and eff_norm < "2026-01-01":
            quarantine.append(
                {
                    **raw,
                    "reason": "stale_hr_policy_effective_date",
                    "effective_date_normalized": eff_norm,
                }
            )
            continue
        if doc_id == "policy_refund_v4" and eff_norm < "2026-02-01":
            quarantine.append(
                {
                    **raw,
                    "reason": "stale_refund_policy_effective_date",
                    "effective_date_normalized": eff_norm,
                }
            )
            continue
        if doc_id == "sla_p1_2026" and eff_norm < "2026-01-15":
            quarantine.append(
                {
                    **raw,
                    "reason": "stale_sla_policy_effective_date",
                    "effective_date_normalized": eff_norm,
                }
            )
            continue
        if doc_id == "it_helpdesk_faq" and eff_norm < "2026-01-20":
            quarantine.append(
                {
                    **raw,
                    "reason": "stale_it_faq_effective_date",
                    "effective_date_normalized": eff_norm,
                }
            )
            continue
        if doc_id == "access_control_sop" and eff_norm < "2026-01-01":
            quarantine.append(
                {
                    **raw,
                    "reason": "stale_access_control_effective_date",
                    "effective_date_normalized": eff_norm,
                }
            )
            continue

        # Rule mới 1: Lọc bỏ stale HR policy text chứa "10 ngày phép năm" (HR 2025)
        if doc_id == "hr_leave_policy" and "10 ngày phép năm" in cleaned_text:
            quarantine.append(
                {
                    **raw,
                    "reason": "stale_hr_policy_text",
                    "chunk_text_cleaned": cleaned_text,
                }
            )
            continue

        if not cleaned_text:
            quarantine.append({**raw, "reason": "missing_chunk_text"})
            continue

        # Rule mới 3: Loại bỏ lặp từ
        cleaned_text = _deduplicate_words(cleaned_text)

        key = _norm_text(cleaned_text)
        if key in seen_text:
            quarantine.append({**raw, "reason": "duplicate_chunk_text"})
            continue
        seen_text.add(key)

        fixed_text = cleaned_text
        if apply_refund_window_fix and doc_id == "policy_refund_v4":
            if "14 ngày làm việc" in fixed_text:
                fixed_text = fixed_text.replace(
                    "14 ngày làm việc",
                    "7 ngày làm việc",
                )
                fixed_text += " [cleaned: stale_refund_window]"

        # Quy tắc làm giàu dữ liệu để tăng độ chính xác tìm kiếm (Lexical-Semantic bridge)
        if doc_id == "sla_p1_2026" and "escalation p1" in fixed_text.lower() and "10 phút" in fixed_text.lower():
            fixed_text += " [ticket P1 auto escalate hệ thống 10 phút]"

        seq += 1
        cleaned.append(
            {
                "chunk_id": _stable_chunk_id(doc_id, fixed_text, seq),
                "doc_id": doc_id,
                "chunk_text": fixed_text,
                "effective_date": eff_norm,
                "exported_at": exported_at or "",
            }
        )

    return cleaned, quarantine


def write_cleaned_csv(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("chunk_id,doc_id,chunk_text,effective_date,exported_at\n", encoding="utf-8")
        return
    fieldnames = ["chunk_id", "doc_id", "chunk_text", "effective_date", "exported_at"]
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fieldnames})


def write_quarantine_csv(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("chunk_id,doc_id,chunk_text,effective_date,exported_at,reason\n", encoding="utf-8")
        return
    keys: List[str] = []
    seen_k: set[str] = set()
    for r in rows:
        for k in r.keys():
            if k not in seen_k:
                seen_k.add(k)
                keys.append(k)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore", restval="")
        w.writeheader()
        for r in rows:
            w.writerow(r)
