# Coding Rules

## 1. Naming
- Function: verb_object
- Variable: descriptive english
- Class: CamelCase
- Tránh tên mơ hồ: a, tmp, x1

## 2. Structure
- 1 function = 1 nhiệm vụ
- < 50 dòng
- Type hints
- Docstring

## 3. Error Handling
Không dùng `except Exception: pass`.
Phải catch đúng lỗi, log context, không log secrets.

## 4. Logging
Không log key/secret.

## 5. No Hardcode
Không hardcode:
- URL
- API key, secret
- symbol/interval
- TP/SL/risk/fee
- file path tuyệt đối

Phải dùng config/ENV.

## 6. Refactor Rule
- Không đổi behavior trừ khi yêu cầu
