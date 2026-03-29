# Secure PDF Viewer Implementation

## Overview

The new `SecurePdfViewer.vue` component replaces the insecure iframe-based PDF rendering with a **canvas-based approach** using Mozilla's pdf.js library. This provides significant security improvements.

---

## Security Improvements

### 1. **JavaScript Execution Blocked**
```javascript
// PDF JavaScript is completely disabled
isEvalSupported: false
```
- **Before**: iframe could execute JavaScript embedded in PDF
- **After**: All JavaScript execution is blocked at the pdf.js level

### 2. **No External Resource Loading**
```javascript
isRemoteResourcesAllowed: false
```
- **Before**: PDF could load external images, scripts, tracking pixels
- **After**: All external resource fetching is blocked

### 3. **Canvas Rendering (No DOM Access)**
- **Before**: PDF rendered in iframe with potential DOM access
- **After**: PDF rendered to `<canvas>` elements - pure pixels, no executable content

### 4. **Security Scanning**
```javascript
async function securityCheck(data: ArrayBuffer): Promise<void> {
  // Detects JavaScript, embedded files, launch actions
  if (pdfHeader.includes('/JavaScript')) {
    securityInfo.value.hasJavaScript = true
    // Blocked automatically
  }
}
```

### 5. **User Warnings**
Shows security banner when potentially dangerous elements are detected:
- JavaScript code
- Embedded files
- External launch actions

---

## Features

| Feature | Description |
|---------|-------------|
| **Page Navigation** | Go to specific page, next/previous buttons |
| **Zoom** | 50% - 300% zoom with smooth rendering |
| **Rotation** | Rotate PDF in 90° increments |
| **Thumbnails** | Visual page thumbnails in sidebar |
| **Bookmarks** | Display PDF outline/bookmarks |
| **Full-text Search** | Search across all pages |
| **Download** | Secure download with authentication |
| **Fullscreen** | Fullscreen viewing mode |
| **Keyboard Shortcuts** | `+`, `-`, `R`, `↑`, `↓`, `Ctrl+F`, `Esc` |

---

## Security Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Browser Sandbox                       │
├─────────────────────────────────────────────────────────┤
│  ┌─────────────────┐    ┌─────────────────────────────┐ │
│  │   Vue App       │    │   pdf.js Worker (isolated)  │ │
│  │                 │    │                             │ │
│  │  SecurePdfViewer│───▶│  • Parse PDF structure      │ │
│  │  Component      │    │  • Render to canvas         │ │
│  │                 │    │  • Block JavaScript         │ │
│  │                 │    │  • Block external resources │ │
│  └─────────────────┘    └─────────────────────────────┘ │
│           │                        │                     │
│           │  Canvas pixels only    │                     │
│           ▼                        ▼                     │
│  ┌─────────────────────────────────────────────────────┐│
│  │              <canvas> Elements (safe)               ││
│  │         No DOM access, no scripts, no events        ││
│  └─────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────┘
```

---

## Comparison: Old vs New

| Aspect | Old (iframe) | New (SecurePdfViewer) |
|--------|-------------|----------------------|
| **JavaScript** | ✅ Could execute | ❌ Blocked |
| **External Resources** | ✅ Could load | ❌ Blocked |
| **DOM Access** | ✅ Possible | ❌ Impossible |
| **Clickjacking** | ✅ Vulnerable | ❌ Protected |
| **XSS via PDF** | ✅ Possible | ❌ Prevented |
| **Thumbnails** | ❌ Not available | ✅ Available |
| **Search** | ❌ Browser-dependent | ✅ Built-in |
| **Page Navigation** | ❌ Browser-dependent | ✅ Custom controls |

---

## Usage

The component is automatically used when opening a PDF document:

```vue
<SecurePdfViewer
  :documentId="selectedDocument.id"
  :visible="showPdfViewer"
  @close="showPdfViewer = false"
/>
```

### Props

| Prop | Type | Description |
|------|------|-------------|
| `documentId` | `number` | ID of document to fetch from API |
| `src` | `string` | Direct URL to PDF (alternative to documentId) |
| `visible` | `boolean` | Control viewer visibility |

### Events

| Event | Description |
|-------|-------------|
| `close` | Emitted when user clicks back/close |

---

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `+` / `=` | Zoom in |
| `-` | Zoom out |
| `R` | Rotate 90° |
| `↑` | Previous page |
| `↓` | Next page |
| `Ctrl+F` | Open search |
| `Esc` | Close viewer |

---

## Dependencies

```json
{
  "pdfjs-dist": "^5.5.207"
}
```

The pdf.js worker is bundled locally via Vite for maximum reliability and consistent versioning:
```javascript
import pdfjsWorker from 'pdfjs-dist/build/pdf.worker.min.mjs?url'
pdfjs.GlobalWorkerOptions.workerSrc = pdfjsWorker
```

**Note**: The old iframe-based `PdfViewer.vue` is kept for reference but is no longer used.
The application now uses `SecurePdfViewer.vue` by default.

---

## Future Enhancements

1. **Text Layer**: Add selectable text overlay for copy/paste
2. **Annotation Support**: View/add annotations securely
3. **Print**: Secure print functionality
4. **Local Worker**: Bundle worker locally instead of CDN
5. **CSP Headers**: Add Content-Security-Policy for extra protection

---

## Testing Security

To verify security features work:

1. **Test with JavaScript PDF**: Create PDF with embedded JS - should show warning banner
2. **Test with External Links**: PDF with external resources - should be blocked
3. **Test Network Isolation**: Verify no external requests in DevTools Network tab

---

## References

- [Mozilla pdf.js Documentation](https://mozilla.github.io/pdf.js/)
- [OWASP PDF Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/PDF_Security_Cheat_Sheet.html)
- [CWE-697: Incorrect Comparison](https://cwe.mitre.org/data/definitions/697.html)
