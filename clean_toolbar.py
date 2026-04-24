import re

with open(r'D:\PDF-lib\pdfcat-new\frontend\src\components\SecurePdfViewer.vue', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Remove custom-toolbar HTML div
old_html = '''      <div v-if="!renderError" class="custom-toolbar">
        <Button variant="ghost" size="sm" @click="handleRotate" title="Rotate">
          <RotateCw class="h-4 w-4" />
        </Button>
        <Button variant="ghost" size="sm" @click="zoomIn" title="Zoom In">
          <ZoomIn class="h-4 w-4" />
        </Button>
        <Button variant="ghost" size="sm" @click="zoomOut" title="Zoom Out">
          <ZoomOut class="h-4 w-4" />
        </Button>
        <span class="toolbar-separator"></span>
        <Button variant="ghost" size="sm" @click="handleDownload" title="Download" disabled>
          <Download class="h-4 w-4 opacity-50" />
        </Button>
      </div>'''

content = content.replace(old_html, '')

# 2. Remove custom-toolbar CSS styles
old_css = '''.custom-toolbar {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.375rem 0.75rem;
  background-color: hsl(var(--background));
  border-top: 1px solid hsl(var(--border));
}

.custom-toolbar button {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 2rem;
  height: 2rem;
  padding: 0;
  border: 1px solid hsl(var(--border));
  background: transparent;
  color: hsl(var(--foreground));
  border-radius: 0.25rem;
  cursor: pointer;
}

.custom-toolbar button:hover {
  background-color: hsl(var(--accent));
}

.custom-toolbar button:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.toolbar-separator {
  width: 1px;
  height: 1.25rem;
  background-color: hsl(var(--border));
  margin: 0 0.25rem;
}

'''

content = content.replace(old_css, '')

# 3. Check if there's still custom-toolbar
if 'custom-toolbar' in content:
    # Use regex to remove any remaining custom-toolbar elements
    content = re.sub(r'\s*<div[^>]*class="custom-toolbar"[^>]*>.*?</div>', '', content, flags=re.DOTALL)
    content = re.sub(r'\.custom-toolbar\s*\{[^}]+\}', '', content, flags=re.DOTALL)
    content = re.sub(r'\.toolbar-separator\s*\{[^}]+\}', '', content, flags=re.DOTALL)

with open(r'D:\PDF-lib\pdfcat-new\frontend\src\components\SecurePdfViewer.vue', 'w', encoding='utf-8') as f:
    f.write(content)

print('Done!')
