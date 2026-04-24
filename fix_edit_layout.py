# Edit EditDialog.vue - split layout

filepath = r'D:\\PDF-lib\\pdfcat-new\\frontend\\src\\components\\EditDialog.vue'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace template structure
old_template = '''<template>
  <div v-if="isOpen" class="modal-overlay" @click.self="handleClose">
    <div class="modal-content">
      <div class="modal-header">
        <h2 class="modal-title">{{ t('edit.title') }}</h2>
        <button class="close-btn" @click="handleClose">
          <X class="h-4 w-4" />
        </button>
      </div>

      <div class="modal-body">
        <div class="doc-info">
          <p class="filename">{{ document?.filename }}</p>
        </div>

        <!-- PDF Preview -->
        <div v-if="previewUrl" class="preview-section">
          <div class="preview-header">
            <FileText class="h-4 w-4" />
            <span>Preview</span>
          </div>
          <div class="preview-container">
            <SimplePdfPreview :src="previewUrl" />
          </div>
        </div>

        <div v-if="isSaving || saveSuccess || saveError" class="save-status">'''

new_template = '''<template>
  <div v-if="isOpen" class="modal-overlay" @click.self="handleClose">
    <div class="modal-content modal-content-wide">
      <div class="modal-header">
        <h2 class="modal-title">{{ t('edit.title') }}</h2>
        <button class="close-btn" @click="handleClose">
          <X class="h-4 w-4" />
        </button>
      </div>

      <div class="modal-body modal-body-split">
        <!-- Left: PDF Preview -->
        <div class="preview-pane">
          <div class="preview-header">
            <FileText class="h-4 w-4" />
            <span>Preview</span>
          </div>
          <div class="preview-container">
            <SimplePdfPreview v-if="previewUrl" :src="previewUrl" />
            <div v-else class="no-preview">
              <p>No preview available</p>
            </div>
          </div>
        </div>

        <!-- Right: Form -->
        <div class="form-pane">
          <div class="doc-info">
            <p class="filename">{{ document?.filename }}</p>
          </div>

          <div v-if="isSaving || saveSuccess || saveError" class="save-status">'''

content = content.replace(old_template, new_template)

# Close the new divs at the end
old_footer = '''      <div class="modal-footer">
        <Button variant="outline" @click="handleClose" :disabled="isSaving">{{ t('common.cancel') }}</Button>
        <Button @click="handleSave" :disabled="isSaving">
          <Save class="h-4 w-4 mr-2" />
          {{ isSaving ? t('edit.saving') : t('edit.save_changes') }}
        </Button>
      </div>
    </div>
  </div>
</template>'''

new_footer = '''          <div class="modal-footer">
            <Button variant="outline" @click="handleClose" :disabled="isSaving">{{ t('common.cancel') }}</Button>
            <Button @click="handleSave" :disabled="isSaving">
              <Save class="h-4 w-4 mr-2" />
              {{ isSaving ? t('edit.saving') : t('edit.save_changes') }}
            </Button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>'''

content = content.replace(old_footer, new_footer)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print('EditDialog template updated!')
