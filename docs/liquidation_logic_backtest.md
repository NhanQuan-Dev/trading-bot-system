# Logic Thanh Lý (Liquidation)

Hệ thống sử dụng **Isolated Margin** với **Maintenance Margin cố định là 0.5% (MMR = 0.005)**. **[UPDATED]**

Liquidation được kích hoạt khi **unrealized loss tiêu hao toàn bộ Initial Margin, trừ lại phần Maintenance Margin**, nhằm đảm bảo tài khoản không bao giờ về 0. **[ADDED]**

Liquidation được tính theo **price-based model (simplified)**, phù hợp cho backtest. **[ADDED]**

---

## Công thức Liquidation Price

### Long position

\[
\text{Giá Thanh Lý}
= \text{Giá Vào} \times \left(1 - \frac{1}{\text{Leverage}} + 0.005\right)
\]

*(Không thay đổi)*

### Short position

\[
\text{Giá Thanh Lý}
= \text{Giá Vào} \times \left(1 + \frac{1}{\text{Leverage}} - 0.005\right)
\]

*(Không thay đổi)*

---

## Diễn giải

- Initial Margin = \( \frac{1}{\text{Leverage}} \)
- Maintenance Margin = **0.5%**
- Mức lỗ tối đa cho phép trước khi bị thanh lý là:

\[
\frac{1}{\text{Leverage}} - 0.5\%
\]
**[ADDED]**

Khi unrealized loss đạt đến mức này, hệ thống sẽ **đóng vị thế ngay lập tức** để giữ lại Maintenance Margin. **[UPDATED]**

---

## Ví dụ

Giả sử:
- Giá BTC = 50,000
- Leverage = 10x

Khi đó:
- Initial Margin = 10%
- Maintenance Margin = 0.5%
- Mức lỗ tối đa trước liquidation = **9.5%** **[ADDED]**

### Giá thanh lý (Long)

\[
50,000 \times (1 - 0.1 + 0.005) = 45,250
\]

*(Không thay đổi)*

Điều này có nghĩa là:
- Nếu giá giảm **9.5%** so với giá vào lệnh **[UPDATED]**
- Vị thế sẽ bị **thanh lý**
- Tài khoản **không bao giờ chạm 0**, mà vẫn giữ lại phần Maintenance Margin **[ADDED]**

---

## Quy tắc kích hoạt Liquidation trong Backtest

- Giá dùng để kiểm tra liquidation là **giá đóng nến (candle close)**, được xem như **mark price approximation** **[ADDED]**
- Liquidation xảy ra khi:

### Long
```
close_price <= liquidation_price
```

### Short
```
close_price >= liquidation_price
```

*(Điều kiện giữ nguyên)*

Khi liquidation xảy ra:
- Vị thế bị đóng ngay lập tức
- Không xét Take Profit / Stop Loss **[UPDATED]**
- Lý do đóng lệnh được ghi nhận là **LIQUIDATION**

---

## Lưu ý

Logic liquidation này là **mô hình đơn giản hóa**, không bao gồm: **[ADDED]**
- Maintenance Margin theo tier
- Funding fee
- Liquidation fee
- Insurance fund

Mô hình này được thiết kế để đảm bảo: **[ADDED]**
- Backtest ổn định
- Dễ giải thích
- Dễ debug
- Phù hợp cho đánh giá strategy
