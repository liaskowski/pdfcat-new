# Performance Optimizations and Bug Fixes

## Summary of Changes

This document describes all the optimizations and fixes implemented to address the performance issues with bulk file uploads and server stability.

---

## Issues Fixed

### 1. Server Startup Check (Port Conflict Detection)
**Problem:** No way to detect if server was already running, causing potential conflicts.

**Solution:** 
- Added `is_port_in_use()` and `check_existing_server_process()` functions in `server/main.py`
- Server now checks if port is already in use before starting
- Displays warning with existing server URL if detected

**Files Modified:**
- `server/main.py`

---

### 2. Batch Upload Blocking/Freezing
**Problem:** Uploading 27+ files simultaneously caused the application to freeze.

**Solution:**
- Created new `task_queue.py` module with `BatchUploadQueue` class
- Implements concurrent upload control (max 3 simultaneous uploads by default)
- Rate limiting between requests (100ms minimum delay)
- Background thread processing with progress tracking
- Proper cancellation support

**Files Created:**
- `client/utils/task_queue.py` - Thread pool and queue management
- `client/ui/dialogs/batch_upload_dialog.py` - Updated to use new queue system

**Files Modified:**
- `client/ui/dialogs/batch_upload_dialog.py`
- `client/ui/controllers/file_operations.py`

---

### 3. Server-Side Processing Queue
**Problem:** Server overload during bulk PDF processing (OCR, indexing).

**Solution:**
- Created server-side `ProcessingQueue` with priority support
- Limits concurrent PDF processing to 2 tasks (configurable)
- Async processing with callback support
- Graceful fallback to synchronous processing if queue is full

**Files Created:**
- `server/services/task_queue.py` - Server-side task queue

**Files Modified:**
- `server/services/pdf_processor.py` - Added async processing support
- `server/services/document_service.py` - Uses async processing
- `server/main.py` - Initializes processing queue on startup

---

### 4. Database Connection Optimization
**Problem:** SQLite database contention during concurrent operations.

**Solution:**
- Enabled WAL (Write-Ahead Logging) mode for better concurrent access
- Increased cache size to 10MB
- Added connection event listeners for optimal SQLite settings
- Used `StaticPool` for SQLite connection management

**Files Modified:**
- `server/database.py`

---

### 5. Rate Limiting Middleware
**Problem:** No protection against request floods during bulk operations.

**Solution:**
- Created `RateLimitMiddleware` with sliding window algorithm
- Default: 100 requests per 60 seconds per IP
- Exempts health check and documentation endpoints
- Returns proper 429 status with retry-after header

**Files Created:**
- `server/utils/rate_limiter.py`

**Files Modified:**
- `server/main.py` - Added middleware to application

---

### 6. Health Check Endpoint
**Problem:** No way to monitor server status or queue health.

**Solution:**
- Added `/health` endpoint returning:
  - Overall status (healthy/degraded)
  - Database connection status
  - Processing queue status (active tasks, queue size)

**Files Modified:**
- `server/routers/documents.py`

---

### 7. Client-Side Server Health Check
**Problem:** Client couldn't detect server overload before starting bulk operations.

**Solution:**
- Added `check_health()` and `is_server_available()` methods to API base
- Batch upload dialog now checks server health before starting
- Prevents starting uploads if server is unavailable

**Files Modified:**
- `client/api/base.py`
- `client/ui/dialogs/batch_upload_dialog.py`

---

### 8. Batch Upload Error Tracking (100+ files → 75 uploaded)
**Problem:** When uploading 100+ files, only ~75 succeeded with no explanation.

**Solution:**
- Added comprehensive error tracking in `BatchUploadQueue`
- Each failed upload is logged with specific error message
- Upload summary shows exactly which files failed and why
- Proper cleanup of temporary encrypted files
- Retry logic with exponential backoff (up to 3 attempts)

**Files Modified:**
- `client/utils/task_queue.py` - Added `_successful_uploads` and `_failed_uploads` tracking
- `client/ui/dialogs/batch_upload_dialog.py` - Shows detailed error summary

---

### 9. Auto-Tags Language Issue (English tags in Polish UI)
**Problem:** Auto-generated tags were always in English regardless of application language.

