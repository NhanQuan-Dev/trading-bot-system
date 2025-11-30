# Testing Rules

## 1. Mục tiêu
Test chính xác – dễ đọc – refactor an toàn.

## 2. Loại test
- Unit test
- Integration test
- E2E (nếu cần)

## 3. Naming
File: test_<module>.py  
Function: test_<behavior>_<expected>()

## 4. Structure AAA
Arrange – Act – Assert.

## 5. Mocking
Không gọi API/DB thật.

## 6. Coverage
Phải test: case thường, edge case, error case.
