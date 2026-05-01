# 🔒 INPUT VALIDATION & SECURITY GUIDE

## Overview

Input validation ko'p muhim qism security'ning. Bu guide'da qanday qilib input data'ni properly validate qilish kerak, deb ko'rsatilgan.

---

## 🛡️ Validation Utilities

### Phone Number Validation

```python
from utils import validate_phone_number

# ✅ Valid formats
phone = validate_phone_number("+998901234567")  # +998
phone = validate_phone_number("901234567")      # without +998
phone = validate_phone_number("+9989-01-234-567")  # with separators

# ❌ Invalid
try:
    validate_phone_number("123")  # too short
except ValueError as e:
    print(e)  # ❌ Invalid phone format
```

### Truck Plate Validation

```python
from utils import validate_truck_plate

# ✅ Valid formats
plate = validate_truck_plate("60A123BC")  # Uzbekistan format
plate = validate_truck_plate("60А123BC")  # Cyrillic A

# ❌ Invalid
try:
    validate_truck_plate("invalid")
except ValueError as e:
    print(e)  # ❌ Invalid truck plate format
```

### Price Validation

```python
from utils import validate_price

# ✅ Valid
price = validate_price(50000.99)  # Decimal

# ❌ Invalid
try:
    validate_price(-100)  # negative
except ValueError as e:
    print(e)  # ❌ Price cannot be less than 0
```

### Text Validation (SQL Injection Prevention)

```python
from utils import validate_text_no_sql_injection

# ✅ Safe
text = validate_text_no_sql_injection("Hello world")

# ❌ SQL Injection attempt
try:
    validate_text_no_sql_injection("'; DROP TABLE users; --")
except ValueError as e:
    print(e)  # ❌ Invalid characters detected
```

---

## 📊 Pydantic Schemas

### Pagination

```python
from utils import PaginationParams

# GET /api/orders?skip=0&limit=20
params = PaginationParams(skip=0, limit=20)
```

### Coordinates

```python
from utils import CoordinatesSchema

coords = CoordinatesSchema(latitude=41.2995, longitude=69.2401)
```

### Address

```python
from utils import AddressSchema

address = AddressSchema(
    city="Tashkent",
    region="Tashkent",
    address="123 Main St",
    latitude=41.2995,
    longitude=69.2401
)
```

### Create Order

```python
from utils import CreateOrderSchema
from decimal import Decimal

order = CreateOrderSchema(
    cargo_name="Electronics",
    weight=Decimal("50.25"),
    price=Decimal("100000"),
    required_truck_type_id=1
)
```

---

## ⚡ Rate Limiting

Simple in-memory rate limiter built-in:

```python
from utils import limiter

# Check if user can make request
key = f"user:{user_id}"
if not limiter.is_allowed(key, max_requests=100, window_seconds=60):
    raise HTTPException(status_code=429, detail="Rate limit exceeded")
```

### Common Rate Limits

| Endpoint | Limit | Window |
|----------|-------|--------|
| Login | 5 | 60 sec |
| Register | 3 | 3600 sec |
| Password Reset | 3 | 3600 sec |
| General API | 100 | 60 sec |
| Create Order | 20 | 3600 sec |

---

## 🔐 SQL Injection Prevention

### ❌ DON'Ts

```python
# BAD: Direct user input in queries
query = f"SELECT * FROM users WHERE name='{user_input}'"

# BAD: String concatenation
query = "SELECT * FROM users WHERE id=" + str(user_id)
```

### ✅ DO's

```python
# GOOD: Use SQLAlchemy ORM
from sqlalchemy import select
from users.models import User

# SQLAlchemy automatically escapes values
stmt = select(User).where(User.name == user_input)
result = await db.execute(stmt)

# GOOD: Use parameterized queries
from sqlalchemy import text
stmt = text("SELECT * FROM users WHERE name = :name")
result = await db.execute(stmt, {"name": user_input})
```

---

## 🛡️ XSS Prevention

### Remove HTML Tags

```python
from utils.security import sanitize_html

# Input with script tag
dirty = "<p>Hello<script>alert('xss')</script></p>"
clean = sanitize_html(dirty)
# Result: "<p>Hello</p>"
```

