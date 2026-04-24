with open(r'D:\\PDF-lib\\pdfcat-new\\frontend\\src\\components\\SecurePdfViewer.vue', 'r', encoding='utf-8') as f:
    content = f.read()

# Find and remove the buttons block after VuePDFjs
old_block = '''      <!-- Custom Toolbar -->
        <button @click="handleRotate" :title="t('viewer.rotate') || 'Rotate'">
          <RotateCw class="h-4 w-4" :style="{ transform: `rotate(${rotation}deg)` }" />
        </button>
        <div class="toolbar-divider"></div>
        <button @click="prevPage" :disabled="currentPage <= 1" :title="t('viewer.prev_page') || 'Previous Page'">
          <ChevronLeft class="h-4 w-4" />
        </button>
        <span class="page-info">{{ currentPage }} / {{ totalPagesCount }}</span>
        <button @click="nextPage" :disabled="currentPage >= totalPagesCount" :title="t('viewer.next_page') || 'Next Page'">
          <ChevronRight class="h-4 w-4" />
        </button>
        <div class="toolbar-divider"></div>
        <button @click="handleReload" title="Reload">
          <RotateCw class="h-4 w-4" />
        </button>
      </div>'''

new_block = '    </div>'

content = content.replace(old_block, new_block)

with open(r'D:\\PDF-lib\\pdfcat-new\\frontend\\src\\components\\SecurePdfViewer.vue', 'w', encoding='utf-8') as f:
    f.write(content)

print('Done!')
