import re

filepath = r'D:\\PDF-lib\\pdfcat-new\\frontend\\src\\components\\SecurePdfViewer.vue'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Find CSS section and add styles for rotate buttons
old_css = '''/* Show secondary toolbar for rotate buttons */
:deep(.pdf-app #secondaryToolbar),
:deep(.pdf-app .secondaryToolbar) {
  position: absolute;
  top: 0;
  left: 0;
  z-index: 100;
}

/* Hide everything in secondary toolbar except rotate buttons */
:deep(.pdf-app #secondaryToolbar button:not([data-l10n-id*="rotate"]),
:deep(.pdf-app .secondaryToolbar button:not([data-l10n-id*="rotate"])) {
  display: none !important;
}

/* Show only rotate buttons */
:deep(.pdf-app #secondaryToolbar button[data-l10n-id*="rotate"]),
:deep(.pdf-app .secondaryToolbar button[data-l10n-id*="rotate"]) {
  display: inline-flex !important;
}'''

new_css = '''/* Show secondary toolbar */
:deep(.pdf-app #secondaryToolbar),
:deep(.pdf-app .secondaryToolbar) {
  display: block !important;
  visibility: visible !important;
  position: absolute;
  right: 10px;
  top: 40px;
  z-index: 100;
  background: hsl(var(--background));
  border: 1px solid hsl(var(--border));
  border-radius: 0.5rem;
  padding: 0.5rem;
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
}

/* Hide ALL buttons in secondary toolbar */
:deep(.pdf-app #secondaryToolbar button),
:deep(.pdf-app .secondaryToolbar button) {
  display: none !important;
}

/* Show ONLY rotate buttons */
:deep(.pdf-app #secondaryToolbar button[data-l10n-id*="pageRotate"]),
:deep(.pdf-app .secondaryToolbar button[data-l10n-id*="pageRotate"]),
:deep(.pdf-app #secondaryToolbar button[data-l10n-id*="rotate"]),
:deep(.pdf-app .secondaryToolbar button[data-l10n-id*="rotate"]) {
  display: inline-flex !important;
  padding: 0.5rem 0.75rem;
  margin: 0.25rem;
  background: transparent;
  border: 1px solid hsl(var(--border));
  border-radius: 0.375rem;
  cursor: pointer;
}'''

content = content.replace(old_css, new_css)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print('Fixed CSS for rotate buttons!')