---

## 📋 API Endpoint Validation Examples

### Example 1: Create Order

```python
from fastapi import APIRouter, Depends
from utils import CreateOrderSchema, PaginationParams, limiter
from utils.security import validate_text

router = APIRouter()

@router.post("/orders")
async def create_order(
    order_data: CreateOrderSchema,
    user_id: int = Depends(get_current_user_id)
):
    """
    ✅ Schema automatically validates:
    - cargo_name: 3-200 chars
    - weight: > 0
    - price: > 0
    - required_truck_type_id: positive integer
    """
    
    # Check rate limit
    key = f"user:{user_id}:create_order"
    if not limiter.is_allowed(key, max_requests=20, window_seconds=3600):
        raise HTTPException(status_code=429)
    
    # Create order
    order = await crud.create_order(db, order_data, user_id)
    return order
```

### Example 2: Search Orders

```python
@router.get("/orders/search")
async def search_orders(
    q: str = Query(..., min_length=2, max_length=100),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100)
):
    """
    ✅ Query parameters validated:
    - q: 2-100 chars (prevents SQL injection via validate_text)
    - skip: >= 0
    - limit: 1-100 (max 100)
    """
    
    # Sanitize search input
    safe_q = validate_text(q, min_len=2, max_len=100)
    
    results = await db.search_orders(safe_q, skip, limit)
    return results
```

---

## 🚨 Common Validation Issues

### Issue 1: Missing Required Fields

```python
# ❌ Request data missing required field
POST /api/orders
{
    "cargo_name": "Electronics"
    // Missing: weight, price, required_truck_type_id
}

# Response: 422 Unprocessable Entity
{
    "detail": [
        {
            "field": "weight",
            "message": "field required",
            "type": "value_error.missing"
        }
    ]
}
```

### Issue 2: Invalid Type

```python
# ❌ Wrong data type
POST /api/orders
{
    "weight": "not_a_number"  // should be number
}

# Response: 422
{
    "detail": [
        {
            "field": "weight",
            "message": "value is not a valid number",
            "type": "type_error.float"
        }
    ]
}
```

### Issue 3: Out of Range

```python
# ❌ Value out of acceptable range
POST /api/orders
{
    "weight": -50  // Negative weight
}

# Response: 422
{
    "detail": [
        {
            "field": "weight",
            "message": "ensure this value is greater than 0",
            "type": "value_error.number.not_gt"
        }
    ]
}
```

---

## 📝 Best Practices

### ✅ DO

1. **Always validate input** - Never trust user input
2. **Use strong types** - Decimal for money, int for counts
3. **Set min/max lengths** - Field(..., min_length=2, max_length=100)
4. **Use enums** - Literal["driver", "sender"] instead of str
5. **Check ranges** - Field(..., ge=0, le=100) for numeric values
6. **Rate limit** - Protect sensitive endpoints
7. **Sanitize** - Remove HTML/dangerous characters
8. **Log validation errors** - For debugging and security monitoring

### ❌ DON'T

1. **Don't skip validation** - Every input needs validation
2. **Don't use string concatenation for queries** - Use parameterized queries
3. **Don't store plain passwords** - Always hash with bcrypt/argon2
4. **Don't expose error details** - Don't show database/system internals
5. **Don't trust client libraries** - Only trust inputs received from users
6. **Don't hardcode limits** - Make rate limits configurable
7. **Don't mix validation logic** - Use Pydantic schemas consistently

---

## 🔄 Workflow

```
User Input
    ↓
[Pydantic Validation] - Type checking, length, ranges
    ↓
[SQL Injection Check] - Detect dangerous patterns
    ↓
[Rate Limiting] - Check if within limits
    ↓
[Database Query] - Safe parameterized query
    ↓
[Response]
```

---

## 📚 Resources

- [Pydantic Documentation](https://docs.pydantic.dev/)
- [OWASP SQL Injection](https://owasp.org/www-community/attacks/SQL_Injection)
- [OWASP XSS](https://owasp.org/www-community/attacks/xss/)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)

---

**Remember**: Security is not optional! 🔒

