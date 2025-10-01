# Crawl Monitor and Serve Data

A web crawling, monitoring, and data serving application built with FastAPI, MongoDB, and Beanie ODM.

## Features

- Web crawling with BeautifulSoup
- Scheduled crawling tasks with APScheduler
- REST API with FastAPI
- MongoDB data storage with Beanie ODM
- Docker containerization

## Prerequisites

- Python 3.12
- Docker and Docker Compose

## Setup Instructions

1. Clone the repository:

   ```bash
   git clone https://github.com/sazedulhaque/crawl-monitor-n-serve-data.git
   cd crawl-monitor-n-serve-data
   ```

2. Create a virtual environment:

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Copy the example environment file:

   ```bash
   cp .env.example .env
   ```

5. Edit `.env` with your configuration.

6. Run with Docker Compose:

   ```bash
   docker-compose up --build
   ```

   Or run locally:

   ```bash
   uvicorn main:app --reload
   ```

## Environment Variables

Create a `.env` file based on `.env.example`:

```
MONGODB_URL=mongodb://db:27017
DATABASE_NAME=crawl_monitor
CRAWL_INTERVAL=60
```

## Dependencies

- fastapi==0.104.1
- uvicorn[standard]==0.24.0
- beanie
- pydantic
- requests
- beautifulsoup4
- apscheduler
- python-dotenv

## API Testing

The API includes built-in Swagger UI documentation. When running the application:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Sample API Endpoints

- `GET /` - Health check
- `GET /api/v1/` - List all items
- `POST /api/v1/` - Create an item
- `GET /api/v1/{item_id}` - Get item by ID
- `PUT /api/v1/{item_id}` - Update item by ID
- `DELETE /api/v1/{item_id}` - Delete item by ID

## Sample MongoDB Document Structure

```json
{
  "_id": "ObjectId('...')",
  "name": "Sample Item",
  "description": "This is a sample document",
  "url": "https://example.com",
  "crawl_timestamp": "2023-09-30T12:00:00Z",
  "status_code": 200,
  "content_length": 12345
}
```

## Screenshots and Logs

### Successful Crawl Run

![Crawl Success](screenshots/crawl_success.png)

### Scheduler Logs

```
2023-09-30 12:00:00 - Scheduler started
2023-09-30 12:01:00 - Crawl task executed successfully
2023-09-30 12:02:00 - Data saved to MongoDB
```

## Development

### Code Formatting

This project uses Black for automatic code formatting. The VS Code settings are configured to format Python files on save.

#### Setup

1. Install development dependencies:

   ```bash
   pip install -r requirements.txt
   ```

2. Install pre-commit hooks (optional, for consistency):
   ```bash
   pre-commit install
   ```

#### VS Code Configuration

The `.vscode/settings.json` file is configured to:

- Use Black as the Python formatter
- Format code on save
- Organize imports automatically
- Enable Ruff linting

### Running Tests

```bash
pytest tests/
```

## Trouble with linter, execute pre-commit manually on local machine

```shell
pre-commit run --all-files
```

### Adding New Crawlers

1. Create a new crawler in `crawler/`
2. Update the scheduler in `scheduler/scheduler.py`
3. Add API endpoints in `api/app.py`

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
