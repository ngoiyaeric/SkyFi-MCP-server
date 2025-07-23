# Authentication

Authentication endpoints for user verification and account statistics.

## Get Current User (whoami)

Get the current authenticated user with details and statistics.

### Endpoint
```
GET /auth/whoami
```

### Headers
```
X-Skyfi-Api-Key: <API_KEY>
```

### Response
```json
{
  "id": "497f6eca-6276-4993-bfeb-53cbbbba6f08",
  "organizationId": "7bc05553-4b68-44e8-b7bc-37be63c6d9e9",
  "email": "user@example.com",
  "firstName": "string",
  "lastName": "string",
  "isDemoAccount": true,
  "currentBudgetUsage": 0,
  "budgetAmount": 0,
  "hasValidSharedCard": true
}
```

### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Unique user identifier |
| `organizationId` | UUID | Organization the user belongs to |
| `email` | string | User's email address |
| `firstName` | string | User's first name |
| `lastName` | string | User's last name |
| `isDemoAccount` | boolean | Whether this is a demo account |
| `currentBudgetUsage` | number | Current budget usage in dollars |
| `budgetAmount` | number | Total budget amount in dollars |
| `hasValidSharedCard` | boolean | Whether the organization has a valid payment method |

### Example (Python)
```python
import logging
import httpx

headers = {"X-Skyfi-Api-Key": "<API_KEY>"}
whoami_response = httpx.get(
    "https://app.skyfi.com/platform-api/auth/whoami", 
    headers=headers
)
whoami = whoami_response.json()

logging.info(f"User: {whoami['id']} - {whoami['email']}")
logging.info(f"Budget: ${whoami['currentBudgetUsage']} / ${whoami['budgetAmount']}")
```

### Example (JavaScript)
```javascript
const headers = { 'X-Skyfi-Api-Key': '<API_KEY>' };

fetch('https://app.skyfi.com/platform-api/auth/whoami', { headers })
  .then(response => response.json())
  .then(data => {
    console.log(`User: ${data.id} - ${data.email}`);
    console.log(`Budget: $${data.currentBudgetUsage} / $${data.budgetAmount}`);
  });
```

### Error Responses

#### 401 - Authentication Failed
Returned when:
- API key is missing
- API key is invalid
- API key has been revoked

```json
{
  "detail": "Authentication failed"
}
```

## Use Cases

### 1. Verify API Key
Use the whoami endpoint to verify your API key is valid and active:

```python
try:
    response = httpx.get(
        "https://app.skyfi.com/platform-api/auth/whoami",
        headers={"X-Skyfi-Api-Key": api_key}
    )
    response.raise_for_status()
    print("API key is valid")
except httpx.HTTPStatusError as e:
    if e.response.status_code == 401:
        print("Invalid API key")
```

### 2. Check Budget Status
Monitor your budget usage before placing orders:

```python
whoami = get_current_user()  # Your whoami implementation
remaining_budget = whoami['budgetAmount'] - whoami['currentBudgetUsage']

if remaining_budget < order_cost:
    print(f"Insufficient budget. Need ${order_cost}, have ${remaining_budget}")
```

### 3. Account Type Detection
Determine if using a demo account:

```python
whoami = get_current_user()
if whoami['isDemoAccount']:
    print("Using demo account - some features may be limited")
```

## Best Practices

1. **Cache User Info**: Don't call whoami before every request. Cache the response and refresh periodically.
2. **Handle 401 Errors**: Always handle authentication failures gracefully.
3. **Monitor Budget**: Check budget before placing large orders to avoid failures.
4. **Validate Payment Method**: Check `hasValidSharedCard` before attempting paid operations.