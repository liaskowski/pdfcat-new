import re

filepath = r'D:\\PDF-lib\\pdfcat-new\\frontend\\src\\components\\SecurePdfViewer.vue'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add pageRotate options to viewerOptions toolbar
old_toolbar = '''      editorFreeTextButton: false,
      editorInkButton: false,
    }'''

new_toolbar = '''      editorFreeTextButton: false,
      editorInkButton: false,
      secondaryToolbarToggle: true,
      pageRotateCw: true,
      pageRotateCcw: true,
    }'''

content = content.replace(old_toolbar, new_toolbar)

# 2. Remove CSS hiding for MAIN toolbar but keep secondary toolbar hidden
old_css = '''/* Hide Open and Print buttons in VuePDFjs/PDF.js toolbar */
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

new_css = '''/* PDF.js toolbar visible via viewerOptions */
/* Toolbar buttons controlled by JS config */'''

content = content.replace(old_css, new_css)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print('Done!')
