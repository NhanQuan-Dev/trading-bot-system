# API Documentation

**Version:** 1.0.0  
**Base URL:** `http://localhost:8000`  
**Last Updated:** December 15, 2025

---

## Authentication

All authenticated endpoints require a Bearer token in the Authorization header:

```
Authorization: Bearer <access_token>
```

### Token Format
- **Access Token:** JWT with 30-minute expiration
- **Refresh Token:** JWT with 7-day expiration

---

## Endpoints

### Health Check

#### GET /health
Check API health status.

**Response:**
```json
{
  "status": "healthy",
  "environment": "development",
  "version": "1.0.0"
}
```

---

## Authentication Endpoints

### Register User

#### POST /api/v1/auth/register
Create a new user account and return authentication tokens.

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "SecurePass123",
  "full_name": "John Doe",
  "timezone": "Asia/Ho_Chi_Minh"
}
```

**Validation:**
- `email`: Valid email format (required)
- `password`: 8-100 characters (required)
- `full_name`: Max 255 characters (optional)
- `timezone`: Valid timezone string (optional, default: "UTC")

**Response (201 Created):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer"
}
```

**Error Responses:**
- `400 Bad Request`: Email already registered
- `422 Unprocessable Entity`: Validation errors

---

### Login

#### POST /api/v1/auth/login
Authenticate user and return tokens.

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "SecurePass123"
}
```

**Response (200 OK):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer"
}
```

**Error Responses:**
- `401 Unauthorized`: Invalid email or password
- `403 Forbidden`: User account is inactive

---

### Refresh Token

#### POST /api/v1/auth/refresh
Get new access token using refresh token.

**Request Body:**
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response (200 OK):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer"
}
```

**Error Responses:**
- `401 Unauthorized`: Invalid or expired refresh token
- `403 Forbidden`: User account is inactive

---

## User Endpoints

### Get Current User

#### GET /api/v1/users/me
Get current authenticated user's profile.

**Authentication:** Required

**Response (200 OK):**
```json
{
  "id": "b161e838-d26f-4399-b61d-9f8a65c8a6f7",
  "email": "user@example.com",
  "full_name": "John Doe",
  "timezone": "Asia/Ho_Chi_Minh",
  "is_active": true,
  "created_at": "2025-12-15T15:31:57.815381Z",
  "last_login_at": "2025-12-15T15:32:42.860021Z"
}
```

**Error Responses:**
- `401 Unauthorized`: Invalid or missing token
- `403 Forbidden`: User account is inactive

---

### Update Profile

#### PATCH /api/v1/users/me
Update current user's profile information.

**Authentication:** Required

**Request Body:**
```json
{
  "full_name": "John Smith",
  "timezone": "America/New_York"
}
```

**Note:** All fields are optional. Only provided fields will be updated.

**Response (200 OK):**
```json
{
  "id": "b161e838-d26f-4399-b61d-9f8a65c8a6f7",
  "email": "user@example.com",
  "full_name": "John Smith",
  "timezone": "America/New_York",
  "is_active": true,
  "created_at": "2025-12-15T15:31:57.815381Z",
  "last_login_at": "2025-12-15T15:32:42.860021Z"
}
```

---

### Update Preferences

#### PUT /api/v1/users/me/preferences
Update user preferences (application settings).

**Authentication:** Required

**Request Body:**
```json
{
  "preferences": {
    "theme": "dark",
    "language": "en",
    "notifications": {
      "email": true,
      "push": false
    },
    "trading": {
      "default_leverage": 10,
      "default_margin_mode": "ISOLATED"
    }
  }
}
```

**Response (200 OK):**
```json
{
  "id": "b161e838-d26f-4399-b61d-9f8a65c8a6f7",
  "email": "user@example.com",
  "full_name": "John Smith",
  "timezone": "America/New_York",
  "is_active": true,
  "created_at": "2025-12-15T15:31:57.815381Z",
  "last_login_at": "2025-12-15T15:32:42.860021Z"
}
```

---

## Error Response Format

All error responses follow this format:

```json
{
  "detail": "Error message or validation errors",
  "request_id": "uuid-v4-request-id"
}
```

### Validation Errors (422)
```json
{
  "detail": [
    {
      "type": "string_too_short",
      "loc": ["body", "password"],
      "msg": "String should have at least 8 characters",
      "input": "short"
    }
  ],
  "body": {...},
  "request_id": "uuid-v4-request-id"
}
```

---

## Testing Examples

### Register and Login Flow

```bash
# 1. Register
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "demo@trading.com",
    "password": "SecurePass123",
    "full_name": "Demo User"
  }'

# Response: Save access_token and refresh_token

# 2. Get user profile
curl http://localhost:8000/api/v1/users/me \
  -H "Authorization: Bearer <access_token>"

# 3. Update profile
curl -X PATCH http://localhost:8000/api/v1/users/me \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "Updated Name",
    "timezone": "Asia/Tokyo"
  }'

# 4. Refresh token when expired
curl -X POST http://localhost:8000/api/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "<refresh_token>"
  }'
```

---

## Rate Limiting

- **Default:** 60 requests per minute per user
- **Headers:**
  - `X-RateLimit-Limit`: Request limit
  - `X-RateLimit-Remaining`: Remaining requests
  - `X-RateLimit-Reset`: Reset timestamp

---

## Interactive API Documentation

FastAPI provides interactive API documentation:

- **Swagger UI:** http://localhost:8000/api/docs
- **ReDoc:** http://localhost:8000/api/redoc
- **OpenAPI JSON:** http://localhost:8000/api/openapi.json

---

## Coming Soon

### Exchange Integration (Phase 2)
- `POST /api/v1/exchanges/connections` - Connect exchange API
- `GET /api/v1/exchanges/connections` - List connections
- `GET /api/v1/exchanges/{exchange_id}/account` - Get account info

### Bot Management
- `POST /api/v1/bots` - Create trading bot
- `GET /api/v1/bots` - List user's bots
- `POST /api/v1/bots/{bot_id}/start` - Start bot
- `POST /api/v1/bots/{bot_id}/stop` - Stop bot

### Orders & Positions
- `POST /api/v1/orders` - Place order
- `GET /api/v1/orders` - List orders
- `GET /api/v1/positions` - List positions
- `DELETE /api/v1/orders/{order_id}` - Cancel order
