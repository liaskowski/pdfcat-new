# Auto-Tagging Feature (Manager)

## Overview

Automatic document tagging feature for existing documents in the database. Uses the **same TagAnalyzer engine** as the client application with `tag_dictionary.json`.

**Date Added:** 2026-03-15  
**Location:** Manager Application  
**Engine:** TagAnalyzer (client/logic/tags_engine.py)

---

## Key Features

### Unified Tag System

- **Same Engine**: Uses `TagAnalyzer` from client
- **Same Dictionary**: Uses `tag_dictionary.json`
- **Consistent Tags**: Manager and client generate identical tags
- **Multi-language**: Supports Russian, English, Polish tags

### How It Works

1. **Read Indexed Content**: Fetches text from `DocumentIndex` table
2. **Analyze Text**: Uses `TagAnalyzer.analyze_file_from_text()`
3. **Match Markers**: Compares text against tag dictionary markers
4. **Generate Tags**: Returns localized tag names
5. **Merge Tags**: Adds new tags to existing document tags
6. **Save**: Commits changes to database

---

## Usage

### In Manager Application

1. **Open Manager**:
   ```bash
   python -m manager.main
   ```

2. **Navigate to Auto-Tagging**:
   - Click "Auto-Tagging" in the left sidebar

3. **Start Auto-Tagging**:
   - Click "Start Auto-Tagging" button
   - Confirm the action
   - All documents will be analyzed

4. **View Results**:
   - Check server logs for progress
   - Tags appear on documents in client

---

## Technical Details

### Server API

**Endpoint:** `POST /api/v1/admin/auto-tag`

**Implementation:**
```python
@router.post("/auto-tag")
async def auto_tag_documents(
    background_tasks: BackgroundTasks,
    db: Session,
    current_user: User
):
    # Import TagAnalyzer from client
    from logic.tags_engine import TagAnalyzer
    
    tag_analyzer = TagAnalyzer()
    docs = db.query(Document).all()
    
    for doc in docs:
        # Get indexed text
        index = db.query(DocumentIndex).filter(
            DocumentIndex.document_id == doc.id
        ).first()
        
        # Analyze text (no file reading needed)
        tags = tag_analyzer.analyze_file_from_text(
            index.content_text, 
            locale="en"
        )
        
        # Merge with existing tags
        # ...
```

### New Method in TagAnalyzer

```python
def analyze_file_from_text(self, text: str, locale: str = "en") -> list[str]:
    """
    Analyze text content directly (without reading from file).
    Useful for re-tagging existing documents where text is already indexed.
    """
    found_tags = []
    for tag_info in self.tags_data:
        markers = tag_info.get("markers", [])
        for marker in markers:
            if re.search(marker, text, re.IGNORECASE | re.UNICODE):
                tag_name = tag_info.get(locale, ...)
                if tag_name not in found_tags:
                    found_tags.append(tag_name)
                break
    return found_tags
```

---

## Files Modified

### Server Side

| File | Changes |
|------|---------|
| `server/routers/admin.py` | Uses `TagAnalyzer` instead of `extract_keywords()` |
| `client/logic/tags_engine.py` | Added `analyze_file_from_text()` method |

### Manager Side

| File | Changes |
|------|---------|
| `manager/api_client/client.py` | `auto_tag()` method (existing) |
| `manager/ui/auto_tag.py` | UI widget (existing) |
| `manager/main.py` | Auto-Tagging tab (existing) |

---

## Comparison: Client vs Manager Auto-Tagging

| Feature | Client (Upload) | Manager (Re-tag) |
|---------|----------------|------------------|
| **When** | During upload | For existing docs |
| **Source** | PDF file | Indexed text |
| **Engine** | TagAnalyzer | TagAnalyzer |
| **Dictionary** | tag_dictionary.json | tag_dictionary.json |
| **Languages** | RU/EN/PL | RU/EN/PL |
| **OCR** | Yes (if needed) | No (text already indexed) |
| **Speed** | Slower (file read) | Faster (DB read) |

---

## Benefits

### Unified System

✅ **Same tags everywhere** - Client and Manager use identical logic  
✅ **Single dictionary** - Edit once, works everywhere  
✅ **Consistent behavior** - No confusion about tag generation

### Performance

