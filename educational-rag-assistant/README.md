# Educational RAG Assistant

An educational Retrieval-Augmented Generation (RAG) assistant built with:
- GLM-OCR for document processing
- E5-large for text embeddings
- PostgreSQL for metadata storage
- Qdrant for vector storage
- Ollama Cloud for LLM inference

## Features

- Document upload and processing with OCR
- Text chunking and embedding generation
- Semantic search using vector similarity
- Chat interface with RAG-powered responses
- User session management
- RESTful API with FastAPI

## Architecture

```
├── app/
│   ├── core/           # Core configuration and utilities
│   ├── models/         # SQLAlchemy data models
│   ├── schemas/        # Pydantic validation schemas
│   ├── api/            # API endpoints
│   └── services/       # Business logic services (to be implemented)
├── data/               # Data storage directory
├── requirements.txt    # Python dependencies
├── docker-compose.yml  # Docker services (PostgreSQL, Qdrant)
└── .env                # Environment variables
```

## Setup (Установка и запуск)

1. Клонируйте репозиторий:
   ```bash
   git clone <URL>
   cd educational-rag-assistant
   ```

2. Создайте и активируйте виртуальное окружение (venv):
   ```bash
   python -m venv venv
   source venv/bin/activate  # Для Mac/Linux
   # Или для Windows: venv\Scripts\activate
   ```

3. Установите зависимости:
   ```bash
   pip install -r requirements.txt
   ```

4. Настройте окружение в файле `.env` (при необходимости).

5. Включите Docker (запустите Docker Desktop) и поднимите необходимые сервисы:
   ```bash
   docker-compose up -d
   ```

6. Запустите сервер (приложение запуск через команду):
   ```bash
   uvicorn app.main:app --reload
   ```
   После запуска приложение будет доступно по адресу: http://localhost:8000


## API Endpoints

### Documents
- `POST /api/v1/documents/` - Upload and process a document
- `GET /api/v1/documents/` - List all documents
- `GET /api/v1/documents/{id}` - Get a specific document
- `PUT /api/v1/documents/{id}` - Update a document
- `DELETE /api/v1/documents/{id}` - Delete a document

### Chat
- `POST /api/v1/sessions/` - Create a new chat session
- `GET /api/v1/sessions/` - List chat sessions
- `GET /api/v1/sessions/{id}` - Get a specific chat session
- `POST /api/v1/sessions/{session_id}/messages` - Add a message to a session
- `POST /api/v1/query/` - Process a query with RAG

## Health Check
- `GET /` - Root endpoint
- `GET /health` - Health check endpoint

## License

MIT