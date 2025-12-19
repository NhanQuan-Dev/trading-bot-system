Bạn là Business Analyst + Product Owner + Solution Architect.

BỐI CẢNH
- Tôi có mock UI đã code sẵn trong thư mục: ./frontend
- Mục tiêu: dựa vào chính UI hiện tại (component, page, routing, form field, label, placeholder, empty state, validation, button, modal, table, filter…) để suy ra Business Requirements và Use Cases.
- Output cuối cùng: tạo 1 file Markdown: docs/business-requirements.md
- Yêu cầu: CHI TIẾT NHẤT CÓ THỂ, rõ ràng, có cấu trúc, và “bám UI”.

NHIỆM VỤ
1) Quét toàn bộ ./frontend để lập “UI Inventory”
   - Liệt kê: pages/screens, components quan trọng, routing, menu/sidebar, modal/drawer, form, table/list, filter/search, state (loading/empty/error), permission/role (nếu có), copy/label.
   - Trích nguyên văn các text/label quan trọng (nút bấm, tiêu đề, field label, message).

2) Từ UI Inventory -> suy ra Business Requirements (BRD)
   - Viết theo dạng có thể dùng để implement backend + QA + stakeholder review.
   - Mỗi requirement phải có:
     - Requirement ID (BR-001…)
     - Mô tả
     - Lý do/giá trị
     - Màn hình liên quan (mapping tới page/component)
     - Rule/validation
     - Acceptance Criteria (Given/When/Then)

3) Sinh Use Cases (UC) theo từng module/screen
   - Mỗi use case phải có:
     - UC ID (UC-001…)
     - Actors (User/Admin/System/External service)
     - Preconditions
     - Trigger
     - Main flow (step-by-step)
     - Alternate flows / Exceptions (ví dụ validation fail, API fail, permission denied, network lost)
     - Postconditions
     - Data involved (fields + source)
     - UI mapping (màn hình + component + action)
     - Audit/log (nếu nên có)

4) Đặc biệt phải suy ra & ghi rõ các thứ thường bị thiếu trong mock UI
   - Authorization & roles matrix (ai thấy gì, làm gì)
   - Business rules ngầm định (required field, range, unique, status transition)
   - Data model sơ bộ (entities + attributes + relationships dựa trên UI)
   - API contract gợi ý (endpoint, method, request/response schema) *chỉ là gợi ý dựa vào UI*
   - Non-functional requirements (performance, logging, error handling, i18n, accessibility nếu có dấu hiệu)
   - Edge cases theo từng screen

5) Format file docs/business-requirements.md bắt buộc có các phần sau:
   A. Overview (problem, goals, non-goals)
   B. Glossary (thuật ngữ từ UI)
   C. Assumptions & Open Questions (cái nào không chắc thì ghi rõ)
   D. UI Inventory (table)
   E. Business Requirements (BR-xxx) (table + chi tiết)
   F. Use Cases (UC-xxx) (chi tiết theo template)
   G. Data Model Draft (entities/relationships)
   H. Suggested APIs (mapping theo usecase)
   I. Validation & Error States Catalog
   J. Status/State Machine (nếu UI có status)
   K. Metrics/Tracking events đề xuất (analytics)
   L. Appendix: Screenshots mapping (nếu có asset) / Source references (file paths)

RÀNG BUỘC
- Không tự bịa tính năng không có dấu vết trong UI. Nếu suy luận, phải gắn nhãn: [INFERRED] và giải thích vì sao suy luận.
- Với mỗi màn hình, phải có ít nhất 3-10 use case tùy độ phức tạp (bao gồm cả empty/error/permission).
- Nếu thấy có route nhưng chưa có UI hoàn chỉnh, vẫn phải tạo requirement ở mức placeholder và ghi Open Question.
- Cực kỳ quan trọng: mapping rõ file path trong frontend tới nội dung requirement/usecase.

OUTPUT
- Tạo mới file: docs/business-requirements.md
- Nội dung phải dài và chi tiết.
- Kèm cuối file: “Traceability Matrix” mapping:
  Route/Screen -> BR IDs -> UC IDs -> Suggested API endpoints

BẮT ĐẦU THỰC HIỆN NGAY:
- Trước tiên hãy liệt kê cây thư mục ./frontend, sau đó đọc lần lượt các file quan trọng (routing + pages + components).
- Sau khi phân tích xong, hãy viết file Markdown đúng format ở trên.