✅ **Fast** - Reads from database, not files  
✅ **No OCR** - Text already extracted  
✅ **Background** - Doesn't block UI

### Maintenance

✅ **Single source** - TagAnalyzer in one place  
✅ **Easy updates** - Change dictionary, works everywhere  
✅ **Debuggable** - Same code path for all tagging

---

## Troubleshooting

### No Tags Generated

**Check:**
1. Tag dictionary exists: `client/assets/configs/tag_dictionary.json`
2. Documents have indexed content (run Reindex if needed)
3. Server logs show tag analysis

**Solution:**
```bash
# In Manager, run Reindex first
# Then run Auto-Tagging
```

### Wrong Tags

**Check:**
1. Tag dictionary markers
2. Language settings

**Solution:**
```json
// Edit tag_dictionary.json
{
  "tags": [
    {
      "id": "invoice",
      "en": "Invoice",
      "ru": "Счёт",
      "markers": ["invoice", "factura", "счёт"]
    }
  ]
}
```

---

## Testing

### Manual Test

1. **Upload document** without tags
2. **Run Reindex** (if needed)
3. **Open Manager** → Auto-Tagging
4. **Start Auto-Tagging**
5. **Check document** in client - tags should appear

### API Test

```bash
# Call auto-tag endpoint
curl -X POST http://localhost:8000/api/v1/admin/auto-tag \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"

# Response:
# {"message": "Auto-tagging started for X documents using tag dictionary."}
```

---

**Status:** ✅ Complete  
**Version:** 2.0 (Unified with Client)  
**Last Updated:** 2026-03-15

## Overview

Automatic document tagging feature that analyzes document content and generates relevant tags using keyword extraction.

**Date Added:** 2026-03-15  
**Location:** Manager Application

---

## Features

### Automatic Tag Generation

- Analyzes document text content using frequency-based keyword extraction
- Supports multiple languages: Russian, English, Polish
- Filters out common stop words automatically
- Runs as background task to avoid blocking
- Adds tags to all documents in one operation

### How It Works

1. **Content Analysis**: Extracts text from document index
2. **Keyword Extraction**: Identifies frequently occurring meaningful words
3. **Stop Word Filtering**: Removes common words (prepositions, articles, etc.)
4. **Tag Assignment**: Adds top keywords as document tags
5. **Preserve Existing**: Merges new tags with existing ones

---

## Usage

### In Manager Application

1. **Open Manager**:
   ```bash
   python -m manager.main
   ```

2. **Navigate to Auto-Tagging**:
   - Click "Auto-Tagging" in the left sidebar

3. **Start Auto-Tagging**:
   - Click "Start Auto-Tagging" button
   - Confirm the action in the dialog
   - Wait for completion (runs in background)

4. **View Results**:
   - Check the log output for progress
   - Status indicator shows: Ready → Running → Completed
   - Success message displays when done

### UI Components

| Component | Description |
|-----------|-------------|
| Status Label | Shows current operation status |
| Progress Bar | Indeterminate progress indicator |
| Log Output | Displays operation messages |
| Start Button | Initiates auto-tagging process |
| Info Panel | Shows usage tips |

---

## Technical Details

### Server API

**Endpoint:** `POST /api/v1/admin/auto-tag`

**Authentication:** Admin required

**Response:**
```json
{
  "message": "Auto-tagging started for X documents. Tags will be generated based on content analysis."
}
```

### Keyword Extraction Algorithm

```python
def extract_keywords(text: str, max_keywords: int = 10) -> list:
    # 1. Extract words (3+ characters)
    # 2. Filter stop words (RU/EN/PL)
    # 3. Count word frequencies
    # 4. Return top N keywords
```

### Stop Words

The following languages are supported with built-in stop word lists:

- **Russian** (100+ words)
- **English** (100+ words)
- **Polish** (50+ words)

Examples of filtered words:
- Russian: "и", "в", "не", "что", "он", "на"...
- English: "the", "and", "or", "but", "in", "on"...
- Polish: "i", "o", "a", "w", "z", "do"...

### Tag Format

Tags are stored as comma-separated values:
```
document1,keyword,analysis,report,2024
```

New tags are merged with existing:
- Existing: `important,work`
- New keywords: `analysis,report`
- Result: `important,work,analysis,report`

---

## Files Modified/Created

### Server Side

