
import { defineStore } from 'pinia'

export const useUploadStore = defineStore('upload', {
  // Состояние (данные)
  state: () => ({
    // Информация о загруженном файле
    fileInfo: {
      name: null,
      size: null,
      catalogsCount: null
    },
    // Список каталогов для кнопок
    catalogButtons: [],
    // Выбранный каталог
    selectedCatalog: null,
    // Результаты обработки
    processingResults: null,
    // Статус загрузки/обработки
    status: 'idle', // idle, uploading, processing, done, error
    error: null,
    // ID задачи (если нужно)
    taskId: null,
    // Путь к временному файлу (если нужно на бэке)
    tempZipPath: null
  }),

  // Геттеры (как computed свойства)
  getters: {
    // Проверка, есть ли загруженный файл
    hasFile: (state) => !!state.fileInfo.name,

    // Количество каталогов
    catalogsCount: (state) => state.catalogButtons.length,

    // Есть ли результаты обработки
    hasResults: (state) => !!state.processingResults,

    // Получить информацию о файле для отображения
    fileDisplayName: (state) => {
      if (!state.fileInfo.name) return 'Файл не выбран'
      return `${state.fileInfo.name} (${(state.fileInfo.size / 1024).toFixed(2)} KB)`
    }
  },

  // Действия (методы)
  actions: {
    // Сохранить информацию о загруженном файле
    setFileInfo(fileInfo) {
      this.fileInfo = {
        name: fileInfo.name || null,
        size: fileInfo.size || null,
        catalogsCount: fileInfo.catalogsCount || null
      }
    },

    // Сохранить список каталогов
    setCatalogButtons(buttons) {
      this.catalogButtons = buttons || []
    },

    // Выбрать каталог
    selectCatalog(catalog) {
      this.selectedCatalog = catalog
    },

    // Сохранить результаты обработки
    setProcessingResults(results) {
      this.processingResults = results
      this.status = 'done'
    },

    // Установить статус
    setStatus(status) {
      this.status = status
    },

    // Установить ошибку
    setError(error) {
      this.error = error
      this.status = 'error'
    },

    // Установить ID задачи
    setTaskId(taskId) {
      this.taskId = taskId
    },

    // Установить путь к временному файлу
    setTempZipPath(path) {
      this.tempZipPath = path
    },

    // Очистить все данные (при новой загрузке)
    clearAll() {
      this.fileInfo = {
        name: null,
        size: null,
        catalogsCount: null
      }
      this.catalogButtons = []
      this.selectedCatalog = null
      this.processingResults = null
      this.status = 'idle'
      this.error = null
      this.taskId = null
      this.tempZipPath = null
    },

    // Очистить только результаты (оставить файл)
    clearResults() {
      this.processingResults = null
      this.status = 'idle'
    }
  },

  // Сохраняем данные в localStorage
  persist: {
    key: 'upload-store', // ключ в localStorage
    storage: localStorage, // используем localStorage
    paths: ['fileInfo', 'catalogButtons', 'selectedCatalog', 'processingResults', 'taskId'] // что сохранять
  }
})
