# Auto-Tagging on Upload Feature

## Overview

Automatic document tagging during file upload in the client application. The system analyzes PDF content and generates relevant tags using the existing TagAnalyzer engine.

**Date Added:** 2026-03-15  
**Feature Type:** Enhancement to existing upload functionality

---

## Features

### Automatic Tag Generation During Upload

- **Batch Upload Dialog**: Auto-tags all files in batch upload
- **Drag-and-Drop**: Auto-tags files when dropped onto client
- **Regular Upload**: Existing single-file upload already has auto-tagging

### Tag Analysis Engine

Uses the existing `TagAnalyzer` class (`client/logic/tags_engine.py`):

- **Dictionary-based**: Uses `tag_dictionary.json` for tag matching
- **Multi-language**: Supports Russian, English, Polish tags
- **OCR Support**: Falls back to OCR if text extraction fails
- **2-page analysis**: Analyzes first 2 pages for accuracy

---

## How It Works

### Upload Flow with Auto-Tagging

```
1. User initiates upload (batch or drag-and-drop)
   ↓
2. UploadWorker/BatchWorker processes each file
   ↓
3. For each file:
   a. Extract text from first 2 pages
   b. If text < 50 chars → OCR
   c. Match text against tag dictionary
   d. Generate tag list
   ↓
4. Upload file with auto-generated tags
   ↓
5. Tags appear in document metadata
```

### Code Flow

#### Batch Upload (`client/ui/dialogs/batch_upload_dialog.py`)

```python
class BatchWorker(QThread):
    def __init__(self, api, files, metadata):
        self.tag_analyzer = TagAnalyzer()
    
    def run(self):
        for file_path in self.files:
            # Auto-tagging
            tags = self.tag_analyzer.analyze_file(file_path, locale="en")
            
            # Merge with manual tags
            if self.metadata.get('tags'):
                manual_tags = self.metadata['tags'].split(',')
                tags = list(set(tags + manual_tags))
            
            # Upload with tags
            self.api.upload_file(..., tags=",".join(tags))
```

#### Drag-and-Drop (`client/utils/workers.py`)

```python
class UploadWorker(QThread):
    def __init__(self, api, paths, ...):
        self.tag_analyzer = TagAnalyzer()
    
    def run(self):
        for fpath, pid in tasks:
            # Auto-tagging
            tags = self.tag_analyzer.analyze_file(fpath, locale="en")
            
            # Log tags
            if tags:
                self.log.emit(f"Auto-tags: {', '.join(tags)}")
            
            # Upload with tags
            self.api.upload_file(..., tags=",".join(tags))
```

---

## Usage

### Batch Upload

1. **Select multiple files** (File → Add PDF or Ctrl+A)
2. **Batch Upload Dialog opens**
3. **Optional**: Enter common metadata (category, manual tags)
4. **Click "Upload All"**
5. **Progress shown** with auto-tag logging
6. **Documents uploaded** with auto-generated tags

### Drag-and-Drop

1. **Drag files** from file explorer
2. **Drop onto client window**
3. **Upload starts automatically**
4. **Progress dialog shows** auto-tags for each file
5. **Documents uploaded** with auto-generated tags

### Single File Upload

1. **Drag single file** or use "Add PDF"
2. **Upload Dialog opens**
3. **Auto-tag analysis runs** in background
4. **Tags appear in tag field** (editable)
5. **Click "Save"** to upload with tags

---

## Tag Dictionary

### Location

`client/assets/configs/tag_dictionary.json`

### Format

```json
{
  "tags": [
    {
      "id": "invoice",
      "en": "Invoice",
      "ru": "Счёт",
      "pl": "Faktura",
      "markers": ["invoice", "factura", "счёт", "фактура"]
    },
    {
      "id": "contract",
      "en": "Contract",
      "ru": "Договор",
      "pl": "Umowa",
      "markers": ["contract", "agreement", "договор", "umowa"]
    }
  ]
}
```

### How Tags Are Matched

1. **Text extraction**: First 2 pages analyzed
2. **Marker matching**: Each tag has markers (keywords)
3. **Case-insensitive**: Matching ignores case
4. **Regex support**: Markers can be regex patterns
5. **Multi-language**: Tags matched in any language

---

## Performance

### Analysis Time

| File Type | Pages | Time |
|-----------|-------|------|
| Text PDF | 2 | <1s |
| Scanned PDF | 2 | 2-5s (OCR) |
| Mixed | 2 | 1-3s |

### Batch Upload

| Files | Total Time (avg) |
|-------|------------------|
| 10 | 15-30s |
| 50 | 1-3 min |
| 100 | 3-5 min |

**Note:** OCR significantly increases processing time.

