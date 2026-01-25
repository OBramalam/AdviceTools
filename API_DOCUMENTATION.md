# Financial Planning API Documentation

## Table of Contents
1. [Overview](#overview)
2. [Base URL](#base-url)
3. [Authentication](#authentication)
4. [API Endpoints](#api-endpoints)
   - [Authentication](#authentication-endpoints)
   - [Financial Plans](#financial-plans-endpoints)
   - [Cash Flows](#cash-flows-endpoints)
   - [Chat](#chat-endpoints)
   - [File Upload](#file-upload-endpoint)
   - [Simulation](#simulation-endpoint)
5. [Data Models](#data-models)
6. [Error Handling](#error-handling)
7. [Example Workflows](#example-workflows)

---

## Overview

This API provides endpoints for financial planning, retirement simulations, and chat-based data collection. The API uses JWT-based authentication with access and refresh tokens.

**Key Features:**
- User authentication and authorization
- Financial plan management (CRUD operations)
- Cash flow management (CRUD operations)
- AI-powered chat for data collection
- File upload and parsing
- Financial simulations

---

## Base URL

```
Development: http://localhost:5000
Production: [TBD]
```

All API endpoints are prefixed with `/api`.

**Example:** `http://localhost:5000/api/auth/login`

---

## Authentication

The API uses JWT (JSON Web Tokens) with a two-token system:
- **Access Token**: Short-lived (30 minutes default), used for API requests
- **Refresh Token**: Long-lived (7 days default), used to get new access tokens

### Authentication Flow

1. **Register/Login** → Receive `access_token` and `refresh_token`
2. **Store tokens** → Save both tokens securely (e.g., in localStorage or httpOnly cookies)
3. **Include access token** → Add to `Authorization` header for protected endpoints:
   ```
   Authorization: Bearer <access_token>
   ```
4. **Refresh when expired** → When access token expires (401), use refresh token to get a new access token
5. **Logout** → Revoke refresh token

### Token Storage Recommendations

- **Access Token**: Store in memory or localStorage (short-lived, less sensitive)
- **Refresh Token**: Store in httpOnly cookie or secure storage (long-lived, more sensitive)

---

## API Endpoints

### Authentication Endpoints

#### Register

Create a new user account.

**Endpoint:** `POST /api/auth/register`

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "SecurePass123!",
  "name": "John Doe"
}
```

**Password Requirements:**
- Minimum 8 characters
- At least one uppercase letter
- At least one lowercase letter
- At least one number

**Response:** `201 Created`
```json
{
  "user": {
    "id": 1,
    "email": "user@example.com",
    "name": "John Doe",
    "is_active": true,
    "is_verified": false,
    "created_at": "2024-01-01T00:00:00"
  },
  "tokens": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer"
  }
}
```

**Error Responses:**
- `400 Bad Request`: Email already registered or invalid password
- `500 Internal Server Error`: Server error

---

#### Login

Authenticate and receive tokens.

**Endpoint:** `POST /api/auth/login`

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "SecurePass123!"
}
```

**Response:** `200 OK`
```json
{
  "user": {
    "id": 1,
    "email": "user@example.com",
    "name": "John Doe",
    "is_active": true,
    "is_verified": false,
    "created_at": "2024-01-01T00:00:00"
  },
  "tokens": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer"
  }
}
```

**Error Responses:**
- `401 Unauthorized`: Incorrect email or password
- `403 Forbidden`: User account is inactive

---

#### Refresh Token

Get a new access token using a refresh token.

**Endpoint:** `POST /api/auth/refresh`

**Request Body:**
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response:** `200 OK`
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Error Responses:**
- `401 Unauthorized`: Invalid or expired refresh token

---

#### Logout

Revoke a refresh token (logout).

**Endpoint:** `POST /api/auth/logout`

**Headers:**
```
Authorization: Bearer <access_token>
```

**Request Body:**
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response:** `200 OK`
```json
{
  "message": "Logged out successfully"
}
```

---

#### Get Current User

Get information about the currently authenticated user.

**Endpoint:** `GET /api/auth/me`

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response:** `200 OK`
```json
{
  "id": 1,
  "email": "user@example.com",
  "name": "John Doe",
  "is_active": true,
  "is_verified": false,
  "created_at": "2024-01-01T00:00:00"
}
```

---

### Financial Plans Endpoints

All financial plan endpoints require authentication.

#### List Financial Plans

Get all financial plans for the current user.

**Endpoint:** `GET /api/financial-plans`

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response:** `200 OK`
```json
[
  {
    "id": 1,
    "user_id": 1,
    "name": "Retirement Plan 2024",
    "description": "My retirement planning",
    "start_age": 35,
    "retirement_age": 65,
    "plan_end_age": 100,
    "plan_start_date": "2024-01-01T00:00:00",
    "current_portfolio_value": 50000.0,
    "portfolio_target_value": 1000000.0
  }
]
```

---

#### Get Financial Plan

Get a specific financial plan by ID.

**Endpoint:** `GET /api/financial-plans/{plan_id}`

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response:** `200 OK`
```json
{
  "id": 1,
  "user_id": 1,
  "name": "Retirement Plan 2024",
  "description": "My retirement planning",
  "start_age": 35,
  "retirement_age": 65,
  "plan_end_age": 100,
  "plan_start_date": "2024-01-01T00:00:00",
  "current_portfolio_value": 50000.0,
  "portfolio_target_value": 1000000.0
}
```

**Error Responses:**
- `404 Not Found`: Financial plan not found or doesn't belong to user

---

#### Create Financial Plan

Create a new financial plan.

**Endpoint:** `POST /api/financial-plans`

**Headers:**
```
Authorization: Bearer <access_token>
```

**Request Body:**
```json
{
  "name": "Retirement Plan 2024",
  "description": "My retirement planning",
  "start_age": 35,
  "retirement_age": 65,
  "plan_end_age": 100,
  "plan_start_date": "2024-01-01T00:00:00",
  "current_portfolio_value": 50000.0,
  "portfolio_target_value": 1000000.0
}
```

**Note:** `user_id` is automatically set from the authenticated user. `id` is auto-generated.

**Response:** `201 Created`
```json
{
  "id": 1,
  "user_id": 1,
  "name": "Retirement Plan 2024",
  "description": "My retirement planning",
  "start_age": 35,
  "retirement_age": 65,
  "plan_end_age": 100,
  "plan_start_date": "2024-01-01T00:00:00",
  "current_portfolio_value": 50000.0,
  "portfolio_target_value": 1000000.0
}
```

---

#### Update Financial Plan

Update an existing financial plan.

**Endpoint:** `PUT /api/financial-plans/{plan_id}`

**Headers:**
```
Authorization: Bearer <access_token>
```

**Request Body:**
```json
{
  "name": "Updated Retirement Plan",
  "description": "Updated description",
  "start_age": 35,
  "retirement_age": 65,
  "plan_end_age": 100,
  "plan_start_date": "2024-01-01T00:00:00",
  "current_portfolio_value": 60000.0,
  "portfolio_target_value": 1200000.0
}
```

**Note:** `id` and `user_id` cannot be changed.

**Response:** `200 OK`
```json
{
  "id": 1,
  "user_id": 1,
  "name": "Updated Retirement Plan",
  "description": "Updated description",
  "start_age": 35,
  "retirement_age": 65,
  "plan_end_age": 100,
  "plan_start_date": "2024-01-01T00:00:00",
  "current_portfolio_value": 60000.0,
  "portfolio_target_value": 1200000.0
}
```

**Error Responses:**
- `404 Not Found`: Financial plan not found or doesn't belong to user

---

#### Delete Financial Plan

Delete a financial plan.

**Endpoint:** `DELETE /api/financial-plans/{plan_id}`

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response:** `204 No Content`

**Error Responses:**
- `404 Not Found`: Financial plan not found or doesn't belong to user

---

### Cash Flows Endpoints

All cash flow endpoints require authentication.

#### List Cash Flows for a Plan

Get all cash flows for a specific financial plan.

**Endpoint:** `GET /api/cashflows/plan/{plan_id}`

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response:** `200 OK`
```json
[
  {
    "id": 1,
    "plan_id": 1,
    "name": "Salary",
    "description": "Monthly salary",
    "amount": 5000.0,
    "start_date": "2024-01-01T00:00:00",
    "end_date": "2054-01-01T00:00:00"
  },
  {
    "id": 2,
    "plan_id": 1,
    "name": "Mortgage",
    "description": "Monthly mortgage payment",
    "amount": -2000.0,
    "start_date": "2024-01-01T00:00:00",
    "end_date": "2034-01-01T00:00:00"
  }
]
```

**Note:** Negative amounts represent expenses, positive amounts represent income.

**Error Responses:**
- `404 Not Found`: Financial plan not found or doesn't belong to user

---

#### Get Cash Flow

Get a specific cash flow by ID.

**Endpoint:** `GET /api/cashflows/{cashflow_id}`

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response:** `200 OK`
```json
{
  "id": 1,
  "plan_id": 1,
  "name": "Salary",
  "description": "Monthly salary",
  "amount": 5000.0,
  "start_date": "2024-01-01T00:00:00",
  "end_date": "2054-01-01T00:00:00"
}
```

**Error Responses:**
- `404 Not Found`: Cash flow not found or doesn't belong to user's plan

---

#### Create Cash Flow

Create a new cash flow for a financial plan.

**Endpoint:** `POST /api/cashflows/plan/{plan_id}`

**Headers:**
```
Authorization: Bearer <access_token>
```

**Request Body:**
```json
{
  "name": "Rental Income",
  "description": "Monthly rental income",
  "amount": 1500.0,
  "start_date": "2024-01-01T00:00:00",
  "end_date": "2054-01-01T00:00:00"
}
```

**Note:** `plan_id` is set from the URL path. `id` is auto-generated.

**Response:** `201 Created`
```json
{
  "id": 3,
  "plan_id": 1,
  "name": "Rental Income",
  "description": "Monthly rental income",
  "amount": 1500.0,
  "start_date": "2024-01-01T00:00:00",
  "end_date": "2054-01-01T00:00:00"
}
```

**Error Responses:**
- `404 Not Found`: Financial plan not found or doesn't belong to user

---

#### Update Cash Flow

Update an existing cash flow.

**Endpoint:** `PUT /api/cashflows/{cashflow_id}`

**Headers:**
```
Authorization: Bearer <access_token>
```

**Request Body:**
```json
{
  "name": "Updated Rental Income",
  "description": "Updated description",
  "amount": 2000.0,
  "start_date": "2024-01-01T00:00:00",
  "end_date": "2054-01-01T00:00:00"
}
```

**Note:** `id` and `plan_id` cannot be changed.

**Response:** `200 OK`
```json
{
  "id": 3,
  "plan_id": 1,
  "name": "Updated Rental Income",
  "description": "Updated description",
  "amount": 2000.0,
  "start_date": "2024-01-01T00:00:00",
  "end_date": "2054-01-01T00:00:00"
}
```

**Error Responses:**
- `404 Not Found`: Cash flow not found or doesn't belong to user's plan

---

#### Delete Cash Flow

Delete a cash flow.

**Endpoint:** `DELETE /api/cashflows/{cashflow_id}`

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response:** `204 No Content`

**Error Responses:**
- `404 Not Found`: Cash flow not found or doesn't belong to user's plan

---

### Chat Endpoints

All chat endpoints require authentication.

#### Send Chat Message

Send a message to the AI assistant and receive a streaming response.

**Endpoint:** `POST /api/chat/message`

**Headers:**
```
Authorization: Bearer <access_token>
Content-Type: application/json
```

**Request Body:**
```json
{
  "message": "Hi, I'd like to start planning for my retirement. I'm 35 years old."
}
```

**Response:** `200 OK` (Server-Sent Events stream)

The response is a Server-Sent Events (SSE) stream. Each chunk is formatted as:
```
data: <chunk of text>\n\n
```

When complete, the stream sends:
```
data: [DONE]\n\n
```

If an error occurs:
```
data: [ERROR] <error message>\n\n
```

**Frontend Implementation Example (JavaScript):**
```javascript
const response = await fetch('http://localhost:5000/api/chat/message', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${accessToken}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({ message: userMessage })
});

const reader = response.body.getReader();
const decoder = new TextDecoder();

while (true) {
  const { done, value } = await reader.read();
  if (done) break;
  
  const chunk = decoder.decode(value);
  const lines = chunk.split('\n');
  
  for (const line of lines) {
    if (line.startsWith('data: ')) {
      const data = line.slice(6);
      if (data === '[DONE]') {
        // Stream complete
        break;
      } else if (data.startsWith('[ERROR]')) {
        // Handle error
        console.error(data);
      } else {
        // Append chunk to UI
        appendToChat(data);
      }
    }
  }
}
```

**Error Responses:**
- `400 Bad Request`: Message is empty
- `401 Unauthorized`: Invalid or expired token

---

#### Get Chat History

Get the conversation history for the current user.

**Endpoint:** `GET /api/chat/history`

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response:** `200 OK`
```json
{
  "messages": [
    {
      "role": "user",
      "content": "Hi, I'd like to start planning for my retirement."
    },
    {
      "role": "assistant",
      "content": "Hello! I'd be happy to help you plan for retirement..."
    }
  ]
}
```

---

#### Clear Chat History

Clear the conversation history for the current user.

**Endpoint:** `DELETE /api/chat/history`

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response:** `200 OK`
```json
{
  "success": true,
  "message": "Chat history cleared"
}
```

---

#### Export Chat

Export chat history as text and optionally trigger parsing to create a financial plan.

**Endpoint:** `POST /api/chat/export`

**Headers:**
```
Authorization: Bearer <access_token>
Content-Type: application/json
```

**Request Body:**
```json
{
  "trigger_parser": true
}
```

**Response:** `200 OK`
```json
{
  "success": true,
  "chat_text": "User: Hi, I'd like to start planning...\nAssistant: Hello! I'd be happy...",
  "filepath": "uploads/conversation_1_20240101_120000.txt"
}
```

**If parsing fails:**
```json
{
  "success": true,
  "chat_text": "...",
  "filepath": "...",
  "error": "Export succeeded but parsing failed: <error details>"
}
```

**Error Responses:**
- `200 OK` with `success: false`: Export failed
  ```json
  {
    "success": false,
    "error": "No chat history to export"
  }
  ```

**Note:** When `trigger_parser` is `true`, the system will:
1. Export the chat to a text file
2. Run the parser to extract financial data
3. Create a `FinancialPlan` and associated `CashFlow` records in the database
4. Return the exported text and file path

---

### File Upload Endpoint

Upload a conversation file for parsing.

**Endpoint:** `POST /api/upload`

**Headers:**
```
Authorization: Bearer <access_token>
Content-Type: multipart/form-data
```

**Request Body (multipart/form-data):**
```
file: <file>
```

**File Requirements:**
- File type: `.txt` only
- Max size: 16MB

**Response:** `200 OK`
```json
{
  "success": true,
  "financial_plan": {
    "id": 1,
    "user_id": 1,
    "name": "John Doe",
    "description": "John Doe",
    "start_age": 35,
    "retirement_age": 65,
    "plan_end_age": 100,
    "plan_start_date": "2024-01-01T00:00:00",
    "current_portfolio_value": 50000.0,
    "portfolio_target_value": 0.0
  },
  "cash_flows": [
    {
      "id": 1,
      "plan_id": 1,
      "name": "Salary",
      "description": "Salary",
      "amount": 5000.0,
      "start_date": "2024-01-01T00:00:00",
      "end_date": "2054-01-01T00:00:00"
    }
  ],
  "adviser_config": {
    "risk_allocation_map": {1: 0.3, 2: 0.5, 3: 0.6, 4: 0.8, 5: 0.9},
    "inflation": 0.02,
    "asset_costs": {"stocks": 0.001, "bonds": 0.001, "cash": 0.001},
    "expected_returns": {"stocks": 0.08, "bonds": 0.04, "cash": 0.02},
    "number_of_simulations": 5000
  }
}
```

**Error Responses:**
- `400 Bad Request`: No file selected, invalid file type, or file too large
- `500 Internal Server Error`: Error parsing conversation

---

### Simulation Endpoint

Run a financial simulation for a financial plan. The simulation automatically fetches cash flows from the database and uses default adviser configuration.

**Endpoint:** `POST /api/simulate`

**Headers:**
```
Authorization: Bearer <access_token>
Content-Type: application/json
```

**Request Body:**
```json
{
  "financial_plan_id": 1
}
```

**Optional Overrides:**

You can optionally override cash flows and adviser config if needed:

```json
{
  "financial_plan_id": 1,
  "cash_flows": [
    {
      "id": 1,
      "plan_id": 1,
      "name": "Custom Income",
      "description": "Custom income source",
      "amount": 6000.0,
      "start_date": "2024-01-01T00:00:00",
      "end_date": "2054-01-01T00:00:00"
    }
  ],
  "adviser_config": {
    "risk_allocation_map": {1: 0.3, 2: 0.5, 3: 0.6, 4: 0.8, 5: 0.9},
    "inflation": 0.025,
    "asset_costs": {"stocks": 0.001, "bonds": 0.001, "cash": 0.001},
    "expected_returns": {"stocks": 0.08, "bonds": 0.04, "cash": 0.02},
    "number_of_simulations": 10000
  }
}
```

**How It Works:**

1. **Financial Plan**: The system fetches the financial plan from the database using `financial_plan_id` and verifies it belongs to the authenticated user.

2. **Cash Flows**: If `cash_flows` is not provided in the request, the system automatically fetches all cash flows associated with the financial plan from the database.

3. **Adviser Config**: If `adviser_config` is not provided, the system uses default values:
   - `risk_allocation_map`: `{1: 0.3, 2: 0.5, 3: 0.6, 4: 0.8, 5: 0.9}`
   - `inflation`: `0.02`
   - `asset_costs`: `{"stocks": 0.001, "bonds": 0.001, "cash": 0.001}`
   - `expected_returns`: `{"stocks": 0.08, "bonds": 0.04, "cash": 0.02}`
   - `number_of_simulations`: `5000`

**Response:** `200 OK`
```json
{
  "success": true,
  "result": {
    // Simulation results (structure depends on simulation engine)
  }
}
```

**Error Responses:**

- `404 Not Found`: Financial plan not found or doesn't belong to user
  ```json
  {
    "detail": "Financial plan not found"
  }
  ```

- `200 OK` with `success: false`: Simulation failed
```json
{
  "success": false,
  "error": "Error message",
  "traceback": "Full traceback (if available)"
}
```

**Note:** The endpoint requires authentication and automatically verifies that the financial plan belongs to the authenticated user. Cash flows are fetched from the database, so ensure the financial plan has associated cash flows created via the Cash Flows endpoints.

---

## Data Models

### User

```typescript
interface User {
  id: number;
  email: string;
  name: string;
  is_active: boolean;
  is_verified: boolean;
  created_at: string; // ISO 8601 datetime
}
```

### FinancialPlan

```typescript
interface FinancialPlan {
  id?: number; // Optional, auto-generated on create
  user_id: number; // Auto-set from authenticated user
  name: string;
  description: string;
  start_age: number;
  retirement_age: number;
  plan_end_age: number;
  plan_start_date: string; // ISO 8601 datetime
  current_portfolio_value: number;
  portfolio_target_value: number;
}
```

### CashFlow

```typescript
interface CashFlow {
  id?: number; // Optional, auto-generated on create
  plan_id: number; // Set from URL path on create
  name: string;
  description: string;
  amount: number; // Positive for income, negative for expenses
  start_date?: string; // ISO 8601 datetime, optional
  end_date?: string; // ISO 8601 datetime, optional
}
```

### ChatMessage

```typescript
interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}
```

### AdviserConfig

```typescript
interface AdviserConfig {
  risk_allocation_map: Record<number, number>; // Risk level -> allocation percentage
  inflation: number;
  asset_costs: Record<string, number>; // Asset type -> cost percentage
  expected_returns: Record<string, number>; // Asset type -> expected return
  number_of_simulations: number;
}
```

### SimulationRequest

```typescript
interface SimulationRequest {
  financial_plan_id: number; // Required: ID of the financial plan to simulate
  cash_flows?: CashFlow[]; // Optional: Override cash flows from database
  adviser_config?: AdviserConfig; // Optional: Override default adviser configuration
}
```

**Note:** If `cash_flows` is not provided, the system automatically fetches all cash flows associated with the financial plan from the database. If `adviser_config` is not provided, default values are used.

### SimulationResponse

```typescript
interface SimulationResponse {
  success: boolean;
  result?: any; // Simulation results (structure depends on simulation engine)
  error?: string; // Error message if simulation failed
  traceback?: string; // Full traceback if available (for debugging)
}
```

---

## Error Handling

### Standard Error Response Format

```json
{
  "detail": "Error message"
}
```

### HTTP Status Codes

- `200 OK`: Request successful
- `201 Created`: Resource created successfully
- `204 No Content`: Request successful, no content to return
- `400 Bad Request`: Invalid request data
- `401 Unauthorized`: Authentication required or token invalid/expired
- `403 Forbidden`: User account is inactive
- `404 Not Found`: Resource not found
- `500 Internal Server Error`: Server error

### Token Expiration Handling

When an access token expires, you'll receive a `401 Unauthorized` response. Implement automatic token refresh:

```javascript
async function apiCall(url, options = {}) {
  const accessToken = getAccessToken();
  
  const response = await fetch(url, {
    ...options,
    headers: {
      ...options.headers,
      'Authorization': `Bearer ${accessToken}`
    }
  });
  
  if (response.status === 401) {
    // Token expired, try to refresh
    const newAccessToken = await refreshAccessToken();
    if (newAccessToken) {
      // Retry the request with new token
      return fetch(url, {
        ...options,
        headers: {
          ...options.headers,
          'Authorization': `Bearer ${newAccessToken}`
        }
      });
    } else {
      // Refresh failed, redirect to login
      redirectToLogin();
    }
  }
  
  return response;
}
```

---

## Example Workflows

### 1. User Registration and Login Flow

```javascript
// 1. Register
const registerResponse = await fetch('http://localhost:5000/api/auth/register', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    email: 'user@example.com',
    password: 'SecurePass123!',
    name: 'John Doe'
  })
});

const { user, tokens } = await registerResponse.json();
localStorage.setItem('accessToken', tokens.access_token);
localStorage.setItem('refreshToken', tokens.refresh_token);

// 2. Use access token for authenticated requests
const plansResponse = await fetch('http://localhost:5000/api/financial-plans', {
  headers: {
    'Authorization': `Bearer ${tokens.access_token}`
  }
});
```

### 2. Chat-Based Data Collection Flow

```javascript
// 1. Start chat conversation
const sendMessage = async (message) => {
  const response = await fetch('http://localhost:5000/api/chat/message', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${accessToken}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ message })
  });
  
  // Handle SSE stream
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let fullResponse = '';
  
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    
    const chunk = decoder.decode(value);
    const lines = chunk.split('\n');
    
    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const data = line.slice(6);
        if (data === '[DONE]') break;
        if (data.startsWith('[ERROR]')) {
          console.error(data);
        } else {
          fullResponse += data;
          updateChatUI(data);
        }
      }
    }
  }
};

// 2. Export and parse chat when ready
const exportAndParse = async () => {
  const response = await fetch('http://localhost:5000/api/chat/export', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${accessToken}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ trigger_parser: true })
  });
  
  const result = await response.json();
  if (result.success && !result.error) {
    // Financial plan and cash flows created
    // Redirect to plan view or refresh plan list
  }
};
```

### 3. Financial Plan Management Flow

```javascript
// 1. Create a financial plan
const createPlan = async (planData) => {
  const response = await fetch('http://localhost:5000/api/financial-plans', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${accessToken}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(planData)
  });
  return await response.json();
};

// 2. Add cash flows to the plan
const addCashFlow = async (planId, cashFlowData) => {
  const response = await fetch(`http://localhost:5000/api/cashflows/plan/${planId}`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${accessToken}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(cashFlowData)
  });
  return await response.json();
};

// 3. Get all plans with their cash flows
const getPlansWithCashFlows = async () => {
  const plansResponse = await fetch('http://localhost:5000/api/financial-plans', {
    headers: { 'Authorization': `Bearer ${accessToken}` }
  });
  const plans = await plansResponse.json();
  
  // Fetch cash flows for each plan
  const plansWithCashFlows = await Promise.all(
    plans.map(async (plan) => {
      const cashFlowsResponse = await fetch(
        `http://localhost:5000/api/cashflows/plan/${plan.id}`,
        { headers: { 'Authorization': `Bearer ${accessToken}` } }
      );
      const cashFlows = await cashFlowsResponse.json();
      return { ...plan, cash_flows: cashFlows };
    })
  );
  
  return plansWithCashFlows;
};
```

### 4. Run Simulation Flow

```javascript
// 1. Create a financial plan
const plan = await createPlan({
  name: "Retirement Plan 2024",
  description: "My retirement planning",
  start_age: 35,
  retirement_age: 65,
  plan_end_age: 100,
  plan_start_date: "2024-01-01T00:00:00",
  current_portfolio_value: 50000.0,
  portfolio_target_value: 1000000.0
});

// 2. Add cash flows to the plan
await addCashFlow(plan.id, {
  name: "Salary",
  description: "Monthly salary",
  amount: 5000.0,
  start_date: "2024-01-01T00:00:00",
  end_date: "2054-01-01T00:00:00"
});

await addCashFlow(plan.id, {
  name: "Mortgage",
  description: "Monthly mortgage payment",
  amount: -2000.0,
  start_date: "2024-01-01T00:00:00",
  end_date: "2034-01-01T00:00:00"
});

// 3. Run simulation (cash flows are automatically fetched from database)
const runSimulation = async (planId) => {
  const response = await fetch('http://localhost:5000/api/simulate', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${accessToken}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      financial_plan_id: planId
    })
  });
  
  const result = await response.json();
  
  if (result.success) {
    console.log('Simulation results:', result.result);
    return result.result;
  } else {
    console.error('Simulation failed:', result.error);
    throw new Error(result.error);
  }
};

// Run the simulation
const simulationResults = await runSimulation(plan.id);

// 4. Optional: Run simulation with custom adviser config
const runSimulationWithCustomConfig = async (planId) => {
  const response = await fetch('http://localhost:5000/api/simulate', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${accessToken}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      financial_plan_id: planId,
      adviser_config: {
        risk_allocation_map: {1: 0.2, 2: 0.4, 3: 0.6, 4: 0.8, 5: 0.95},
        inflation: 0.025,
        asset_costs: {"stocks": 0.0015, "bonds": 0.001, "cash": 0.0005},
        expected_returns: {"stocks": 0.09, "bonds": 0.04, "cash": 0.02},
        number_of_simulations: 10000
      }
    })
  });
  
  return await response.json();
};
```

---

## Additional Notes

### CORS

The API is configured to accept requests from:
- `http://localhost:3000` (React default)
- `http://localhost:5173` (Vite default)

For production, update CORS settings in `api/main.py`.

### Rate Limiting

Currently, there is no rate limiting implemented. Consider implementing rate limiting for production.

### Pagination

List endpoints (financial plans, cash flows) do not currently support pagination. All records are returned. Consider implementing pagination for large datasets.

### WebSocket Alternative

The chat endpoint uses Server-Sent Events (SSE) for streaming. If you prefer WebSockets, the backend would need to be modified to support WebSocket connections.

---

## Support

For questions or issues, please refer to the API documentation at `/docs` (Swagger UI) or `/redoc` (ReDoc) when the server is running.

