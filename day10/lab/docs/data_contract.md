# Data contract — Lab Day 10

Data contract là cam kết chất lượng dữ liệu giữa nhóm Data Engineering (cung cấp) và nhóm AI/RAG (tiêu thụ). File cấu hình gốc được quản lý tập trung tại `contracts/data_contract.yaml`.

---

## 1. Nguồn dữ liệu (source map)

| Nguồn | Phương thức ingest | Failure mode chính | Metric / alert |
|-------|-------------------|-------------------|----------------|
| `policy_refund_v4` | Batch export CSV | Format date sai, Stale refund window (14d) | Sửa tự động hoặc Quarantine |
| `sla_p1_2026` | Batch export CSV | Date hiệu lực cũ (< 2026-01-15), Lặp từ | Quarantine nếu cũ, Tự động dedupe từ |
| `it_helpdesk_faq` | Batch export CSV | Date hiệu lực cũ (< 2026-01-20), Trống | Quarantine nếu cũ hoặc trống |
| `hr_leave_policy` | Batch export CSV | Dữ liệu cũ "10 ngày phép năm", Date cũ | Quarantine stale text, Quarantine date cũ |
| `access_control_sop` | Batch export CSV | Thiếu doc_id (quarantined), Trống text | Quarantine nếu không khớp allowlist |

---

## 2. Schema cleaned

| Cột | Kiểu | Bắt buộc | Ghi chú |
|-----|------|----------|---------|
| `chunk_id` | string | Có | Hash SHA-256 duy nhất: `doc_id|chunk_text|seq` |
| `doc_id` | string | Có | Tên tài liệu nguồn canonical (ví dụ: `policy_refund_v4`) |
| `chunk_text` | string | Có | Đoạn văn bản sau khi chuẩn hóa prefix, từ lặp, và làm giàu |
| `effective_date` | date | Có | Ngày hiệu lực của chính sách, định dạng ISO `YYYY-MM-DD` |
| `exported_at` | datetime | Có | Thời điểm xuất dữ liệu, định dạng ISO `YYYY-MM-DDTHH:MM:SS` |

---

## 3. Quy tắc quarantine vs drop

- **Quarantine**: Mọi dòng dữ liệu vi phạm các quy định về chất lượng (ví dụ: sai format date, trùng lặp text, ngày hiệu lực quá cũ, chứa thông tin chính sách cũ) đều được chuyển vào khu vực cách ly `artifacts/quarantine/quarantine_<run_id>.csv` thay vì bị xóa bỏ hoàn toàn (drop).
- **Quy trình xử lý**: Nhóm Data Owner sẽ review các file quarantine hàng tuần. Nếu phát hiện lỗi từ nguồn xuất bản, họ sẽ yêu cầu hệ thống CRM/ERP nguồn export lại. Nếu lỗi do code transform (ví dụ: parser date chưa hoàn thiện), Data Engineer sẽ sửa rule và rerun pipeline.

---

## 4. Phiên bản & canonical

- **Source of truth**: Các file tài liệu tại thư mục `data/docs/` là canonical source (nguồn chính thống duy nhất).
- **Phiên bản hiện hành**:
  - `policy_refund_v4.txt`: Chỉ chấp nhận phiên bản v4 với thời gian hoàn tiền là **7 ngày làm việc**. Phiên bản cũ v3 (14 ngày làm việc) bị coi là stale.
  - `hr_leave_policy.txt`: Chỉ chấp nhận số ngày phép năm 12/15/18 ngày theo chính sách 2026. Mọi văn bản chứa "10 ngày phép năm" (năm 2025) là stale và bị quarantine.
  - `sla_p1_2026.txt`: SLA giải quyết ticket P1 là **4 giờ**, phản hồi ban đầu **15 phút**. Bản v2025 cũ (resolution 6 giờ) bị loại bỏ.
