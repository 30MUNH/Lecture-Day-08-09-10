# Quality report — Lab Day 10

**run_id:** `2026-06-10T07-25Z`  
**Ngày:** 2026-06-10

---

## 1. Tóm tắt số liệu

| Chỉ số | Trước (Chưa Clean/Baseline) | Sau (Đã Fix & Clean) | Ghi chú |
|--------|----------------------------|---------------------|---------|
| **raw_records** | 247 | 247 | Tổng số chunk đầu vào thô |
| **cleaned_records** | 0 (Halt ở E6) | 29 | Số lượng chunk sạch được ghi vào ChromaDB |
| **quarantine_records** | 0 (Halt) | 218 | Số lượng chunk lỗi bị cách ly |
| **Expectation halt?** | CÓ (E6 thất bại) | KHÔNG (Tất cả expectations PASS) | Pipeline chạy thành công trọn vẹn |

---

## 2. Before / after retrieval (Đánh giá chất lượng tìm kiếm)

Dữ liệu so sánh chi tiết được kết xuất tại các tệp:
- Bản sạch: [after_fix_eval.csv](file:///d:/Vin/day10/Lecture-Day-08-09-10/day10/lab/artifacts/eval/after_fix_eval.csv)
- Bản hỏng (inject): [after_inject_bad.csv](file:///d:/Vin/day10/Lecture-Day-08-09-10/day10/lab/artifacts/eval/after_inject_bad.csv)

### Câu hỏi then chốt: hoàn tiền (`q_refund_window`)
- **Trước khi fix (injected bad):**
  - **top1_preview**: `Yêu cầu hoàn tiền được chấp nhận trong vòng 14 ngày làm việc kể từ xác nhận đơn.`
  - **hits_forbidden**: `yes` (Tìm thấy thông tin sai lệch "14 ngày làm việc").
- **Sau khi fix (clean run):**
  - **top1_preview**: `Yêu cầu hoàn tiền được chấp nhận trong vòng 7 ngày làm việc kể từ xác nhận đơn. [cleaned: stale_refund_window]`
  - **hits_forbidden**: `no` (Thông tin đã được sửa tự động về "7 ngày làm việc").

### Đánh giá chất lượng HR Leave Policy (`q_leave_version`)
- **Trước khi lọc stale text (năm 2025):**
  - AI retrieve trúng câu `"Nhân viên dưới 3 năm kinh nghiệm được 10 ngày phép năm"` (tải trọng sai, thuộc chính sách 2025 cũ).
- **Sau khi lọc stale text (năm 2026):**
  - AI retrieve đúng câu `"Nhân viên dưới 3 năm kinh nghiệm được 12 ngày phép năm theo chính sách 2026."`
  - **contains_expected**: `yes`
  - **hits_forbidden**: `no`

---

## 3. Freshness & monitor

Kết quả kiểm tra freshness:
```json
freshness_check=FAIL {"latest_exported_at": "2026-04-11T00:00:00", "age_hours": 1447.429, "sla_hours": 24.0, "reason": "freshness_sla_exceeded"}
```
- **Ý nghĩa**: SLA freshness được cấu hình là 24 giờ. Vì dữ liệu trong export CSV là từ tháng 4 năm 2026 (`2026-04-11`), trong khi thời gian hệ thống hiện tại là tháng 6 năm 2026, nên tuổi của dữ liệu vượt quá mức cho phép. Đây là một cảnh báo đúng đắn giúp kỹ sư phát hiện hệ thống CRM/ERP nguồn bị ngưng sync dữ liệu.

---

## 4. Corruption inject (Sprint 3)

- **Cách thực hiện**: Chạy lệnh `python etl_pipeline.py run --run-id inject-bad --no-refund-fix --skip-validate`. Lệnh này vô hiệu hóa việc sửa đổi quy định hoàn tiền (`--no-refund-fix`) đồng thời bỏ qua việc kiểm tra chặn của expectations (`--skip-validate`).
- **Cách phát hiện**: 
  - Expectation `refund_no_stale_14d_window` ngay lập tức báo trạng thái `FAIL (halt)` với violations = 1.
  - Khi chạy thử nghiệm truy vấn ngữ nghĩa, câu hỏi `q_refund_window` lập tức trả về kết quả chứa `"14 ngày làm việc"` (đây là thông tin sai lệch nghiêm trọng, có thể gây thiệt hại tài chính cho công ty).
