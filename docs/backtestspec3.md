## Ví dụ minh họa cho Mục 1: Multi-timeframe core (1m source – HTF signal)

### Bối cảnh

- Timeframe strategy (HTF): **1h**
- Timeframe execution (LTF): **1m**
- Strategy condition (ví dụ):
    - Khi **nến 1h đóng**
    - RSI(1h) < 30
    - → sinh signal BUY

### Bước 1: Aggregate 1m → 1h (HTF)

Từ các nến 1m trong khoảng **09:00–09:59**, hệ thống tự tạo nến 1h:

- Open = open của 09:00
- High = max(high) từ 09:00–09:59
- Low = min(low) từ 09:00–09:59
- Close = close của 09:59

📌 **Lưu ý quan trọng**:

Hệ thống **không dùng trực tiếp nến 1h từ Binance**, mà luôn sinh HTF từ 1m để đảm bảo đồng bộ.

### Bước 2: Thời điểm strategy được phép chạy

- Trong khoảng **09:00–09:59**:
    - Nến 1h **đang hình thành**
    - Strategy **KHÔNG được evaluate**
    - Dữ liệu 1m trong giai đoạn này **chỉ dùng để xây nến 1h**
- Tại thời điểm **09:59:59 → 10:00:00**:
    - Nến 1h **09:00–09:59 đóng**
    - Strategy được evaluate **DUY NHẤT tại thời điểm này**

Ví dụ:

- RSI(1h) = 28 → thỏa điều kiện

➡️ **Signal BUY được sinh tại 10:00**

### Bước 3: Sau khi có signal – replay 1m để execution

- Sau khi signal được sinh tại **10:00**
- Engine bắt đầu replay các nến **1m từ 10:00 → 10:59** để:
    - kiểm tra entry
    - fill limit order
    - xử lý TP / SL

📌 **Quan trọng**:

- Các nến 1m **trước 10:00**:
    - KHÔNG được dùng cho entry
    - KHÔNG được dùng cho trigger
- Các nến 1m **sau 10:00**:
    - Chỉ dùng cho execution
    - KHÔNG ảnh hưởng ngược lại signal 1h đã sinh

### Điều KHÔNG được phép (để tránh hiểu sai)

- Không được:
    - Dùng nến 1m trong 09:00–09:59 để vào lệnh
    - Dùng close của nến 1m đang chạy để thay thế close 1h
    - Evaluate strategy nhiều lần trong cùng 1 nến 1h

---

### Kết luận từ ví dụ

- Nến 1m là **nguồn dữ liệu gốc duy nhất**
- Nến 1h chỉ là **kết quả aggregate**
- Strategy:
    - chỉ chạy khi **nến 1h đã đóng**
- Execution:
    - chỉ xảy ra trên **nến 1m sau thời điểm signal**