| File | Changes |
|------|---------|
| `server/routers/admin.py` | Added `/auto-tag` endpoint |
| `server/services/pdf_processor.py` | Added `extract_keywords()` function |

### Manager Side

| File | Changes |
|------|---------|
| `manager/api_client/client.py` | Added `auto_tag()` method |
| `manager/ui/auto_tag.py` | **New** - Auto-tag UI widget |
| `manager/main.py` | Added Auto-Tagging tab |

---

## Performance

### Processing Time

| Documents | Estimated Time |
|-----------|---------------|
| 10-50 | < 1 minute |
| 50-200 | 1-3 minutes |
| 200-500 | 3-10 minutes |
| 500+ | 10+ minutes |

### Resource Usage

- **CPU**: Moderate during keyword extraction
- **Memory**: Low (processes documents sequentially)
- **Database**: Updates tags field for each document
- **Network**: Single API call, background processing

---

## Best Practices

### When to Use

✅ **Good scenarios:**
- After bulk document upload
- When documents have no tags
- For organizing large document collections
- Periodic maintenance (monthly/quarterly)

❌ **Avoid when:**
- Documents already have good manual tags
- Only few documents need tagging
- During peak usage hours

### Tips

1. **Review Tags**: After auto-tagging, review and clean up tags
2. **Merge Duplicates**: Use "Tag Merging" tool for similar tags
3. **Run Off-Peak**: Schedule for low-usage periods
4. **Backup First**: Create backup before bulk operations

---

## Limitations

### Current Limitations

1. **No Progress Tracking**: Background task doesn't report individual document progress
2. **All-or-Nothing**: Processes all documents, cannot select subset
3. **Simple Algorithm**: Frequency-based, no semantic analysis
4. **No Undo**: Changes are permanent (use backup to restore)

### Future Improvements

- [ ] Progress reporting per document
- [ ] Selective document processing
- [ ] Machine learning-based keyword extraction
- [ ] Tag suggestions instead of auto-apply
- [ ] Undo/rollback functionality
- [ ] Schedule automatic tagging

---

## Troubleshooting

### Common Issues

**Issue:** Auto-tagging fails immediately  
**Solution:** Check server logs for errors, ensure documents are indexed

**Issue:** No tags generated  
**Solution:** Verify documents have text content in index (run reindex if needed)

**Issue:** Timeout error  
**Solution:** Increase API timeout in client, check server resources

**Issue:** Duplicate tags  
**Solution:** Use "Tag Merging" tool to consolidate similar tags

### Logs

Check server logs for detailed information:
```bash
# Server logs (check console or log file)
INFO: Auto-tagging started for 150 documents
INFO: Auto-tagging completed for 150 documents
```

---

## API Reference

### Manager API Client

```python
from manager.api_client import ManagerAPIClient

api = ManagerAPIClient("http://localhost:8000")
api.login("admin", "password")

# Trigger auto-tagging
message = api.auto_tag()
print(message)
# Output: "Auto-tagging started for 150 documents..."
```

### Server Endpoint

```python
# server/routers/admin.py
@router.post("/auto-tag")
async def auto_tag_documents(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    # Implementation details...
```

---

## Testing

### Manual Testing

1. Upload 5-10 documents without tags
2. Run reindex to ensure content is indexed
3. Open Manager → Auto-Tagging
4. Click "Start Auto-Tagging"
5. Verify tags appear on documents

### Automated Testing

```bash
# Run manager tests (if available)
python -m pytest tests/test_manager.py -v

# Test keyword extraction
python -c "from server.services.pdf_processor import extract_keywords; print(extract_keywords('test document analysis report', 5))"
```

---

## Security

### Access Control

- **Admin Only**: Only admin users can trigger auto-tagging
- **Authentication Required**: Valid JWT token needed
- **Background Processing**: Prevents timeout attacks

### Data Integrity

- **Transactional**: Changes committed to database atomically
- **Error Handling**: Failed documents don't stop entire process
- **Logging**: All operations logged for audit

---

## Related Features

| Feature | Description |
|---------|-------------|
| **Reindex** | Rebuild document text index |
| **Tag Merge** | Combine duplicate tags |
| **Search** | Find documents by tags |
| **Dictionary Editor** | Manage categories/types |

---

**Status:** ✅ Complete  
**Version:** 1.0  
**Last Updated:** 2026-03-15