---

## Configuration

### Tag Analyzer Settings

Located in `client/logic/tags_engine.py`:

```python
class TagAnalyzer:
    def __init__(self, dictionary_path=None):
        self.dictionary_path = dictionary_path  # Default: client/assets/configs/tag_dictionary.json
        self.tags_data = []
        self.load_dictionary()
    
    def analyze_file(self, file_source, locale="en", password=None):
        # Analyzes first 2 pages
        # Returns list of tags
```

### Customization

1. **Add custom tags**: Edit `tag_dictionary.json`
2. **Change locale**: Modify `locale` parameter in analyze_file()
3. **Adjust pages**: Change `range(2)` to analyze more/fewer pages

---

## Files Modified

### Client Side

| File | Changes |
|------|---------|
| `client/utils/workers.py` | Added TagAnalyzer to UploadWorker, auto-tag in run() |
| `client/ui/dialogs/batch_upload_dialog.py` | Added TagAnalyzer to BatchWorker, auto-tag in run() |
| `client/logic/tags_engine.py` | Existing (no changes) |
| `client/assets/configs/tag_dictionary.json` | Existing (user-editable) |

---

## Error Handling

### Tag Analysis Failures

- **Non-critical**: If tag analysis fails, upload continues without tags
- **Logged**: Errors printed to console
- **User notified**: Progress log shows analysis status

### Fallback Behavior

```python
try:
    tags = self.tag_analyzer.analyze_file(fpath, locale="en")
except Exception as tag_error:
    print(f"Tag analysis failed for {fpath}: {tag_error}")
    tags = []  # Continue without tags

# Upload proceeds regardless
self.api.upload_file(..., tags=",".join(tags))
```

---

## Testing

### Manual Testing

1. **Prepare test PDFs** with known content
2. **Upload via drag-and-drop**
3. **Check console output** for auto-tags
4. **Verify tags in document metadata**

### Example Test

```python
from client.logic.tags_engine import TagAnalyzer

analyzer = TagAnalyzer()
tags = analyzer.analyze_file("test_invoice.pdf", locale="en")
print(f"Auto-tags: {tags}")
# Expected: ['Invoice', 'Finance', 'Payment']
```

---

## Troubleshooting

### No Tags Generated

**Possible causes:**
1. Tag dictionary not loaded
2. Text not extracted (scanned without OCR)
3. No matching markers in dictionary

**Solutions:**
1. Check `tag_dictionary.json` exists
2. Ensure OCR is enabled for scanned documents
3. Add more markers to dictionary

### Wrong Tags

**Possible causes:**
1. Markers too generic
2. False positives in matching

**Solutions:**
1. Make markers more specific
2. Use regex patterns for precision
3. Add negative markers (future feature)

### Slow Upload

**Possible causes:**
1. OCR on all pages
2. Large number of files
3. Slow hardware

**Solutions:**
1. Reduce pages analyzed (edit tags_engine.py)
2. Disable OCR for text PDFs
3. Batch upload in smaller groups

---

## Future Improvements

- [ ] **Progress reporting**: Show tag analysis progress separately
- [ ] **Tag suggestions**: Show tags for user approval before upload
- [ ] **Machine learning**: Use ML-based tag suggestion
- [ ] **Custom dictionaries**: Per-user or per-folder tag dictionaries
- [ ] **Tag confidence**: Show confidence score for each tag
- [ ] **Batch tagging**: Re-tag existing documents

---

## Related Features

| Feature | Description |
|---------|-------------|
| **Manual Tags** | User can add/edit tags in upload dialog |
| **Tag Merging** | Manager can merge duplicate tags |
| **Tag Search** | Search documents by hashtag (#tag) |
| **Dictionary Editor** | Manager can edit tag dictionary |

---

## API Reference

### TagAnalyzer

```python
class TagAnalyzer:
    def __init__(self, dictionary_path: str = None)
    def load_dictionary(self) -> None
    def analyze_file(self, file_source: str | bytes, locale: str = "en", password: str = None) -> list[str]
    def suggest_tags_by_similarity(self, new_doc_title: str, existing_docs: list, threshold: float = 0.8) -> list[str]
```

### UploadWorker

```python
class UploadWorker(QThread):
    def __init__(self, api, paths: list[str], target_folder_id: int = None, is_public: bool = False)
    # Added:
    self.tag_analyzer = TagAnalyzer()
```

### BatchWorker

```python
class BatchWorker(QThread):
    def __init__(self, api, files, metadata)
    # Added:
    self.tag_analyzer = TagAnalyzer()
```

---

**Status:** ✅ Complete  
**Version:** 1.0  
**Last Updated:** 2026-03-15
