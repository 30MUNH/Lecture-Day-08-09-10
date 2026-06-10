# Runbook — Lab Day 10 (Sửa sự cố chất lượng dữ liệu RAG)

Tài liệu này hướng dẫn xử lý nhanh khi có lỗi dữ liệu hoặc cảnh báo từ hệ thống observability của pipeline dữ liệu tri thức.

---

## Symptom

1. **User / Agent báo lỗi**: Người dùng hoặc AI agent phản hồi sai thông tin chính sách hoàn tiền (ví dụ: trả lời "14 ngày làm việc" thay vì "7 ngày").
2. **Cảnh báo từ CI/CD hoặc Scheduler**: Pipeline chạy thất bại (exit code 1) ở bước kiểm định chất lượng (`run_expectations` ném lỗi halt).
3. **Cảnh báo freshness**: Hệ thống báo động đỏ freshness check `FAIL` do dữ liệu quá cũ.

---

## Detection

Quan sát các chỉ số sau trên dashboard giám sát hoặc log:
- **`freshness_check`**: FAIL (ví dụ: `age_hours` vượt quá SLA `24`).
- **`Expectation halt`**: Báo lỗi cụ thể, ví dụ: `refund_no_stale_14d_window` FAIL hoặc `hr_leave_no_stale_10d_annual` FAIL.
- **`quarantine_records`**: Tăng đột biến (chứng tỏ dữ liệu đầu vào bị lỗi nhiều, bị cách ly hàng loạt).

---

## Diagnosis

Khi phát hiện sự cố, thực hiện chẩn đoán theo các bước sau:

| Bước | Việc làm | Kết quả mong đợi |
|------|----------|------------------|
| **1** | Kiểm tra file manifest chạy gần nhất tại `artifacts/manifests/manifest_<run_id>.json` | Xác định thời điểm export gần nhất (`latest_exported_at`) và các cờ cấu hình chạy. |
| **2** | Mở file quarantine tương ứng tại `artifacts/quarantine/quarantine_<run_id>.csv` | Tìm kiếm các dòng có lý do cách ly cụ thể (`reason`) như `stale_hr_policy_text`, `stale_refund_policy_effective_date`, `invalid_effective_date_format`. |
| **3** | Chạy đánh giá retrieval offline: `python eval_retrieval.py` | Kiểm tra xem các câu hỏi quan trọng có bị tụt độ chính xác hoặc dính từ cấm (`hits_forbidden == yes`) hay không. |

---

## Mitigation

1. **Rerun pipeline phục hồi**: Nếu lỗi do một tệp tạm thời hoặc lỗi mạng khi ghi DB, dọn dẹp `./chroma_db` và rerun pipeline sạch:
   ```bash
   Remove-Item -Recurse -Force ./chroma_db
   python etl_pipeline.py run
   ```
2. **Khôi phục bản sao lưu (Rollback)**: Trong trường hợp dữ liệu mới bị hỏng hoàn toàn và chưa thể sửa ngay, tiến hành tải lại cơ sở dữ liệu từ snapshot lưu trữ trước đó.
3. **Bật banner cảnh báo**: Nếu dữ liệu bị chậm cập nhật quá 48 giờ (freshness SLA vi phạm nghiêm trọng), hiển thị thông báo "Dữ liệu chính sách đang được bảo trì" trên giao diện RAG Agent.

---

## Prevention

- **Thêm Guardrail & Expectation**: Luôn duy trì bộ quy tắc kiểm định nghiêm ngặt với thuộc tính `severity: halt` cho các lỗi nghiêm trọng về mặt nghiệp vụ (ví dụ: các điều khoản pháp lý hoặc tài chính).
- **Cấu hình Alert Slack**: Đồng bộ cảnh báo pipeline đến kênh Slack `#pipeline-alerts` để các kỹ sư trực incident nhận được alert ngay lập tức khi pipeline gặp sự cố.
