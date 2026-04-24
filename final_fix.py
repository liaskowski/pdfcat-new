# Read the file
filepath = r'D:\\PDF-lib\\pdfcat-new\\frontend\\src\\components\\SecurePdfViewer.vue'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add secondaryToolbarToggle, pageRotateCw, pageRotateCcw
old_options = '''      editorFreeTextButton: false,
      editorInkButton: false,
    }'''
new_options = '''      editorFreeTextButton: false,
      editorInkButton: false,
      secondaryToolbarToggle: true,
      pageRotateCw: true,
      pageRotateCcw: true,
    }'''
content = content.replace(old_options, new_options)

# 2. Remove CSS that hides main toolbar
old_hide = '''/* Hide Open and Print buttons in VuePDFjs/PDF.js toolbar */
/* PDF.js uses these IDs for toolbar buttons */
:deep(.pdf-app #toolbarViewer #openFile),
:deep(.pdf-app #toolbarViewer #print),
:deep(.pdf-app .toolbarButton[aria-label*="Open"]),
:deep(.pdf-app .toolbarButton[aria-label*="Print"]),
:deep(.pdf-app .toolbarButton[data-l10n-id*="open"]),
:deep(.pdf-app .toolbarButton[data-l10n-id*="print"]) {
  display: none !important;
}

/* Hide entire toolbar globally */
:deep(.pdf-app .toolbar),
:deep(.pdf-app #toolbarViewer),
:deep(.pdf-app #toolbarContainer),
:deep(.pdf-app .toolbarContainer) {
  display: none !important;
}

/* Collapse the toolbar height so content shifts up */
:deep(.pdf-app) {
  --vue-pdfjs-toolbar-height: 0px !important;
}'''
new_hide = '''/* PDF.js toolbar buttons controlled by viewerOptions */
/* Toolbar visible, only Open/Print hidden via JS config */'''
content = content.replace(old_hide, new_hide)

# 3. Remove CSS that hides secondary toolbar (rotate buttons need it)
old_secondary = '''/* Also hide any secondary toolbar */
:deep(.pdf-app #secondaryToolbar),
:deep(.pdf-app .secondaryToolbar) {
  display: none !important;
}'''
new_secondary = '''/* Secondary toolbar visible - contains rotate buttons */
:deep(.pdf-app #secondaryToolbar),
:deep(.pdf-app .secondaryToolbar) {
  display: flex !important;
}'''
content = content.replace(old_secondary, new_secondary)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print('Done!')
