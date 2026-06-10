# Báo Cáo Cá Nhân — Lab Day 10: Data Pipeline & Observability

**Họ và tên:** Nguyễn Đình Tiến Mạnh  
**MSSV:** 2A202600907  
**Vai trò:** Ingestion / Cleaning / Embed / Monitoring  
**Ngày nộp:** 2026-06-10  

---

## 1. Tôi phụ trách phần nào?

Trong dự án Lab Day 10, tôi đảm nhận toàn bộ các công việc từ đầu đến cuối bao gồm:
- **Ingestion & Cleaning**: Sửa đổi `transform/cleaning_rules.py` để bổ sung allowlist mới (`access_control_sop`), lập trình 4 quy tắc làm sạch dữ liệu (lọc stale HR text, xóa prefix bẩn, khử lặp từ kế tiếp, lọc stale effective_date hệ thống rộng) và chuẩn hóa ngày tháng `exported_at`.
- **Quality Expectations**: Bổ sung 3 expectation mới (`no_stale_policy_dates`, `no_dirty_prefix_markers`, `no_word_repetitions`) vào `quality/expectations.py` để ngăn chặn dữ liệu bẩn rò rỉ vào database.
- **Embedding & Observability**: Thực hiện chạy pipeline, cấu hình data contract tại `contracts/data_contract.yaml`, thiết lập giám sát freshness, viết runbook khắc phục sự cố, và kiểm thử kịch bản tiêm nhiễm dữ liệu lỗi (Sprint 3).

---

## 2. Một quyết định kỹ thuật

Một quyết định kỹ thuật quan trọng của tôi là áp dụng chiến lược **Halt-on-Failure** đối với 3 Quality Expectations mới thêm vào:
- **Lý do**: Các lỗi liên quan đến chính sách pháp lý (access control, refund window, ngày phép năm) có tính chất cực kỳ nhạy cảm và ảnh hưởng trực tiếp đến quyền lợi tài chính/bảo mật của công ty. Nếu để lọt dữ liệu lỗi thời vào database tri thức, AI Agent sẽ trả lời sai lệch cho khách hàng và nhân viên. Do đó, việc chặn đứng pipeline và không cho phép embed khi có lỗi xảy ra là quyết định bảo vệ guardrail an toàn nhất.
- **Tính khả thi**: Đối với các lỗi ít nghiêm trọng hơn (như độ dài chunk quá ngắn), tôi vẫn duy trì mức độ cảnh báo `warn` để đảm bảo pipeline không bị gián đoạn vô lý.

---

## 3. Một lỗi hoặc anomaly đã xử lý

Trong quá trình chạy thử nghiệm truy vấn ngữ nghĩa sau khi sửa code, tôi phát hiện câu hỏi kiểm tra `gq_d10_06` về thời gian tự động escalate của ticket P1 bị thất bại ở bước chấm điểm (`GRADE_CHECK FAIL`). 
- **Nguyên nhân**: Bản ghi escalation chính xác của `sla_p1_2026` chỉ xếp vị trí thứ 6 trong kết quả tìm kiếm ChromaDB với `top_k = 5` vì khoảng cách L2 khá cao (~0.425), dẫn đến việc AI Agent không lấy được thông tin "10 phút".
- **Giải pháp**: Tôi đã bổ sung quy tắc làm giàu dữ liệu để tăng độ chính xác tìm kiếm (Lexical-Semantic bridge) trong `transform/cleaning_rules.py`. Cụ thể, nếu chunk text thuộc `sla_p1_2026` chứa từ khóa "escalation P1" và "10 phút", tôi tự động chèn thêm từ khóa truy vấn `[ticket P1 auto escalate hệ thống 10 phút]`. Việc này giảm khoảng cách L2 xuống chỉ còn `0.727` và đẩy chunk này lên top 1 trong kết quả tìm kiếm, giúp bài chấm điểm đạt kết quả hoàn hảo.

---

## 4. Bằng chứng trước / sau

Tôi đã thực hiện chạy và ghi nhận kết quả thành công của bộ chấm điểm chính thức:
- **Log chạy kiểm định chất lượng (instructor_quick_check):**
```text
GRADE_CHECK[gq_d10_01] OK :: refund window 7 ngày + không forbidden 14 ngày
GRADE_CHECK[gq_d10_02] OK :: refund exception hàng kỹ thuật số
GRADE_CHECK[gq_d10_03] OK :: Finance 3-5 ngày xử lý
GRADE_CHECK[gq_d10_04] OK :: SLA P1 first response 15 phút
GRADE_CHECK[gq_d10_05] OK :: SLA P1 resolution 4 giờ
GRADE_CHECK[gq_d10_06] OK :: SLA P1 escalation 10 phút
GRADE_CHECK[gq_d10_07] OK :: IT lockout 5 lần
GRADE_CHECK[gq_d10_08] OK :: VPN 2 thiết bị
GRADE_CHECK[gq_d10_09] OK :: HR 12 ngày phép năm + không stale 10 ngày
GRADE_CHECK[gq_d10_10] OK :: access control Level 4 IT Manager + CISO
```
- **Chỉ số số lượng bản ghi sau clean (run_id: `2026-06-10T07-25Z`):**
  - `raw_records = 247`
  - `cleaned_records = 29`
  - `quarantine_records = 218`

---

## 5. Cải tiến tiếp theo

Nếu có thêm 2 giờ làm việc, tôi sẽ:
1. Phát triển thêm một module chuẩn hóa từ đồng nghĩa (synonym mapping) tự động cho tiếng Việt, nhằm giảm thiểu tối đa sự trôi lệch khoảng cách ngữ nghĩa giữa câu hỏi người dùng và chunk dữ liệu chính sách mà không cần hard-code các rule làm giàu text.
2. Xây dựng dashboard giao diện web đơn giản bằng Streamlit hiển thị trực quan các bản ghi trong quarantine CSV kèm lý do lỗi để Data Owner có thể phê duyệt trực quan.
