# Codebase & Architecture Rules

## 1. Layer
- domain
- application
- infrastructure
- interfaces

Domain không được import infrastructure.

## 2. Folder Structure
src/
  domain/
  application/
  infrastructure/
  interfaces/
tests/

## 3. Config (No Hardcode)
Không hardcode:
- URL
- API key/secret
- symbol/interval
- trading params
- db config

Phải dùng ENV/config loader.

## 4. Migration
Không sửa schema trực tiếp – phải dùng migration.

## 5. Dependency Direction
domain -> application -> infrastructure

## 6. Legacy
Không rewrite toàn bộ – refactor nhỏ, có TODO.
