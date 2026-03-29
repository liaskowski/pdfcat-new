# Search Bug Fix

## Problem Description

**Issue:** When searching for text from document content, the search results were empty (FileGrid showed no results), even though:
- Search suggestions worked (indicating documents were indexed on server)
- Server returned search results
- Documents were visible when browsing normally

**Date Identified:** 2026-03-15

---

## Root Cause Analysis

### The Bug

The search functionality had a **double-filtering problem**:

1. **Server-side search** (`/search` endpoint):
   - Correctly searched `DocumentIndex.content_text` 
   - Returned documents matching the search query by title OR content
   - Results were correct

2. **Client-side re-filtering** (`SearchHandler._on_search_finished`):
   ```python
   # OLD CODE - BUGGY
   for d in documents:
       cached_data = self._cache.get(d.id, {})
       
       # Check if query matches title or LOCAL cache content
       title_match = query_lower in d.title.lower()
       content_match = query_lower in cached_data.get("content", "").lower()  # ❌ EMPTY!
       match = title_match or content_match
       
       if query_lower and not match:
           continue  # ❌ Filters out server results!
   ```

**The Problem:** 
- Local cache (`self._cache`) was empty for documents not yet indexed locally
- Background indexing (`IndexingWorker`) runs AFTER search results are displayed
- All documents found by content (not title) were filtered out on client side
- Result: Empty FileGrid even though server returned results

### Why Suggestions Worked

Search suggestions use a different endpoint (`/suggestions`) that directly queries the server without client-side filtering:

```python
# server/routers/documents.py - get_suggestions
docs_query = (
    db.query(DocumentIndex.content_text)
    .join(Document)
    .filter(...)
    .filter(DocumentIndex.content_text.ilike(search_pattern))
    .limit(20)
)
```

---

## Solution

### Fix Applied

**File:** `client/ui/controllers/search_handler.py`

**Change:** Trust server search results and only apply category/file_type/tag filters on client side.

```python
# NEW CODE - FIXED
def _on_search_finished(self, documents, query):
    query_lower = query.lower() if query else ""

    # Update local cache with documents from server
    # Server already performed content search, so we trust its results
    for d in documents:
        if d.id not in self._cache:
            self._cache[d.id] = {"title": d.title, "content": d.content or ""}
        else:
            self._cache[d.id]["title"] = d.title
            if d.content:
                self._cache[d.id]["content"] = d.content

    category_id = self.ui.search_bar.category_id()
    file_type_id = self.ui.search_bar.file_type_id()

    filtered = []
    for d in documents:
        # ✅ Server already searched by content/title, trust its results
        # Only apply category/file_type filters
        
        if category_id is not None and (not d.category or d.category.id != category_id):
            continue
        if file_type_id is not None and (not d.file_type or d.file_type.id != file_type_id):
            continue

        # Only apply tag filter on client side (hashtag search)
        if query_lower.startswith("#") and len(query_lower) > 1:
            tag_to_find = query_lower[1:]
            if not (d.tags and tag_to_find in d.tags.lower()):
                continue

        filtered.append(d)

    # Display results
    pdf_icon = self.view._make_pdf_icon(64) if hasattr(self.view, '_make_pdf_icon') else None
    self.ui.file_grid.rebuild_with_files(filtered, pdf_icon)
    
    # Background indexing continues as before
    # ...
```

### Key Changes

| Before | After |
|--------|-------|
| Client re-checked title AND content | Client trusts server search results |
| Empty cache caused filtering | Cache is updated but not used for filtering |
| Hashtag search mixed with text search | Hashtag search handled separately |
| All filters applied together | Only category/file_type/tag filters applied |

---

## Test Coverage

### New Tests (`tests/test_search_fix.py`)

| Test | Purpose | Status |
|------|---------|--------|
| `test_on_search_finished_with_empty_cache` | Results display even with empty cache | ✅ Pass |
| `test_on_search_finished_with_content_search` | Content search results trusted | ✅ Pass |
| `test_on_search_finished_category_filter` | Category filter works | ✅ Pass |
| `test_on_search_finished_file_type_filter` | File type filter works | ✅ Pass |
| `test_on_search_finished_hashtag_filter` | Hashtag search works | ✅ Pass |
| `test_on_search_finished_updates_cache` | Cache is updated | ✅ Pass |
| `test_on_search_finished_mixed_filters` | Combined filters work | ✅ Pass |

### Running Tests

```bash
# Run search fix tests
python -m unittest tests.test_search_fix -v

# Run all tests
python run_batch_tests.py --unit
```

---

## Impact

### Before Fix

| Scenario | Result |
|----------|--------|
| Search by title | ✅ Works |
| Search by content (indexed locally) | ✅ Works |
| Search by content (not indexed) | ❌ **Empty results** |
| Hashtag search | ✅ Works |
| Category filter | ✅ Works |

### After Fix

| Scenario | Result |
|----------|--------|
| Search by title | ✅ Works |
| Search by content (indexed locally) | ✅ Works |
| Search by content (not indexed) | ✅ **Works now!** |
| Hashtag search | ✅ Works |
| Category filter | ✅ Works |

---

## Performance Considerations

### Server Load

- **No change:** Server already performed full-text search
- Client now trusts server results instead of re-filtering

### Network Traffic

- **No change:** Same documents transferred

### Client Performance

- **Improved:** Less client-side filtering logic
- **Faster:** Documents displayed immediately without waiting for cache check

### Background Indexing

- **Unchanged:** `IndexingWorker` still runs in background
- **Purpose:** Now only for offline search optimization (future feature)

---

## Future Improvements

### 1. Offline Search

With proper local indexing, offline search could work:

```python
# Future: If offline, use local cache
if not self.api.is_online():
    # Search local cache only
    for doc_id, cached in self._cache.items():
        if query_lower in cached.get("content", "").lower():
            # ... 
```

### 2. Search Result Highlighting

Show which field matched:

```python
# Future: Include match info in UI
for d in documents:
    match_type = "title" if query_lower in d.title.lower() else "content"
    # Display icon/badge showing match type
```

### 3. Search Result Ranking

Sort by relevance:

```python
# Future: Score-based ranking
scored_docs = []
for d in documents:
    score = 0
    if query_lower in d.title.lower():
        score += 10  # Title match is more relevant
    if query_lower in cached_data.get("content", "").lower():
        score += 1   # Content match is less relevant
    scored_docs.append((d, score))

# Sort by score
scored_docs.sort(key=lambda x: x[1], reverse=True)
```

---

## Related Files

- `client/ui/controllers/search_handler.py` - **Fixed**
- `client/ui/file_grid.py` - Displays search results
- `client/ui/search_bar.py` - Search input and filters
- `server/routers/documents.py` - Server search endpoint
- `tests/test_search_fix.py` - **New tests**

---

## Verification

To verify the fix works:

1. **Start the application:**
   ```bash
   python -m client.main
   ```

2. **Upload a document** with searchable content (e.g., "confidential report 2026")

3. **Wait for server indexing** (check server logs for OCR/indexing complete)

4. **Search for content text** (not title):
   - Enter "confidential" in search bar
   - Press Enter

5. **Expected result:** Document should appear in FileGrid

6. **Before fix:** FileGrid would be empty

---

**Fix Status:** ✅ Complete  
**Tests:** ✅ 7/7 Passing  
**Verified:** Manual testing recommended
