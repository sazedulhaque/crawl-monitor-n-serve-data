# Crawl Monitor and Serve Data

A web crawling, monitoring and data serving application built with FastAPI, MongoDB and Beanie ODM.

## Features

- **Web Scraping**: Automated book data extraction from books.toscrape.com
- **Change Detection**: Content hash-based change monitoring with three-tier optimization
- **Scheduled Tasks**: Configurable crawling intervals (12h/24h) with APScheduler
- **REST API**: Comprehensive FastAPI endpoints with authentication
- **Rate Limiting**: Global 100/hour limit with endpoint-specific overrides
- **Data Storage**: MongoDB with Beanie ODM and change history tracking
- **Authentication**: JWT-based auth with dual methods (OAuth2 + Bearer token)
- **Testing**: test cases with pytest and coverage reporting
- **Docker Support**: Full containerization with Docker Compose

## Prerequisites

- Python 3.12+
- Docker and Docker Compose
- MongoDB (included in Docker setup)

## Quick Start

1. **Clone the repository**:

   ```bash
   git clone https://github.com/sazedulhaque/crawl-monitor-n-serve-data.git
   cd crawl-monitor-n-serve-data
   ```

2. **Start with Docker** (Recommended):

   ```bash
   docker-compose up --build
   ```

3. **Access the application**:
   - API: http://localhost:8000
   - Swagger UI: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc

## Local Development Setup

1. **Create virtual environment**:

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies**:

   ```bash
   pip install -r requirements.txt
   ```

3. **Environment configuration**:

   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

4. **Run locally**:
   ```bash
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

## Environment Variables

Create a `.env` file:

```env
# Application
PROJECT_NAME="Book Scraping API"
VERSION="1.0.0"
ENVIRONMENT="development"

# Database
MONGODB_URL=mongodb://mongodb:27017
DATABASE_NAME=book_scraper_db

# Security
SECRET_KEY=your-secret-key-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440


# Crawling Configuration
CRAWL_INTERVAL= 360  # in minutes == 6 hour
NOTIFICATIONL_INTERVAL=12
```

## API Documentation

### Authentication

The API supports **two authentication methods**:

1. **OAuth2 Password Flow** (Swagger UI):
   - Click "Authorize" → "OAuth2PasswordBearer"
   - Enter username/password
2. **Bearer Token** (Direct):
   - Get token from `/api/v1/auth/token`
   - Click "Authorize" → "HTTPBearer"
   - Paste token

### Core Endpoints

#### Authentication

- `POST /api/v1/auth/register` - Register new user
- `POST /api/v1/auth/login` - User login
- `POST /api/v1/auth/token` - OAuth2 token endpoint
- `GET /api/v1/auth/me` - Get current user
- `GET /api/v1/auth/verify-token` - Verify token validity

#### Books Management

- `GET /api/v1/books/` - List books (filtering, pagination, sorting)
- `GET /api/v1/books/{id}` - Get specific book
- `POST /api/v1/books/` - Create book (authenticated)
- `PUT /api/v1/books/{id}` - Update book (authenticated)
- `DELETE /api/v1/books/{id}` - Delete book (authenticated)

#### Change Monitoring

- `GET /api/v1/books/changes/recent` - Book data changes report
- `GET /api/v1/books/session/data` - Scraping session history

#### System

- `GET /health-check` - Health check

## Scheduler Configuration

The application runs automated tasks:

- **Book Scraping**: Every 6 hours (configurable via .env.example & it will create .env in docker container)

### Code Quality Tools

```bash
# Install pre-commit hooks
pre-commit install

# Run manually on all files
pre-commit run --all-files

# Format with Black
black apps/

# Lint with Ruff and fix
ruff check . --fix
```

### VS Code Configuration

The `.vscode/settings.json` configures:

- Black formatting on save
- Ruff linting
- Import organization
- Python path settings

### Authenticate and Get Books

```bash
# Get token
TOKEN=$(curl -X POST "http://localhost:8000/api/v1/auth/token" \
  -d "username=your_user&password=your_pass" | jq -r '.access_token')

