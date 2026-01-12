# 

## 1. Multi-timeframe core: 1m làm nguồn dữ liệu, HTF làm signal

**Mục tiêu**: Backtest chạy strategy theo HTF (1h/4h…) nhưng mô phỏng đường đi giá bằng 1m để tăng độ chính xác.

**Yêu cầu**

- Hệ thống chỉ lấy **dữ liệu gốc timeframe 1m** (atomic data).
- Từ 1m, hệ thống phải **aggregate** ra HTF (1h/4h…) để tính indicator và chạy logic strategy.
- Strategy **chỉ được evaluate tại thời điểm HTF candle đóng** (HTF close). Không được evaluate khi HTF candle đang hình thành.
- Sau khi có signal tại HTF close, engine phải replay các candle 1m thuộc “cửa sổ thời gian tiếp theo” để thực thi entry/exit.

**Kết quả cần đạt**

- Không xảy ra look-ahead bias.
- HTF và LTF luôn đồng bộ vì cùng sinh từ 1m.

## 2. Setup–Trigger model: đợi nến đóng để xác nhận setup, dùng 1m để trigger entry

**Mục tiêu**: Cho phép chiến lược tách rõ “đủ điều kiện tìm entry” và “điểm entry hợp lệ”.

**Yêu cầu**

- Khi HTF candle đóng và thỏa điều kiện strategy → tạo trạng thái `SETUP_CONFIRMED`.
- Sau khi setup confirmed, engine chuyển sang `WAITING_FOR_TRIGGER` và chỉ quan sát 1m để tìm trigger entry.
- Trigger có thể là:
    - chạm mức giá (limit touch)
    - break micro-structure
    - reclaim/failed breakdown
    - pattern LTF (ví dụ engulfing) nhưng phải dựa trên **nến 1m đã đóng**, không dùng close của nến 1m đang chạy như dữ liệu hoàn chỉnh.
- Nếu hết “setup validity window” (ví dụ 1 HTF candle hoặc cấu hình N phút) mà không có trigger → hủy setup (`SETUP_EXPIRED`).

**Kết quả cần đạt**

- Entry time/price được xác định ở LTF, nhưng chỉ sau khi setup HTF được xác nhận.

## 3. Execution & Fill engine (Limit/TP/SL) với policy chống fill ảo

**Mục tiêu**: Mô phỏng fill limit và xử lý TP/SL sát thực tế trong giới hạn dữ liệu 1m.

**Yêu cầu**

- Engine phải hỗ trợ **FillPolicy** có cấu hình (ít nhất 3 mode):
    - `optimistic`: chạm giá là fill
    - `neutral`: yêu cầu cross hợp lý + có thể lọc wick
    - `strict`: cross + wick-filter + spread (và tùy chọn volume filter)
- Rule tối thiểu cho limit fill (để xử lý “trượt qua”):
    - Buy Limit fill khi: `1m.open >= limit_price AND 1m.low <= limit_price`
    - Sell Limit fill khi: `1m.open <= limit_price AND 1m.high >= limit_price`
    - Nếu open đã “nằm qua” giá limit theo hướng bất lợi (gap) → không fill.
- Xử lý TP/SL:
    - TP/SL chỉ được check **sau khi entry đã fill**.
    - Nếu trong cùng 1 candle 1m chạm cả TP và SL → phải xử lý theo **price path assumption** (configurable, default neutral).
- Multi-order (grid/DCA):
    - Có thứ tự fill rõ ràng (Buy: giá cao→thấp, Sell: giá thấp→cao).
    - Mỗi fill phải kiểm tra margin/position constraints (không fill vượt vốn).

**Kết quả cần đạt**

- Giảm fill ảo do wick/gap.
- Kết quả backtest “khắt khe” hơn và đáng tin khi lên live.

## 4. Event-driven logging & auditability (bắt buộc để debug và so sánh)

**Mục tiêu**: Mọi quyết định trong backtest phải giải thích được (debug được).

**Yêu cầu**

- Engine phải phát sinh log/event theo chuẩn tối thiểu:
    - `HTF_CANDLE_CLOSED`
    - `SETUP_CONFIRMED` / `SETUP_EXPIRED`
    - `ORDER_CREATED` / `ORDER_CANCELED`
    - `TRIGGER_HIT`
    - `ORDER_FILLED` (kèm policy + lý do fill/reject)
    - `TP_HIT` / `SL_HIT`
    - `POSITION_OPENED` / `POSITION_CLOSED`
- Mỗi trade record phải lưu:
    - `signal_time` (HTF close)
    - `entry_time` (LTF)
    - `entry_price`, `exit_time`, `exit_price`
    - `exit_reason` (TP/SL/Manual/Expired)
    - `max_drawdown`, `runup`
    - `execution_delay = entry_time - signal_time`
    - `fill_policy` + các điều kiện đã thỏa/miss
- Có khả năng replay/debug theo trade_id để tái hiện lại quyết định fill.

**Kết quả cần đạt**

- QA/Dev có thể kiểm chứng từng trade.
- Dễ so sánh kết quả giữa optimistic/neutral/strict.