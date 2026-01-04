Prompt đã được điều chỉnh (bản chuẩn để dùng cho AI / FE dev)

Mục tiêu
Khi giá vừa update và lớn hơn giá trước đó, hiển thị hiệu ứng nổ (burst / ice-like explosion) ngay tại label giá hiện tại.

Điều kiện trigger

Chỉ trigger khi newPrice > previousPrice

Không trigger khi giá giảm hoặc không đổi

Nếu nhiều update liên tiếp → reset animation chứ không chồng hiệu ứng

Vị trí hiệu ứng

Tâm hiệu ứng nằm chính giữa label giá (price label / last price marker)

Không làm dịch layout hoặc ảnh hưởng crosshair

Mô tả hiệu ứng (visual concept)

Hiệu ứng giống tảng băng nổi vỡ ra:

Bắt đầu từ 1 khối lớn, sáng nhẹ

Nổ ra thành nhiều mảnh mềm (soft shards / blobs)

Các mảnh bung ra nhẹ, không giật, rồi tan dần

Cảm giác:

“mượt”

“nặng vừa phải”

không chói, không flash mạnh

Animation timing & easing

Tổng thời gian: 400–700ms

Giai đoạn:

Scale up nhẹ (1.0 → 1.15) trong ~80ms

Burst + outward motion với easing easeOutCubic

Fade + blur nhẹ + scale down rồi biến mất

Không dùng linear animation

Màu sắc & opacity

Màu chính: xanh nhạt / cyan / xanh băng (#7dd3fc, #38bdf8 hoặc tương đương)

Opacity ban đầu ~0.6–0.8 → về 0

Có thể thêm radial gradient để mềm hơn

Performance constraints

Không tạo object mới mỗi tick giá → dùng pool / reuse nếu có

Không ảnh hưởng FPS khi giá update liên tục

Không re-render toàn chart

Tech gợi ý (không bắt buộc)

Canvas overlay / absolutely positioned layer

Animation bằng requestAnimationFrame hoặc CSS transform + opacity

Tách animation logic khỏi price update logic

Kết quả mong muốn

Người dùng cảm nhận rõ ràng giá đang tăng

Hiệu ứng đẹp, mượt, tinh tế, không gây phân tâm

Hoạt động ổn định trong real-time chart

🧠 Ghi chú thêm (để bạn dùng khi cần refine)

Nếu muốn phân biệt mạnh/yếu:

delta nhỏ → nổ nhỏ

delta lớn → nổ to + nhiều mảnh hơn

Nếu chart zoom nhỏ → giảm scale hiệu ứng

Có thể bật/tắt bằng feature flag: priceIncreaseEffectEnabled