**Solution:**
- Fixed locale detection in tag analysis
- `TagInputWidget` now properly uses locale from `Translator`
- Batch upload dialog uses correct locale for tag generation
- Tag dictionary lookup respects locale priority: `locale > en > id`
- Added `set_locale()` method for dynamic locale changes

**Files Modified:**
- `client/widgets/tag_input.py` - Added `set_locale()` method, improved locale handling
- `client/ui/dialogs/batch_upload_dialog.py` - Uses `Translator.get_locale()`
- `client/workers/tag_worker.py` - Default locale parameter, better comments
- `client/ui/components/document_form.py` - Already correct, verified

---

### 10. Files Not Opening After Tag Assignment
**Problem:** After assigning tags to files, documents stopped opening entirely.

**Solution:**
- Fixed document loading order in preview panel
- Document content now loads BEFORE showing cached preview
- Better error handling in `ModernPDFViewer.load_document()`
- Proper cleanup of previous document before loading new one
- Explicit error messages when document loading fails
- Handles encrypted documents and empty documents gracefully

**Files Modified:**
- `client/ui/preview_panel.py` - Fixed loading order, better error handling
- `client/widgets/modern_pdf_viewer.py` - Improved error messages, proper cleanup

---

## Architecture Overview

### Client-Side Upload Flow
```
User selects files → BatchUploadDialog
                   ↓
        Check server health
                   ↓
        Create upload queue (max 3 workers)
                   ↓
        For each file:
          - Encrypt PDF
          - Auto-generate tags
          - Submit to queue
                   ↓
        Queue processes with rate limiting
                   ↓
        Progress updates → UI
```

### Server-Side Processing Flow
```
Upload request → DocumentService
              ↓
        Save to database
              ↓
        Submit to ProcessingQueue (max 2 workers)
              ↓
        Background processing:
          - PDF text extraction
          - OCR (if enabled)
          - Index creation
              ↓
        Callback → Update database
```

---

## Configuration

### Client-Side Tuning
In `client/utils/task_queue.py`:
```python
BatchUploadQueue(api, max_workers=3, rate_limit=3)
```

### Server-Side Tuning
In `server/main.py`:
```python
init_pdf_processor(max_workers=2)
```

In `server/utils/rate_limiter.py`:
```python
RateLimitMiddleware(max_requests=100, window_seconds=60)
```

### Database Tuning
In `server/database.py`:
```python
PRAGMA cache_size=10000  # 10MB cache
PRAGMA journal_mode=WAL  # Better concurrency
```

---

## Testing Recommendations

1. **Bulk Upload Test:**
   - Upload 50+ PDF files simultaneously
   - Verify UI remains responsive
   - Check progress updates are smooth
   - Test cancellation during upload

2. **Server Load Test:**
   - Start server while another instance is running
   - Verify warning message appears
   - Check health endpoint during load

3. **Rate Limiting Test:**
   - Send 100+ rapid requests
   - Verify 429 responses after limit
   - Check retry-after header

4. **Database Concurrency:**
   - Multiple users uploading simultaneously
   - Verify no database locks
   - Check WAL file creation

---

## Future Improvements

1. **Distributed Queue:** Consider Redis/RQ for production deployments
2. **Progressive Upload:** Chunk large files (>50MB) for resumable uploads
3. **Client-Side Caching:** Cache document metadata to reduce server load
4. **WebSocket Updates:** Real-time progress updates instead of polling
5. **Adaptive Rate Limiting:** Adjust limits based on server load

---

## Migration Notes

- No database schema changes required
- Existing uploads continue to work
- New queue system is backward compatible
- Old `BatchWorker` class removed from batch_upload_dialog.py

---

## Troubleshooting

### Upload Queue Stuck
Check logs for task errors. Restart client if needed.

### Server Queue Full
Monitor `/health` endpoint. Queue accepts 100 tasks max.
Older tasks will be processed before new ones.

### Database Locked
Verify WAL mode is enabled. Check for long-running queries.

### Rate Limit Triggered
Wait for retry-after seconds. Consider increasing limits for trusted clients.
