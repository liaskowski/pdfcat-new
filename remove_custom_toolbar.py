import re

filepath = r'D:\\PDF-lib\\pdfcat-new\\frontend\\src\\components\\SecurePdfViewer.vue'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Remove custom-toolbar HTML block
pattern_html = r'\s*<div v-if="!renderError" class="custom-toolbar">.*?</div>'
content = re.sub(pattern_html, '', content, flags=re.DOTALL)

# 2. Remove custom-toolbar CSS block
pattern_css = r'\.custom-toolbar\s*\{[^}]+\}\s*'
content = re.sub(pattern_css, '', content, flags=re.DOTALL)

# 3. Remove any remaining custom-toolbar related CSS
content = re.sub(r'\.custom-toolbar[^\{]*\{[^}]+\}\s*', '', content, flags=re.DOTALL)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print('Custom toolbar removed!')
