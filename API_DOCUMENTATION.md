# Financial Planning API Documentation

## Table of Contents
1. [Overview](#overview)
2. [Base URL](#base-url)
3. [Authentication](#authentication)
4. [API Endpoints](#api-endpoints)
   - [Authentication](#authentication-endpoints)
   - [Financial Plans](#financial-plans-endpoints)
     - [Duplicate Financial Plan](#duplicate-financial-plan-endpoint)
   - [Cash Flows](#cash-flows-endpoints)
   - [Portfolios](#portfolio-endpoints)
   - [Adviser Config](#adviser-config-endpoints)
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
- Portfolio management (CRUD operations)
- Adviser configuration management (user-level defaults)
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

Create a new user account. An adviser config with default settings is automatically created for the new user.

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

#### Duplicate Financial Plan

Create a new financial plan by duplicating an existing one, including its portfolios and cash flows.

- The source plan must belong to the authenticated user.
- The new plan will have the same parameters as the source plan, but with a generated name.
- All associated portfolios and cash flows are cloned:
  - `plan_id` is set to the new plan's id
  - `portfolio_id` on cash flows is remapped to the cloned portfolios
  - `reference_cashflow_id` is remapped to the cloned cash flows

**Endpoint:** `POST /api/financial-plans/{plan_id}/duplicate`

**Headers:**
```
Authorization: Bearer <access_token>
```

**Path Parameters:**
- `plan_id` (integer, required): ID of the financial plan to duplicate

**Request Body:**

None.

The new plan's name is automatically generated based on the source plan's name:

- `<name> (Copy)`
- `<name> (Copy 2)`, `<name> (Copy 3)`, ... if needed to ensure uniqueness per user.

**Response:** `201 Created`

Returns the duplicated financial plan.

```json
{
  "id": 42,
  "user_id": 1,
  "name": "Retirement Plan 2024 (Copy)",
  "description": "My retirement planning",
  "start_age": 35,
  "retirement_age": 65,
  "plan_end_age": 100,
  "plan_start_date": "2024-01-01T00:00:00",
  "portfolio_target_value": 1000000.0
}
```

**Error Responses:**
- `404 Not Found`: Financial plan not found or doesn't belong to user
- `500 Internal Server Error`: Failed to duplicate the financial plan

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
    "periodicity": "monthly",
    "frequency": 1,
    "start_date": "2024-01-01T00:00:00",
    "end_date": "2054-01-01T00:00:00"
  },
  {
    "id": 2,
    "plan_id": 1,
    "name": "Mortgage",
    "description": "Monthly mortgage payment",
    "amount": -2000.0,
    "periodicity": "monthly",
    "frequency": 1,
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
  "periodicity": "monthly",
  "frequency": 1,
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
  "periodicity": "monthly",
  "frequency": 1,
  "start_date": "2024-01-01T00:00:00",
  "end_date": "2054-01-01T00:00:00"
}
```

**Note:** 
- `plan_id` is set from the URL path. `id` is auto-generated.
- `periodicity` defaults to `"monthly"` if not provided
- `frequency` defaults to `1` if not provided

**Response:** `201 Created`
```json
{
  "id": 3,
  "plan_id": 1,
  "name": "Rental Income",
  "description": "Monthly rental income",
  "amount": 1500.0,
  "periodicity": "monthly",
  "frequency": 1,
  "start_date": "2024-01-01T00:00:00",
  "end_date": "2054-01-01T00:00:00"
}
```

**Example: Travel Expense Every 2 Years**
```json
{
  "name": "Travel Expense",
  "description": "Biannual vacation",
  "amount": 5000.0,
  "periodicity": "annually",
  "frequency": 2,
  "start_date": "2024-06-01T00:00:00",
  "end_date": "2054-06-01T00:00:00"
}
```

**Example: One-Off Expense**
```json
{
  "name": "Car Purchase",
  "description": "One-time car purchase",
  "amount": -30000.0,
  "periodicity": "one_off",
  "frequency": 1,
  "start_date": "2024-12-01T00:00:00",
  "end_date": null
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
  "periodicity": "monthly",
  "frequency": 1,
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
  "periodicity": "monthly",
  "frequency": 1,
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

### Portfolio Endpoints

All portfolio endpoints require authentication.

Portfolios define asset allocation strategies for financial plans. Each portfolio can have different expected returns, asset costs, and allocation weights. When portfolios are configured for a financial plan, the simulation service will automatically use them.

#### List Portfolios for a Plan

Get all portfolios for a specific financial plan.

**Endpoint:** `GET /api/portfolios/plan/{plan_id}`

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
    "name": "Conservative Portfolio",
    "weights": [
      {
        "step": 0.0,
        "stocks": 0.3,
        "bonds": 0.7,
        "cash": 0.0
      }
    ],
    "expected_returns": {
      "stocks": 0.06,
      "bonds": 0.03,
      "cash": 0.02
    },
    "asset_costs": {
      "stocks": 0.001,
      "bonds": 0.001,
      "cash": 0.001
    },
    "initial_portfolio_value": 48000.0,
    "cashflow_allocation": 0.4
  },
  {
    "id": 2,
    "plan_id": 1,
    "name": "Aggressive Portfolio",
    "weights": [
      {
        "step": 0.0,
        "stocks": 0.9,
        "bonds": 0.1,
        "cash": 0.0
      }
    ],
    "expected_returns": {
      "stocks": 0.10,
      "bonds": 0.04,
      "cash": null
    },
    "asset_costs": {
      "stocks": 0.0015,
      "bonds": 0.001,
      "cash": 0.001
    },
    "initial_portfolio_value": 72000.0,
    "cashflow_allocation": 0.6,
    "tax_jurisdiction": null,
    "tax_config": null
  }
]
```

**Note:** 
- `id` is the database primary key (auto-generated, optional on create)
- `plan_id` is set from the URL path on create
- `initial_portfolio_value` is the nominal dollar amount allocated to this portfolio
- `cashflow_allocation` must sum to 1.0 across all portfolios for a plan
- `weights` is an array of asset allocation weights at different time steps
- `expected_returns` and `asset_costs` can have `null` values for optional fields (e.g., `cash`)

**Error Responses:**
- `404 Not Found`: Financial plan not found or doesn't belong to user

---

#### Get Portfolio

Get a specific portfolio by ID.

**Endpoint:** `GET /api/portfolios/{portfolio_id}`

**Note:** `{portfolio_id}` is the integer database ID of the portfolio.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response:** `200 OK`
```json
{
  "id": 1,
  "plan_id": 1,
  "name": "Conservative Portfolio",
  "weights": [
    {
      "step": 0.0,
      "stocks": 0.3,
      "bonds": 0.7,
      "cash": 0.0
    }
  ],
  "expected_returns": {
    "stocks": 0.06,
    "bonds": 0.03,
    "cash": 0.02
  },
  "asset_costs": {
    "stocks": 0.001,
    "bonds": 0.001,
    "cash": 0.001
  },
  "initial_portfolio_value": 48000.0,
  "cashflow_allocation": 0.4
}
```

**Error Responses:**
- `404 Not Found`: Portfolio not found or doesn't belong to user's plan

---

#### Create Portfolio

Create a new portfolio for a financial plan.

**Endpoint:** `POST /api/portfolios/plan/{plan_id}`

**Headers:**
```
Authorization: Bearer <access_token>
Content-Type: application/json
```

**Request Body:**
```json
{
  "name": "Conservative Portfolio",
  "weights": [
    {
      "step": 0.0,
      "stocks": 0.3,
      "bonds": 0.7
      // cash is automatically calculated as 1 - 0.3 - 0.7 = 0.0
    }
  ],
  
  // Alternative example: If you want to explicitly specify all three allocations
  // (Note: cash is still computed, but you can verify it matches your desired value)
  // "weights": [
  //   {
  //     "step": 0.0,
  //     "stocks": 0.5,
  //     "bonds": 0.3
  //     // cash will be calculated as 1 - 0.5 - 0.3 = 0.2
  //   }
  // ],
  "expected_returns": {
    "stocks": 0.06,
    "bonds": 0.03,
    "cash": 0.02
  },
  "asset_costs": {
    "stocks": 0.001,
    "bonds": 0.001,
    "cash": 0.001
  },
  "initial_portfolio_value": 48000.0,
  "cashflow_allocation": 0.4,
  "tax_jurisdiction": null,
  "tax_config": null
}
```

**Note:** 
- `id` is optional (auto-generated on create)
- `plan_id` is set from the URL path
- `weights` must sum to 1.0 for each entry
  - You provide `stocks` and `bonds` in the request
  - `cash` is automatically calculated as `1 - stocks - bonds` and included in the response
  - If you want a specific cash allocation, set `stocks` and `bonds` such that `1 - stocks - bonds = desired_cash`
- `initial_portfolio_value` is the nominal dollar amount allocated to this portfolio
- `cashflow_allocation` must sum to 1.0 across all portfolios for the plan
- `tax_jurisdiction` and `tax_config` are optional. Both must be provided to apply tax. See [Tax Configuration](#tax-configuration) section for details.

**Response:** `201 Created`
```json
{
  "id": 1,
  "plan_id": 1,
  "name": "Conservative Portfolio",
  "weights": [
    {
      "step": 0.0,
      "stocks": 0.3,
      "bonds": 0.7,
      "cash": 0.0
    }
  ],
  "expected_returns": {
    "stocks": 0.06,
    "bonds": 0.03,
    "cash": 0.02
  },
  "asset_costs": {
    "stocks": 0.001,
    "bonds": 0.001,
    "cash": 0.001
  },
  "initial_portfolio_value": 48000.0,
  "cashflow_allocation": 0.4
}
```

**Error Responses:**
- `404 Not Found`: Financial plan not found or doesn't belong to user

---

#### Update Portfolio

Update an existing portfolio.

**Endpoint:** `PUT /api/portfolios/{portfolio_id}`

**Headers:**
```
Authorization: Bearer <access_token>
Content-Type: application/json
```

**Request Body:**
```json
{
  "name": "Updated Conservative Portfolio",
  "weights": [
    {
      "step": 0.0,
      "stocks": 0.35,
      "bonds": 0.65
    }
  ],
  "expected_returns": {
    "stocks": 0.065,
    "bonds": 0.035,
    "cash": 0.02
  },
  "asset_costs": {
    "stocks": 0.001,
    "bonds": 0.001,
    "cash": 0.001
  },
    "initial_portfolio_value": 60000.0,
  "cashflow_allocation": 0.5
}
```

**Note:** 
- `id` cannot be changed (it's the database primary key)
- `plan_id` cannot be changed
- All other fields can be updated

**Response:** `200 OK`
```json
{
  "id": 1,
  "plan_id": 1,
  "name": "Updated Conservative Portfolio",
  "weights": [
    {
      "step": 0.0,
      "stocks": 0.35,
      "bonds": 0.65,
      "cash": 0.0
    }
  ],
  "expected_returns": {
    "stocks": 0.065,
    "bonds": 0.035,
    "cash": 0.02
  },
  "asset_costs": {
    "stocks": 0.001,
    "bonds": 0.001,
    "cash": 0.001
  },
    "initial_portfolio_value": 60000.0,
  "cashflow_allocation": 0.5
}
```

**Error Responses:**
- `404 Not Found`: Portfolio not found or doesn't belong to user's plan

---

#### Delete Portfolio

Delete a portfolio.

**Endpoint:** `DELETE /api/portfolios/{portfolio_id}`

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response:** `204 No Content`

**Error Responses:**
- `404 Not Found`: Portfolio not found or doesn't belong to user's plan

**Note:** After deleting portfolios, ensure that remaining portfolios' `cashflow_allocation` still sums to 1.0, or the simulation may fail validation.

---

### Adviser Config Endpoints

All adviser config endpoints require authentication.

Adviser config represents user-level default settings that apply across all financial plans for a user. Each user has exactly one adviser config that defines default simulation parameters, risk allocation mappings, and frontend UI constraints.

**Important:** An adviser config is automatically created with default settings when a user account is registered. Users cannot create or delete their adviser config - they can only retrieve and update it.

#### Get Adviser Config

Get the adviser config for the current user.

**Endpoint:** `GET /api/adviser-configs`

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response:** `200 OK`
```json
{
  "risk_allocation_map": {1: 0.3, 2: 0.5, 3: 0.6, 4: 0.8, 5: 0.9},
  "inflation": 0.02,
  "asset_costs": {"stocks": 0.001, "bonds": 0.001, "cash": 0.001},
  "expected_returns": {"stocks": 0.08, "bonds": 0.04, "cash": 0.02},
  "number_of_simulations": 5000,
  "allocation_step": 0.10
}
```

**Error Responses:**
- `404 Not Found`: Adviser config not found for the current user (should not occur as config is created during registration)

---

#### Update Adviser Config

Update the adviser config for the current user.

**Endpoint:** `PUT /api/adviser-configs`

**Headers:**
```
Authorization: Bearer <access_token>
Content-Type: application/json
```

**Request Body:**
```json
{
  "risk_allocation_map": {1: 0.25, 2: 0.45, 3: 0.65, 4: 0.85, 5: 0.95},
  "inflation": 0.025,
  "asset_costs": {"stocks": 0.0015, "bonds": 0.001, "cash": 0.0005},
  "expected_returns": {"stocks": 0.09, "bonds": 0.04, "cash": 0.02},
  "number_of_simulations": 10000,
  "allocation_step": 0.05
}
```

**Response:** `200 OK`
```json
{
  "risk_allocation_map": {1: 0.25, 2: 0.45, 3: 0.65, 4: 0.85, 5: 0.95},
  "inflation": 0.025,
  "asset_costs": {"stocks": 0.0015, "bonds": 0.001, "cash": 0.0005},
  "expected_returns": {"stocks": 0.09, "bonds": 0.04, "cash": 0.02},
  "number_of_simulations": 10000,
  "allocation_step": 0.05
}
```

**Error Responses:**
- `404 Not Found`: Adviser config not found for the current user (should not occur as config is created during registration)

**Note:** 
- `allocation_step` is a frontend-only field that controls the precision of allocation inputs (e.g., 0.10 = 10% increments). This is not enforced on the backend.
- `risk_allocation_map` maps risk levels (1-5) to stock allocation percentages (0.0 to 1.0)
- `asset_costs` and `expected_returns` define costs and expected returns for each asset class
- `number_of_simulations` controls how many Monte Carlo simulation paths to run

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
    "number_of_simulations": 5000,
    "allocation_step": 0.10
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
    "number_of_simulations": 10000,
    "allocation_step": 0.10
  }
}
```

**How It Works:**

1. **Financial Plan**: The system fetches the financial plan from the database using `financial_plan_id` and verifies it belongs to the authenticated user.

2. **Cash Flows**: If `cash_flows` is not provided in the request, the system automatically fetches all cash flows associated with the financial plan from the database.

3. **Portfolios**: The system automatically fetches all portfolios associated with the financial plan from the database. Portfolios are always used for simulation. If no portfolios exist for the plan, you must create at least one portfolio before running a simulation.

4. **Adviser Config**: If `adviser_config` is not provided, the system first checks if the user has a saved adviser config in the database. If not, it uses default values:
   - `risk_allocation_map`: `{1: 0.3, 2: 0.5, 3: 0.6, 4: 0.8, 5: 0.9}`
   - `inflation`: `0.02`
   - `asset_costs`: `{"stocks": 0.001, "bonds": 0.001, "cash": 0.001}`
   - `expected_returns`: `{"stocks": 0.08, "bonds": 0.04, "cash": 0.02}`
   - `number_of_simulations`: `5000`
   - `allocation_step`: `0.10`

**Response:** `200 OK`

Always returns a `MultiPortfolioSimulationResultDTO` for consistent structure:

```json
{
  "success": true,
  "result": {
    "timestep_unit": "monthly",
    "aggregated": {
      "real": {
        "simulation_data": [[...], [...]],  // 2D array: [num_simulations][num_timesteps]
        "percentiles": {
          "5": [...],
          "25": [...],
          "50": [...],
          "75": [...],
          "95": [...]
        },
        "mean": [...],
        "final_mean": 1234567.89,
        "final_median": 987654.32,
        "final_std": 234567.89,
        "final_min": 0.0,
        "final_max": 5000000.0
      },
      "nominal": {
        "simulation_data": [[...], [...]],
        "percentiles": {
          "5": [...],
          "25": [...],
          "50": [...],
          "75": [...],
          "95": [...]
        },
        "mean": [...],
        "final_mean": 2345678.90,
        "final_median": 1876543.21,
        "final_std": 345678.90,
        "final_min": 0.0,
        "final_max": 8000000.0
      },
      "destitution": [0.0, 0.001, 0.002, ...],
      "timesteps": [0, 1, 2, 3, ...],  // Units depend on timestep_unit: months if "monthly", years if "annual"
      "simulation_time": 0.123,
      "simulation_time_per_timestep": 0.002,
      "simulation_time_per_path": 0.0001,
      "total_parameters": 354000,
      "destitution_area": 0.0025
    },
    "individual_portfolios": {
      "default": {
        // For single portfolio: same structure as aggregated above, key is "default"
        // For multi-portfolio: separate result for each portfolio, keyed by portfolio database ID (as string)
        "real": { ... },
        "nominal": { ... },
        "destitution": [...],
        "timesteps": [...],  // Units depend on timestep_unit at top level
        "simulation_time": 0.123,
        "simulation_time_per_timestep": 0.002,
        "simulation_time_per_path": 0.0001,
        "total_parameters": 354000,
        "destitution_area": 0.0025
      }
    }
  }
}
```

**Response Structure:**
- **Single portfolio** (default): `individual_portfolios` contains one entry with key `"default"`, and `aggregated` is identical to this single portfolio result
- **Multi-portfolio**: `individual_portfolios` contains separate results for each portfolio (keyed by portfolio database ID as string), and `aggregated` represents the combined wealth across all portfolios

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

**Note:** 
- The endpoint requires authentication and automatically verifies that the financial plan belongs to the authenticated user.
- Cash flows are fetched from the database, so ensure the financial plan has associated cash flows created via the Cash Flows endpoints.
- Portfolios are automatically fetched from the database. If portfolios exist for the financial plan, they will be used for the simulation. Create portfolios via the Portfolio endpoints.
- The response always uses the same structure (`MultiPortfolioSimulationResultDTO`) for consistency:
  - **Single portfolio** (default): `individual_portfolios` contains one entry with key `"default"`, and `aggregated` is identical to this result
  - **Multi-portfolio**: `individual_portfolios` contains separate results for each portfolio (keyed by portfolio database ID as string), and `aggregated` represents the combined wealth across all portfolios

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
  portfolio_target_value: number;
}
```

### CashFlow

```typescript
interface CashFlow {
  id?: number; // Optional, auto-generated on create
  plan_id: number; // Set from URL path on create
  portfolio_id?: number | null; // Optional: when set, this is a portfolio-specific cashflow; when null/omitted, it's a plan-level cashflow
  name: string;
  description: string;
  amount: number; // Interpretation depends on 'basis' (see below)
  periodicity: "monthly" | "quarterly" | "annually" | "one_off"; // Time unit for cashflow occurrence (default: "monthly")
  frequency: number; // Number of periods to skip between occurrences (default: 1, ignored for "one_off")
  start_date?: string; // ISO 8601 datetime, required for recurring cashflows, optional for one_off
  end_date?: string; // ISO 8601 datetime, required for recurring cashflows, optional for one_off
  basis?: "fixed" | "pct_total_income" | "pct_specific_income" | "pct_savings"; 
  // How to interpret 'amount':
  // - "fixed"              => amount is a nominal currency value (e.g., 500 = $500)
  // - "pct_total_income"   => amount is a percentage of total income at each timestep (e.g., 10 = 10% of total income)
  // - "pct_specific_income"=> amount is a percentage of a specific income cashflow (identified by reference_cashflow_id)
  // - "pct_savings"        => amount is a percentage of net savings (income - expenses) at each timestep

  reference_cashflow_id?: number | null; 
  // Optional id of another CashFlow this one is based on (used with "pct_specific_income" basis)

  include_in_main_savings?: boolean; 
  // Whether this cashflow should be included when computing plan-level net savings (income - expenses):
  // - true  => contributes to the shared income/expense pool (default for normal income/expenses)
  // - false => treated as a portfolio-specific adjustment (e.g., employer/government contributions) and
  //            does not change the shared net savings that get allocated across portfolios
}
```

**Periodicity and Frequency:**
- `periodicity`: Defines the time unit for cashflow occurrences
  - `"monthly"`: Cashflow occurs every N months (where N = frequency)
  - `"quarterly"`: Cashflow occurs every N quarters (where N = frequency)
  - `"annually"`: Cashflow occurs every N years (where N = frequency)
  - `"one_off"`: Single occurrence at `start_date` (frequency is ignored)
- `frequency`: Number of periods to skip between occurrences (minimum: 1)
  - Example: `periodicity="monthly", frequency=2` = every 2 months
  - Example: `periodicity="annually", frequency=2` = every 2 years
  - Example: `periodicity="quarterly", frequency=1` = every quarter (every 3 months)

**Amount Interpretation:**
- For `basis="fixed"`:
  - `periodicity="monthly"`: Amount is per month
  - `periodicity="quarterly"`: Amount is per quarter
  - `periodicity="annually"`: Amount is per year
  - `periodicity="one_off"`: Amount is total (single occurrence)
- For percentage-based bases (`"pct_total_income"`, `"pct_specific_income"`, `"pct_savings"`):
  - `amount` is always interpreted as a percentage (e.g., `10` = 10%) of the chosen base at each timestep

**Date Requirements:**
- Recurring cashflows (`monthly`, `quarterly`, `annually`): Both `start_date` and `end_date` are required
- One-off cashflows (`one_off`): Only `start_date` is required (or `end_date` can equal `start_date`)

### PortfolioConfig

```typescript
interface SimulationPortfolioWeights {
  step: number; // Time step (year) for this weight configuration
  stocks: number; // Stock allocation (0.0 to 1.0)
  bonds: number; // Bond allocation (0.0 to 1.0)
  cash: number; // Cash allocation (always calculated as 1 - stocks - bonds, returned in response but not required in request)
}

interface ExpectedReturns {
  stocks?: number; // Expected return for stocks (0.0 to 1.0, optional)
  bonds?: number; // Expected return for bonds (0.0 to 1.0, optional)
  cash?: number | null; // Expected return for cash (0.0 to 1.0, optional)
}

interface AssetCosts {
  stocks: number; // Asset cost for stocks (0.0 to 1.0)
  bonds: number; // Asset cost for bonds (0.0 to 1.0)
  cash: number; // Asset cost for cash (0.0 to 1.0)
}

interface PortfolioConfig {
  id?: number; // Optional, auto-generated database primary key
  plan_id: number; // Financial plan this portfolio belongs to (set from URL on create)
  name?: string; // Optional name for the portfolio
  weights: SimulationPortfolioWeights[]; // Array of weight configurations over time
  expected_returns: ExpectedReturns; // Expected returns for each asset class
  asset_costs: AssetCosts; // Asset costs for each asset class
  initial_portfolio_value: number; // Nominal dollar value of initial wealth allocated to this portfolio
  cashflow_allocation: number; // Fraction of cashflows (must sum to 1.0 across all portfolios)
  tax_jurisdiction?: string | null; // Tax jurisdiction (e.g., "nz", "au") or null for no tax. Optional.
  tax_config?: TaxConfig | null; // Jurisdiction-specific tax parameters. Optional. See TaxConfig section below.
}
```

**Note:** 
- `id` is the database primary key (auto-generated, optional on create)
- `plan_id` is set from the URL path when creating portfolios
- `initial_portfolio_value` is the nominal dollar amount allocated to this portfolio (not a fraction)
- `cashflow_allocation` must sum to 1.0 across all portfolios for a plan
- Each entry in `weights` must have `stocks + bonds + cash = 1.0`
  - You provide `stocks` and `bonds` in the request
  - `cash` is automatically calculated as `1 - stocks - bonds` and included in the response
  - If you want a specific cash allocation, set `stocks` and `bonds` such that `1 - stocks - bonds = desired_cash`
- **Tax Configuration**: 
  - Both `tax_jurisdiction` and `tax_config` must be provided to apply tax calculations
  - If either is `null` or omitted, the portfolio will be simulated without tax
  - `tax_jurisdiction` can default to `adviser_config.tax_jurisdiction` if not provided
  - See [Tax Configuration](#tax-configuration) section below for details on tax config structure
- When portfolios are configured for a financial plan, the simulation service automatically uses them
- At least one portfolio must exist for a financial plan before running a simulation

### Tax Configuration

Tax configuration models define the structure for jurisdiction-specific tax parameters. These models are used in the `tax_config` field of `PortfolioConfig`.

**Important:** Both `tax_jurisdiction` and `tax_config` must be provided for tax to be applied. If either is `null` or omitted, the portfolio will be simulated without tax, even if a jurisdiction is set.

#### TaxConfig (Union Type)

```typescript
// Currently supported jurisdictions:
type TaxConfig = NewZealandTaxConfig;
// Future jurisdictions will be added here as they are implemented:
// type TaxConfig = NewZealandTaxConfig | AustralianTaxConfig | USTaxConfig | ...
```

#### NewZealandTaxConfig

Tax configuration for New Zealand accounts using PIE (Portfolio Investment Entity) and FIF (Foreign Investment Fund) tax rules.

```typescript
interface NewZealandTaxConfig {
  jurisdiction: "nz"; // Must be "nz" for New Zealand tax
  pir_rate: number; // Prescribed Investor Rate (PIR), 0.0 to 1.0 (e.g., 0.28 = 28%)
  marginal_tax_rate: number; // Marginal tax rate, 0.0 to 1.0 (e.g., 0.33 = 33%)
  percent_pie_fund: number; // Percentage of portfolio in PIE funds, 0.0 to 1.0 (e.g., 0.6 = 60%)
  percent_fif_fund: number; // Percentage of portfolio in FIF funds, 0.0 to 1.0 (e.g., 0.4 = 40%)
}
```

**Validation Rules:**
- `pir_rate`: Must be between 0.0 and 1.0 (inclusive)
- `marginal_tax_rate`: Must be between 0.0 and 1.0 (inclusive)
- `percent_pie_fund`: Must be between 0.0 and 1.0 (inclusive)
- `percent_fif_fund`: Must be between 0.0 and 1.0 (inclusive)
- `percent_pie_fund + percent_fif_fund` must equal 1.0 (within 0.01 tolerance)

**Example:**
```json
{
  "jurisdiction": "nz",
  "pir_rate": 0.28,
  "marginal_tax_rate": 0.33,
  "percent_pie_fund": 0.6,
  "percent_fif_fund": 0.4
}
```

**Usage in PortfolioConfig:**
```typescript
const portfolio: PortfolioConfig = {
  // ... other fields ...
  tax_jurisdiction: "nz",
  tax_config: {
    jurisdiction: "nz",
    pir_rate: 0.28,
    marginal_tax_rate: 0.33,
    percent_pie_fund: 0.6,
    percent_fif_fund: 0.4
  }
};
```

**Note:** More jurisdiction-specific tax config models will be added here as they are implemented (e.g., `AustralianTaxConfig`, `USTaxConfig`, etc.). The `TaxConfig` union type will be updated to include all supported jurisdictions.

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
  risk_allocation_map: Record<number, number>; // Risk level (1-5) -> stock allocation percentage (0.0 to 1.0)
  inflation: number; // Annual inflation rate (e.g., 0.02 = 2%)
  asset_costs: Record<string, number>; // Asset type -> cost percentage (e.g., {"stocks": 0.001, "bonds": 0.001, "cash": 0.001})
  expected_returns: Record<string, number>; // Asset type -> expected return (e.g., {"stocks": 0.08, "bonds": 0.04, "cash": 0.02})
  number_of_simulations: number; // Number of Monte Carlo simulation paths to run
  allocation_step: number; // Frontend-only: Step size for allocation inputs (e.g., 0.10 = 10% increments). Not enforced on backend.
  tax_jurisdiction?: string | null; // Default tax jurisdiction (e.g., "nz", "au") for new portfolios. Optional.
}
```

**Note:** 
- `allocation_step` is a frontend-only field that controls the precision of allocation inputs in the UI (e.g., 0.10 means users can only input 80%, 70%, 60%, etc., not 85%, 75%, 65%). This constraint is not enforced on the backend.
- `tax_jurisdiction` is a default value that can be used when creating new portfolios. It does not automatically apply tax - portfolios must have both `tax_jurisdiction` and `tax_config` set to actually apply tax calculations.
- Each user can have one adviser config that serves as default settings across all their financial plans.
- If no adviser config exists for a user, default values are used when running simulations.

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
  result?: MultiPortfolioSimulationResultDTO; // Always returns consistent structure
  error?: string; // Error message if simulation failed
  traceback?: string; // Full traceback if available (for debugging)
}
```

### SimulationResultDTO

```typescript
interface SimulationDataDTO {
  simulation_data: number[][]; // 2D array: [num_simulations][num_timesteps]
  percentiles: {
    5: number[];
    25: number[];
    50: number[];
    75: number[];
    95: number[];
  };
  mean: number[]; // Mean wealth at each timestep
  final_mean: number; // Mean wealth at final timestep
  final_median: number; // Median wealth at final timestep
  final_std: number; // Standard deviation of final wealth
  final_min: number; // Minimum final wealth across all simulations
  final_max: number; // Maximum final wealth across all simulations
}

interface SimulationResultDTO {
  real: SimulationDataDTO; // Inflation-adjusted wealth values
  nominal: SimulationDataDTO; // Current dollar values (not inflation-adjusted)
  destitution: number[]; // Probability of destitution at each timestep (0.0 to 1.0)
  timesteps: number[]; // Time points for each data point (units: months if timestep_unit="monthly", years if timestep_unit="annual")
  simulation_time: number; // Total execution time in seconds
  simulation_time_per_timestep: number; // Average time per timestep
  simulation_time_per_path: number; // Average time per simulation path
  total_parameters: number; // Total number of parameters computed
  destitution_area: number; // Time-weighted average destitution risk
}
```

### MultiPortfolioSimulationResultDTO

```typescript
interface MultiPortfolioSimulationResultDTO {
  timestep_unit: "monthly" | "annual"; // Time unit for all timesteps in the response (applies to all data)
  aggregated: SimulationResultDTO; // Combined results across all portfolios
  individual_portfolios: Record<string, SimulationResultDTO>; // Results for each portfolio, keyed by portfolio database ID (as string)
}
```

**Note:** The response always uses `MultiPortfolioSimulationResultDTO` for consistency:
- **Single portfolio**: `individual_portfolios` contains one entry with key `"default"`, and `aggregated` is identical to this result
- **Multi-portfolio**: `individual_portfolios` contains separate results for each portfolio (keyed by portfolio database ID as string), and `aggregated` represents the combined wealth across all portfolios
- **Timestep Unit**: The `timestep_unit` field indicates whether timesteps represent months or years. When `"monthly"`, timesteps are in months (e.g., 0, 1, 2, ..., 360 for 30 years). When `"annual"`, timesteps are in years (e.g., 0, 1, 2, ..., 30). This applies to all timestep arrays in the response.

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
        number_of_simulations: 10000,
        allocation_step: 0.05
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

