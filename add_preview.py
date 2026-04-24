# Add PDF preview to UploadDialog and EditDialog

# ============ UPLOAD DIALOG ============
filepath = r'D:\\PDF-lib\\pdfcat-new\\frontend\\src\\components\\UploadDialog.vue'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Import SecurePdfViewer
old_imports = "import { X, Upload, Loader2, CheckCircle2, AlertCircle, FileText } from 'lucide-vue-next'\nimport { Button } from '@/components/ui/button'\nimport { Input } from '@/components/ui/input'"
new_imports = "import { X, Upload, Loader2, CheckCircle2, AlertCircle, FileText } from 'lucide-vue-next'\nimport { Button } from '@/components/ui/button'\nimport { Input } from '@/components/ui/input'\nimport SecurePdfViewer from '@/components/SecurePdfViewer.vue'"
content = content.replace(old_imports, new_imports)

# 2. Add previewUrl computed
old_computed = "const isOpen = computed({\n  get: () => props.open,\n  set: (value) => emit('update:open', value)\n})"
new_computed = "const previewUrl = computed(() => {\n  if (selectedFiles.value.length === 1) {\n    return URL.createObjectURL(selectedFiles.value[0])\n  }\n  return null\n})\n\nconst isOpen = computed({\n  get: () => props.open,\n  set: (value) => emit('update:open', value)\n})"
content = content.replace(old_computed, new_computed)

# 3. Add preview section in template (after drop-zone, before file-list)
old_template = "        <!-- File list for batch uploads -->\n        <div v-if=\"selectedFiles.length > 1\" class=\"file-list\">"
new_template = "        <!-- PDF Preview (single file) -->\n        <div v-if=\"previewUrl\" class=\"preview-section\">\n          <div class=\"preview-header\">\n            <FileText class=\"h-4 w-4\" />\n            <span>Preview</span>\n          </div>\n          <div class=\"preview-container\">\n            <SecurePdfViewer :src=\"previewUrl\" :visible=\"true\" />\n          </div>\n        </div>\n\n        <!-- File list for batch uploads -->\n        <div v-if=\"selectedFiles.length > 1\" class=\"file-list\">"
content = content.replace(old_template, new_template)

# 4. Add CSS for preview
old_css = ".file-item-remove:hover {\n  background-color: hsl(var(--destructive) / 0.1);\n  color: hsl(var(--destructive));\n}"
new_css = ".file-item-remove:hover {\n  background-color: hsl(var(--destructive) / 0.1);\n  color: hsl(var(--destructive));\n}\n\n.preview-section {\n  border: 1px solid hsl(var(--border));\n  border-radius: 0.5rem;\n  overflow: hidden;\n  background-color: hsl(var(--background));\n}\n\n.preview-header {\n  display: flex;\n  align-items: center;\n  gap: 0.5rem;\n  padding: 0.75rem 1rem;\n  border-bottom: 1px solid hsl(var(--border));\n  background-color: hsl(var(--muted));\n  font-size: 0.875rem;\n  font-weight: 500;\n  color: hsl(var(--foreground));\n}\n\n.preview-container {\n  height: 400px;\n  overflow: hidden;\n}"
content = content.replace(old_css, new_css)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print('UploadDialog updated!')

# ============ EDIT DIALOG ============
filepath = r'D:\\PDF-lib\\pdfcat-new\\frontend\\src\\components\\EditDialog.vue'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Import SecurePdfViewer + FileText
old_imports = "import { X, Save, Loader2, CheckCircle2, AlertCircle } from 'lucide-vue-next'\nimport { Button } from '@/components/ui/button'\nimport { Input } from '@/components/ui/input'"
new_imports = "import { X, Save, Loader2, CheckCircle2, AlertCircle, FileText } from 'lucide-vue-next'\nimport { Button } from '@/components/ui/button'\nimport { Input } from '@/components/ui/input'\nimport SecurePdfViewer from '@/components/SecurePdfViewer.vue'"
content = content.replace(old_imports, new_imports)

# 2. Add previewUrl computed
old_computed = "const isOpen = computed({\n  get: () => props.open,\n  set: (value) => emit('update:open', value)\n})"
new_computed = "const previewUrl = computed(() => {\n  if (props.document?.id) {\n    return `${docStore.apiBaseUrl}/documents/${props.document.id}/file?token=${docStore.token}`\n  }\n  return null\n})\n\nconst isOpen = computed({\n  get: () => props.open,\n  set: (value) => emit('update:open', value)\n})"
content = content.replace(old_computed, new_computed)

# 3. Add preview section in template (after doc-info)
old_template = "        <div class=\"doc-info\">\n          <p class=\"filename\">{{ document?.filename }}</p>\n        </div>\n\n        <div v-if=\"isSaving || saveSuccess || saveError\" class=\"save-status\">"
new_template = "        <div class=\"doc-info\">\n          <p class=\"filename\">{{ document?.filename }}</p>\n        </div>\n\n        <!-- PDF Preview -->\n        <div v-if=\"previewUrl\" class=\"preview-section\">\n          <div class=\"preview-header\">\n            <FileText class=\"h-4 w-4\" />\n            <span>Preview</span>\n          </div>\n          <div class=\"preview-container\">\n            <SecurePdfViewer :src=\"previewUrl\" :visible=\"true\" />\n          </div>\n        </div>\n\n        <div v-if=\"isSaving || saveSuccess || saveError\" class=\"save-status\">"
content = content.replace(old_template, new_template)

# 4. Add CSS for preview
old_css = ".filename {\n  font-size: 0.875rem;\n  color: hsl(var(--muted-foreground));\n  margin: 0;\n  font-family: monospace;\n  word-break: break-all;\n}"
new_css = ".filename {\n  font-size: 0.875rem;\n  color: hsl(var(--muted-foreground));\n  margin: 0;\n  font-family: monospace;\n  word-break: break-all;\n}\n\n.preview-section {\n  border: 1px solid hsl(var(--border));\n  border-radius: 0.5rem;\n  overflow: hidden;\n  background-color: hsl(var(--background));\n}\n\n.preview-header {\n  display: flex;\n  align-items: center;\n  gap: 0.5rem;\n  padding: 0.75rem 1rem;\n  border-bottom: 1px solid hsl(var(--border));\n  background-color: hsl(var(--muted));\n  font-size: 0.875rem;\n  font-weight: 500;\n  color: hsl(var(--foreground));\n}\n\n.preview-container {\n  height: 400px;\n  overflow: hidden;\n}"
content = content.replace(old_css, new_css)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print('EditDialog updated!')
print('Done!')
