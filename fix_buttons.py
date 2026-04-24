import re

filepath = r'D:\\PDF-lib\\pdfcat-new\\frontend\\src\\components\\SecurePdfViewer.vue'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Remove buttons that are directly after VuePDFjs without parent div
pattern = r'''      <!-- Custom Toolbar -->
        <button @click="handleRotate".*?>
          <RotateCw class="h-4 w-4".*?/>
        </button>
        <div class="toolbar-divider"></div>
        <button @click="prevPage".*?>
          <ChevronLeft class="h-4 w-4" />
        </button>
        <span class="page-info">\{\{ currentPage \}\} / \{\{ totalPagesCount \}\}</span>
        <button @click="nextPage".*?>
          <ChevronRight class="h-4 w-4" />
        </button>
        <div class="toolbar-divider"></div>
        <button @click="handleReload".*?>
          <RotateCw class="h-4 w-4" />
        </button>
      </div>'''

# Use simpler pattern - remove from <!-- Custom Toolbar --> to closing </div>
pattern2 = r'      <!-- Custom Toolbar -->\s*<button.*?RotateCw.*?</button>\s*<div class="toolbar-divider"></div>\s*<button.*?prevPage.*?</button>\s*<span class="page-info">.*?</span>\s*<button.*?nextPage.*?</button>\s*<div class="toolbar-divider"></div>\s*<button.*?handleReload.*?</button>\s*</div>'

content = re.sub(pattern2, '    </div>', content, flags=re.DOTALL)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print('Fixed!')
