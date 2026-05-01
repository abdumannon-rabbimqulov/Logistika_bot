# 🔴 Error Handling & Logging System

## Global Exception Handler

Hamma exceptions (errors) bir joydan boshqariladi. Bu quyidagi turlardagi xatolarni hal qiladi:

### Olam langan Exception Turlari

1. **Database Errors** (SQLAlchemy)
   - `IntegrityError` - Duplicate entry, foreign key violation
   - `SQLAlchemyError` - Connection, syntax errors
   
2. **Validation Errors** (Pydantic)
   - Invalid request data format
   - Missing required fields
   
3. **Authentication Errors** (JWT)
   - Invalid token
   - Expired token
   
4. **Other Errors**
   - 500 Internal Server Error

### Error Response Format

Barcha error responses quyidagi format'da qaytariladi:

```json
{
  "status": "error",
  "status_code": 400,
  "message": "❌ Invalid request data",
  "error_code": "VALIDATION_ERROR",
  "details": {
    "errors": [
      {
        "field": "email",
        "message": "invalid email format",
        "type": "value_error.email"
      }
    ]
  },
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2025-05-01T10:30:45.123456+00:00"
}
```

## Request Logging

Har bitta HTTP request/response avtomatik log qilinadi:

```
📥 POST /api/auth/login          -> Yangi request
📤 POST /api/auth/login - 200    -> Successful response
❌ GET /api/user - 401           -> Error response
```

### Log Fields

- `request_id` - Unique request identifier (use for debugging)
- `method` - HTTP method (GET, POST, etc.)
- `path` - Request path
- `status_code` - Response status code
- `timestamp` - When the request was processed

### Example Request ID

```
X-Request-ID: 550e8400-e29b-41d4-a716-446655440000
```

## Health Check Endpoints

### Service Status
```bash
GET /health
```

Response:
```json
{
  "status": "ok",
  "service": "Logistika AI API",
  "environment": "production",
  "timestamp": "2025-05-01T10:30:45.123456+00:00"
}
```

### Database Status
```bash
GET /health/db
```

Response (OK):
```json
{
  "status": "ok",
  "database": "connected"
}
```

Response (Error):
```json
{
  "status": "error",
  "database": "disconnected",
  "error": "Connection refused"
}
```

## Common HTTP Status Codes

| Code | Meaning | Example |
|------|---------|---------|
| 200 | OK | Successful request |
| 201 | Created | New resource created |
| 204 | No Content | Successfully deleted |
| 400 | Bad Request | Invalid input data |
| 401 | Unauthorized | Missing/invalid token |
| 403 | Forbidden | No permission |
| 404 | Not Found | Resource doesn't exist |
| 409 | Conflict | Duplicate entry, foreign key error |
| 422 | Validation Error | Invalid data format |
| 500 | Internal Error | Server error |

## Debugging with Request ID

Every request gets a unique `request_id`:

1. **From Response Header:**
   ```bash
   curl -i https://api.example.com/users
   # Look for: X-Request-ID: abc123...
   ```

2. **From Error Response:**
   ```json
   {
     "request_id": "abc-123-def",
     "status": "error"
   }
   ```

3. **Search Logs:**
   ```bash
   grep "abc-123-def" logs/app.log
   ```

## Environment Variables for Logging

```bash
# Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
LOG_LEVEL=INFO

# Environment mode (development, production)
ENVIRONMENT=production
```

### Log Output

- **Development Mode**: Console output with colors and readable format
- **Production Mode**: JSON format to file (`logs/app.log`)

## Error Handling Examples

### Example 1: Validation Error

**Request:**
```bash
curl -X POST https://api.example.com/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "invalid"}'
```

**Response (422):**
```json
{
  "status": "error",
  "status_code": 422,
  "message": "❌ Invalid request data",
  "error_code": "VALIDATION_ERROR",
  "details": {
    "errors": [
      {
        "field": "email",
        "message": "invalid email format",
        "type": "value_error.email"
      }
    ]
  },
  "request_id": "req-123-abc",
  "timestamp": "2025-05-01T10:30:45.123456+00:00"
}
```

### Example 2: Database Error

**Response (409 Conflict):**
```json
{
  "status": "error",
  "status_code": 409,
  "message": "❌ Database conflict - duplicate entry or invalid reference",
  "error_code": "CONFLICT",
  "request_id": "req-123-def",
  "timestamp": "2025-05-01T10:30:45.123456+00:00"
}
```

### Example 3: Authentication Error

**Response (401 Unauthorized):**
```json
{
  "status": "error",
  "status_code": 401,
  "message": "❌ Invalid or expired authentication token",
  "error_code": "AUTHENTICATION_ERROR",
  "request_id": "req-123-ghi",
  "timestamp": "2025-05-01T10:30:45.123456+00:00"
}
```

## Logging Best Practices

### ✅ DO's

```python
import logging

logger = logging.getLogger(__name__)

# Good: Use appropriate log level
logger.info("User login successful", extra={"user_id": 123})
logger.warning("High memory usage detected")
logger.error("Database connection failed", exc_info=exc)

# Good: Add context
logger.info("Order created", extra={"order_id": 456, "user_id": 123})
```

### ❌ DON'Ts

```python
# Bad: Logging sensitive data
logger.info(f"Password: {password}")
logger.info(f"API Key: {api_key}")

# Bad: Using print instead of logging
print("User logged in")  # ❌ Use logger.info instead

# Bad: Logging too verbose
logger.debug("Entering function X")
logger.debug("In loop iteration 5")
```

## Monitoring & Alerts

### Check for Errors

```bash
# Count errors in last 1 hour
grep "ERROR" logs/app.log | wc -l

# Find errors from specific user
grep "user_id.*123" logs/app.log | grep ERROR

# Monitor real-time
tail -f logs/app.log | grep ERROR
```

### Performance Issues

```bash
# Find slow requests (> 1s)
grep "📤" logs/app.log | awk '{print $NF}' | sort -n | tail -10
```

---

**Remember**: Always check the `request_id` when debugging issues! 🔍

