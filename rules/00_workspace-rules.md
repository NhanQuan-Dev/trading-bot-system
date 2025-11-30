# Workspace Rules

Mục tiêu: Thiết lập bộ nguyên tắc để AI trong Cursor viết code có kỷ luật, nhất quán, không hardcode, dễ maintain và luôn tham chiếu đúng rule.

## 1. File rule tương ứng cho từng tác vụ
- Viết hoặc sửa code → 01_coding-rules.md
- Viết hoặc sửa test → 02_testing-rules.md
- Thiết kế kiến trúc, dựng codebase → 03_codebase-architecture-rules.md

## 2. Nguyên tắc chung
1. Không phá code đang chạy ổn định
2. Mọi thay đổi phải có: làm gì – tại sao – ảnh hưởng
3. Ưu tiên readability
4. Không thêm thư viện nặng khi không cần
5. Không log hoặc commit secrets
6. Code phải dynamic – không hardcode

## 3. No Hardcode – Code phải dynamic
Nghiêm cấm hardcode:
- API key, token, secret
- URL, endpoint
- risk%, leverage, threshold
- symbol, interval
- file path tuyệt đối
- DB host/port/schema

Tất cả phải đến từ:
- ENV, config file, config object, DI