# Use token
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/books/?category=Fiction&min_price=10"
```

## Dependencies

### Core Framework

- fastapi==0.115.4
- uvicorn[standard]==0.32.0
- beanie==2.0.0
- pydantic==2.9.2
- pydantic-settings==2.6.0

### Authentication & Security

- python-multipart==0.0.17
- python-jose[cryptography]==3.3.0
- argon2-cffi==23.1.0
- slowapi==0.1.9

### Web Scraping & HTTP

- httpx==0.27.2
- beautifulsoup4==4.12.3
- lxml==5.3.0

### Task Scheduling & Utils

- apscheduler==3.10.4
- aiofiles

### Development & Code Quality

- ruff
- black
- pre-commit

### Testing

- pytest==8.3.3
- pytest-asyncio==0.24.0
- pytest-cov==6.0.0
- pytest-mock==3.14.0

## API Testing

The API includes built-in Swagger UI documentation. When running the application:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Sample API Endpoints

#### Health & Info

- `GET /health-check` - Health check

#### Books

- `GET /api/v1/books/` - List all books (with pagination)
- `POST /api/v1/books/` - Create a book
- `GET /api/v1/books/{book_id}` - Get book by ID
- `PUT /api/v1/books/{book_id}` - Update book by ID
- `DELETE /api/v1/books/{book_id}` - Delete book by ID

#### Crawling & Monitoring

- `GET /api/v1/books/changes/recent` - Get recent book changes (daily report)
- `GET /api/v1/books/session/data` - Get crawl session data

#### Authentication

- `POST /api/v1/auth/register` - Register new user
- `POST /api/v1/auth/login` - User login
- `GET /api/v1/auth/me` - Get current user information
- `POST /api/v1/auth/refresh` - Refresh authentication token

### Running Tests

```bash
pytest apps/tests
pytest
```

## Trouble with linter, execute pre-commit manually on local machine

```shell
pre-commit run --all-files
```

## How can we check the changes

To verify that the change detection system is working correctly:

1. Modify book data directly in the MongoDB database, or use the GET and PUT API endpoints
2. **Important**: When updating a book, you must also update the `content_hash` field to reflect the content changes. Otherwise, the change detection mechanism will not recognize the modifications.

### Note of improvment

1. As it is a test base project So I try to make it simple with the given criteria. But in production level develoopment we can Follow the best practices like Dependency invertion .etc
2. Scrping has challenges like pagination, change detection but here we try to put some delay and present the crawler as a legit by using user agent in headers but there is still room for improvment.

3. I added create/update/delete API for book so we can test it properly.

4. Normally we try to put every static in a constant variable with upper caps but here we did not add it due to time limit.

5. We can improve the rate limiter more robust by using a middleware for applying global limits.

6. In user registration normally i put password & reconfirm password field. Here I escaped it;

7. We also used MD5 hash for content hasing as this hash is for comparing not for security purpose.

## API Examples

### Get Change Report

`http://localhost:8001/api/v1/books/changes/recent?page=1&size=50`

### Sample:

```json
[
  {
    "_id": "68e2732809965e46fd391304",
    "created_at": "2025-10-05T13:31:20.854000",
    "updated_at": "2025-10-05T13:31:20.854000",
    "book": {
      "id": "68e2717bdc898bab9b1a6b97",
      "collection": "books"
    },
    "change_type": "updated",
    "field_changed": "in_stock",
    "old_value": "True",
    "new_value": "False",
    "changes": {
      "in_stock": {
        "old": "True",
        "new": "False"
      }
    },
    "description": "in_stock updated from True to False",
    "crawl_session_id": null
  },
  {
    "_id": "68e27b1909965e46fd391308",
    "created_at": "2025-10-05T14:05:13.836000",
    "updated_at": "2025-10-05T14:05:13.836000",
    "book": {
      "id": "68e2717bdc898bab9b1a6b97",
      "collection": "books"
    },
    "change_type": "updated",
    "field_changed": null,
    "old_value": null,
    "new_value": null,
    "changes": {
      "title": {
        "old": "Penny Maybe Gone",
        "new": "Penny Maybe"
      },
      "in_stock": {
        "old": false,
        "new": true
      },
      "rating": {
        "old": 4,
        "new": 3
      },
      "reviews_count": {
        "old": 1,
        "new": 0
      }
    },
    "description": "Updated 4 field(s) during crawl",
    "crawl_session_id": "0e0c63aa-5bd9-466e-aa6a-66031ac56cbc"
  }
]
```

### Get Scraping Session Data

`http://localhost:8001/api/v1/books/session/data?page=1&size=50`

### Sample:

```json
[
  {
    "_id": "68e27aff09965e46fd391307",
    "created_at": "2025-10-05T14:04:47.332000",
    "updated_at": "2025-10-05T14:14:19.773000",
    "session_id": "0e0c63aa-5bd9-466e-aa6a-66031ac56cbc",
    "status": "running",
    "started_by": null,
    "total_pages": 50,
    "processed_pages": 48,
    "new_books": 0,
    "updated_books": 1,
    "failed_books": 0,
    "last_processed_url": null,
    "error_message": null,
    "completed_at": null
  },
  {
    "_id": "68e27163dc898bab9b1a6b65",
    "created_at": "2025-10-05T13:23:47.184000",
    "updated_at": "2025-10-05T13:33:40.930000",
    "session_id": "ddb19f48-d5e4-49f3-a041-c4cf8bc82a5c",
    "status": "completed",
    "started_by": null,
    "total_pages": 50,
    "processed_pages": 50,
    "new_books": 1000,
    "updated_books": 0,
    "failed_books": 0,
    "last_processed_url": null,
    "error_message": null,
    "completed_at": "2025-10-05T13:33:40.930000"
  }
]
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
