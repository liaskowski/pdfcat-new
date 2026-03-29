# PDF Library System

A full-stack document management system consisting of a **FastAPI Backend** and a **Modern PyQt6 Client**.

## 🌟 Key Features

### Backend (Server)
- **FastAPI**: High-performance async API.
- **OCR Engine**: Tesseract integration for scanning images/PDFs.
- **Full-Text Search**: Automatic indexing of document content.
- **Security**: JWT Authentication & Role-based access control.
- **Headless Processing**: Background tasks for PDF analysis.

### Frontend (Client)
- **Modern UI**: Adaptive layouts, dark/light themes, and responsive design.
- **Smart Caching**: Local caching of thumbnails and large previews for instant loading.
- **State Persistence**: Remembers window sizes, positions, and splitters between sessions.
- **PDF Viewer**: Custom-built high-performance PDF viewer with zoom and rotation.
- **Admin Panel**: User management interface.

## 🛠 Installation

### Prerequisites
- **Python 3.12+** (recommended 3.14)
- **Go 1.21+** (for microservices)
- **Node.js 18+** (optional, for frontend development)

### 1. Clone the repository
```bash
git clone <repository_url>
cd pdfCAT
```

### 2. Setup Python Environment
```bash
# Create virtual environment (standard naming)
python -m venv .venv

# Activate environment
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# Install dependencies
pip install -r server/requirements.txt
pip install -r client/requirements.txt  # if available
```

### 3. Install Tesseract OCR (Required for server-side OCR)
- **Windows**: [Download Installer](https://github.com/UB-Mannheim/tesseract/wiki) or `choco install tesseract`
- **Linux**: `sudo apt-get install tesseract-ocr`
- **macOS**: `brew install tesseract`

### 4. Setup Go Microservices
```bash
cd services
go mod download
cd ..
```

## 🚀 Running the Application

### Quick Start (Recommended)
```bash
# Start all services (Go microservices + FastAPI)
.\start_server.bat          # Windows
# or
python start_all.py         # Cross-platform
```

### Manual Start

#### 1. Start Go Microservices
```bash
# Terminal 1 - Search Service
cd services/search-service
go run main.go

# Terminal 2 - PDF Service  
cd services/pdf-service
go run main.go
```

#### 2. Start FastAPI Server
```bash
# Terminal 3
python server/main.py
# Or via uvicorn:
uvicorn server.main:app --reload --port 8000
```

#### 3. Start Client (Optional)
```bash
# Terminal 4
python -m client.main
```

### Service URLs
- **FastAPI Server**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Search Service**: http://localhost:8001/health
- **PDF Service**: http://localhost:8002/health

## 📂 Project Structure

```
pdfCAT/
├── .venv/                    # Python virtual environment (standard)
├── server/                   # FastAPI backend
│   ├── main.py              # FastAPI application entry point
│   ├── requirements.txt     # Python dependencies
│   └── ...                  # Other server modules
├── services/                # Go microservices
│   ├── search-service/      # Search microservice (port 8001)
│   ├── pdf-service/         # PDF processing microservice (port 8002)
│   └── ...                  # Other services
├── client/                  # PyQt6 desktop application
│   ├── main.py             # Client entry point
│   ├── ui/                 # UI components
│   ├── controllers/        # Business logic
│   ├── api/                # API client wrapper
│   └── utils/              # Helper utilities
├── uploads/                 # Document storage
├── logs/                    # Application logs
├── docs/                    # Documentation
├── scripts/                 # Utility scripts
├── tests/                   # Test files
├── start_server.bat        # Windows startup script
├── start_all.py           # Cross-platform startup script
├── requirements.txt       # Global dependencies (if needed)
└── .gitignore             # Git ignore rules
```

## ⚙️ Configuration

### Environment Variables
Create `.env` file in project root (optional):
```env
# Server Configuration
PORT=8000
HOST=0.0.0.0
DEBUG=false

# Database
DATABASE_URL=sqlite:///./app.db

# Security
SECRET_KEY=your-secret-key-here
ADMIN_PASSWORD=admin

# OCR
TESSERACT_CMD=/usr/bin/tesseract  # Linux/macOS
# TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe  # Windows
```

### Virtual Environment
- **Standard naming**: `.venv` (follows Python conventions)
- **Python version**: 3.12+ (recommended 3.14)
- **Isolation**: Complete separation from system Python
- **Reproducibility**: All dependencies in `requirements.txt`

### Port Allocation
- **8000**: FastAPI main server
- **8001**: Go Search Service
- **8002**: Go PDF Service
- **50000-50001**: Service discovery (internal)

## 🧩 Development Standards

### Team Collaboration
1. **Environment Setup**: Always use `.venv` for virtual environment
2. **Dependencies**: Keep `requirements.txt` updated
3. **Code Style**: Follow PEP 8 for Python, go fmt for Go
4. **Branching**: Use feature branches, PR for review
5. **Testing**: Write tests for new features

### Virtual Environment Rules
- ✅ **Use `.venv`** - standard Python convention
- ✅ **Add to `.gitignore`** - never commit venv
- ✅ **Document dependencies** - keep requirements.txt updated
- ✅ **Python 3.12+** - ensure compatibility
- ❌ **No system packages** - keep environment isolated
- ❌ **No hardcoded paths** - use relative paths

### Startup Scripts
- **`start_server.bat`**: Windows batch script for team members
- **`start_all.py`**: Cross-platform Python script
- Both scripts auto-detect and create `.venv` if missing
- Both scripts install dependencies automatically