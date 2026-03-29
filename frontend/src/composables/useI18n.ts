import { ref } from 'vue'

const currentLocale = ref('en')

const messages: Record<string, any> = {
  en: {
    common: {
      cancel: 'Cancel',
      save: 'Save',
      delete: 'Delete',
      edit: 'Edit',
      download: 'Download',
      upload: 'Upload',
      search: 'Search...',
      loading: 'Loading...',
      error: 'Error',
      success: 'Success'
    },
    nav: {
      my_documents: 'My Documents',
      shared: 'Shared with me',
      community: 'Community',
      folders: 'Folders'
    },
    document: {
      title: 'Title',
      owner: 'Owner',
      size: 'Size',
      uploaded: 'Uploaded',
      type: 'Type',
      category: 'Category',
      tags: 'Tags',
      notes: 'Notes'
    }
  },
  ru: {
    common: {
      cancel: 'Отмена',
      save: 'Сохранить',
      delete: 'Удалить',
      edit: 'Изменить',
      download: 'Скачать',
      upload: 'Загрузить',
      search: 'Поиск...',
      loading: 'Загрузка...',
      error: 'Ошибка',
      success: 'Успешно'
    },
    nav: {
      my_documents: 'Мои документы',
      shared: 'Доступные мне',
      community: 'Общие',
      folders: 'Папки'
    },
    document: {
      title: 'Название',
      owner: 'Владелец',
      size: 'Размер',
      uploaded: 'Загружен',
      type: 'Тип',
      category: 'Категория',
      tags: 'Теги',
      notes: 'Заметки'
    }
  }
}

export function useI18n() {
  function t(key: string) {
    const keys = key.split('.')
    let value = messages[currentLocale.value]
    for (const k of keys) {
      if (value && value[k]) {
        value = value[k]
      } else {
        return key
      }
    }
    return value
  }

  function setLocale(locale: string) {
    if (messages[locale]) {
      currentLocale.value = locale
      localStorage.setItem('locale', locale)
    }
  }

  // Init
  const saved = localStorage.getItem('locale')
  if (saved && messages[saved]) {
    currentLocale.value = saved
  }

  return { t, setLocale, currentLocale, locale: currentLocale }
}
