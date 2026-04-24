# Add split layout CSS to EditDialog

filepath = r'D:\\PDF-lib\\pdfcat-new\\frontend\\src\\components\\EditDialog.vue'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace modal-content style
old_modal_content = '''.modal-content {
  background-color: hsl(var(--background));
  border-radius: 0.5rem;
  width: 100%;
  max-width: 550px;
  max-height: 95vh;
  overflow-y: auto;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
}'''

new_modal_content = '''.modal-content {
  background-color: hsl(var(--background));
  border-radius: 0.5rem;
  width: 100%;
  max-width: 550px;
  max-height: 95vh;
  overflow-y: auto;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
}

.modal-content-wide {
  max-width: 1100px;
}'''

content = content.replace(old_modal_content, new_modal_content)

# Replace modal-body style
old_modal_body = '''.modal-body {
  padding: 1.25rem;
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}'''

new_modal_body = '''.modal-body {
  padding: 1.25rem;
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.modal-body-split {
  display: flex;
  gap: 1.5rem;
  padding: 0;
}

.preview-pane {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  border: 1px solid hsl(var(--border));
  border-radius: 0.5rem;
  overflow: hidden;
  background-color: hsl(var(--background));
}

.form-pane {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 1rem;
  padding: 0 1.25rem 1.25rem 1.25rem;
  overflow-y: auto;
  max-height: 70vh;
}'''

content = content.replace(old_modal_body, new_modal_body)

# Update preview-section to preview-pane styles
old_preview_section = '''.preview-section {
  border: 1px solid hsl(var(--border));
  border-radius: 0.5rem;
  overflow: hidden;
  background-color: hsl(var(--background));
}'''

new_preview_section = '''.preview-pane .preview-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1rem;
  border-bottom: 1px solid hsl(var(--border));
  background-color: hsl(var(--muted));
  font-size: 0.875rem;
  font-weight: 500;
  color: hsl(var(--foreground));
}

.preview-pane .preview-container {
  flex: 1;
  min-height: 500px;
  overflow: hidden;
  background-color: hsl(var(--background));
}

.no-preview {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: hsl(var(--muted-foreground));
  font-size: 0.875rem;
}'''

content = content.replace(old_preview_section, new_preview_section)

# Update modal-footer for form-pane
old_footer = '''.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
  padding: 1rem 1.25rem;
  border-top: 1px solid hsl(var(--border));
}'''

new_footer = '''.form-pane .modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
  padding-top: 1rem;
  border-top: 1px solid hsl(var(--border));
  margin-top: auto;
}'''

content = content.replace(old_footer, new_footer)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print('EditDialog CSS updated!')
