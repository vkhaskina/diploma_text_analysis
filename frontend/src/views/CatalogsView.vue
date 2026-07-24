<template>
  <div class="catalogs-container">
    <div class="header">
      <h3>Найдены конечные каталоги ({{ catalogButtons?.length || 0 }})</h3>
      <p>Выберите каталог для анализа:</p>
    </div>

    <!-- Добавляем проверку на существование fileInfo -->
    <div v-if="fileInfo && fileInfo.name" class="file-info card mb-4">
      <div class="card-body">
        <h5 class="card-title">Загруженный файл:</h5>
        <p><strong>Имя:</strong> {{ fileInfo.name }}</p>
        <p><strong>Размер:</strong> {{ formatSize(fileInfo.size) }}</p>
      </div>
    </div>

    <div class="catalogs-list">
      <div
        v-for="catalog in catalogButtons"
        :key="catalog.id"
        class="catalog-item"
        @click="handleCatalogSelect(catalog)"
        :class="{ 'selected': selectedCatalogId === catalog.id }"
      >
        <div class="catalog-name">
          <strong>{{ catalog.name }}</strong>
        </div>

        <div class="catalog-path">
          {{ catalog.label }}
        </div>

        <div class="catalog-info">
          Каталог №{{ catalog.id }}
        </div>
      </div>
    </div>

    <div class="actions">
      <button
        @click="analyzeSelectedCatalog"
        :disabled="!selectedCatalogId || analyzing"
        class="analyze-btn"
      >
        <span v-if="analyzing" class="spinner-border spinner-border-sm me-2"></span>
        {{ analyzing ? 'Анализ...' : 'Анализировать выбранный каталог' }}
      </button>
    </div>

    <div v-if="error" class="alert alert-danger mt-4">
      {{ error }}
    </div>
  </div>
</template>

<script>
import { mapState, mapActions } from 'pinia'
import { useUploadStore } from '@/stores/uploaded'

export default {
  name: 'CatalogsView',

  data() {
    return {
      selectedCatalogId: null,
      selectedCatalogPath: null,
      analyzing: false,
      error: null,
    }
  },

  computed: {
    ...mapState(useUploadStore, [
      'catalogButtons',
      'fileInfo',
      'selectedCatalog',
      'processingResults',
      'status'
    ])
  },

  methods: {
    ...mapActions(useUploadStore, [
      'selectCatalog',
      'setProcessingResults',
      'setStatus',
      'setError',
      'clearAll'
    ]),

    handleCatalogSelect(catalog) {
      if (catalog.id !== undefined && catalog.id !== null && catalog.id !== 0) {
        this.selectedCatalogId = catalog.id;
        this.selectedCatalogPath = catalog.path;

        this.selectCatalog(catalog);

        console.log('Выбран каталог:', catalog);
      } else {
        console.error('Некорректный ID каталога:', catalog.id);
        this.error = 'Ошибка выбора каталога';
      }
    },

    // async analyzeSelectedCatalog() {
    //   if (!this.selectedCatalogId || !this.selectedCatalogPath) {
    //     this.error = 'Пожалуйста, выберите каталог';
    //     return;
    //   }

    //   this.analyzing = true;
    //   this.error = null;
    //   this.setStatus('analyzing');

    //   // Подготовка данных для отправки
    //   const requestData = {
    //     catalog_id: this.selectedCatalogId,
    //     catalog_path: this.selectedCatalogPath,
    //     catalog_name: this.selectedCatalog?.name || null
    //   };

    //   console.log('Отправляю данные на бэкенд:', requestData);

    //   try {
    //     const response = await fetch('http://localhost:8000/api/analyze/', {
    //       method: 'POST',
    //       headers: {
    //         'Content-Type': 'application/json',
    //       },
    //       credentials: 'include',
    //       body: JSON.stringify(requestData)
    //     });

    //     const result = await response.json();
    //     console.log('Ответ от сервера:', result);

    //     if (response.ok) {
    //       console.log('Анализ запущен:', result);
    //       this.setProcessingResults(result);
    //       this.$router.push('/analysis');
    //     } else {
    //       this.error = result.error || result.message || 'Ошибка при анализе';
    //       this.setError(this.error);
    //     }
    //   } catch (err) {
    //     console.error('Ошибка при отправке запроса:', err);
    //     this.error = 'Ошибка сети: ' + err.message;
    //     this.setError(this.error);
    //   } finally {
    //     this.analyzing = false;
    //   }
    // },

    async analyzeSelectedCatalog() {
      if (!this.selectedCatalogId || !this.selectedCatalogPath) {
        this.error = 'Пожалуйста, выберите каталог';
        return;
      }

      this.analyzing = true;
      this.error = null;
      this.setStatus('analyzing');

      // Отправляем ТОЛЬКО путь, без ID
      const requestData = {
        catalog_path: this.selectedCatalogPath
      };

      console.log('Отправляю данные на бэкенд:', requestData);

      try {
        const response = await fetch('http://localhost:8000/api/analyze/', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          credentials: 'include',
          body: JSON.stringify(requestData)
        });

        const result = await response.json();
        console.log('Ответ от сервера:', result);

        if (response.ok) {
          console.log('Анализ запущен:', result);
          this.setProcessingResults(result);
          this.$router.push('/analysis');
        } else {
          this.error = result.error || result.message || 'Ошибка при анализе';
          this.setError(this.error);
        }
      } catch (err) {
        console.error('Ошибка при отправке запроса:', err);
        this.error = 'Ошибка сети: ' + err.message;
        this.setError(this.error);
      } finally {
        this.analyzing = false;
      }
    },

    formatSize(bytes) {
      if (!bytes) return '0 Bytes';
      const k = 1024;
      const sizes = ['Bytes', 'KB', 'MB', 'GB'];
      const i = Math.floor(Math.log(bytes) / Math.log(k));
      return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
  },

  mounted() {
    console.log('CatalogsView mounted');
    console.log('CatalogButtons:', this.catalogButtons);
    console.log('FileInfo:', this.fileInfo);

    // Если нет каталогов - возвращаем на главную
    if (!this.catalogButtons || this.catalogButtons.length === 0) {
      console.warn('Нет каталогов, редирект на главную');
      this.$router.push('/');
    }

    // Если есть выбранный каталог в хранилище - восстанавливаем
    if (this.selectedCatalog) {
      this.selectedCatalogId = this.selectedCatalog.id;
      this.selectedCatalogPath = this.selectedCatalog.path;
    }
  }
}
</script>

<style scoped>
  /* Ваши стили остаются без изменений */
  .catalogs-container {
    margin-top: 10px;
  }

  .header {
    margin-bottom: 25px;
    padding-bottom: 15px;
    border-bottom: 3px solid #3498db;
  }

  .header h3 {
    margin: 0 0 10px 0;
    color: #333;
    font-size: 1.8em;
  }

  .header p {
    margin: 0;
    color: #666;
    font-size: 1.1em;
  }

  .file-info {
    background: #f8f9fa;
    border-left: 4px solid #3498db;
    margin-bottom: 25px;
  }

  .card {
    border: 1px solid #e0e0e0;
    border-radius: 10px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  }

  .card-body {
    padding: 20px;
  }

  .card-title {
    color: #2c3e50;
    margin-bottom: 15px;
  }

  .catalogs-list {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
    gap: 20px;
    max-height: 500px;
    overflow-y: auto;
    padding: 15px;
    margin-bottom: 30px;
    background: white;
    border-radius: 10px;
    border: 1px solid #e0e0e0;
  }

  .catalog-item {
    background: white;
    padding: 20px;
    border-radius: 10px;
    border: 2px solid #e0e0e0;
    cursor: pointer;
    transition: all 0.3s;
    position: relative;
    overflow: hidden;
  }

  .catalog-item:hover {
    border-color: #3498db;
    transform: translateY(-5px);
    box-shadow: 0 10px 20px rgba(52, 152, 219, 0.2);
  }

  .catalog-item.selected {
    border-color: #2196F3;
    background: linear-gradient(135deg, #f0f8ff 0%, #e3f2fd 100%);
    box-shadow: 0 5px 15px rgba(33, 150, 243, 0.3);
  }

  .catalog-item.selected::before {
    content: '✓';
    position: absolute;
    top: 10px;
    right: 10px;
    background: #2196F3;
    color: white;
    width: 25px;
    height: 25px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: bold;
  }

  .catalog-name {
    font-size: 18px;
    margin-bottom: 8px;
    color: #2c3e50;
    font-weight: 600;
  }

  .catalog-path {
    font-size: 14px;
    color: #7f8c8d;
    margin-bottom: 10px;
    word-break: break-all;
    line-height: 1.4;
  }

  .catalog-info {
    font-size: 13px;
    color: #95a5a6;
    padding: 5px 10px;
    background: #f8f9fa;
    border-radius: 15px;
    display: inline-block;
    font-weight: 500;
  }

  .actions {
    display: flex;
    gap: 20px;
    justify-content: center;
    margin-top: 30px;
    padding-top: 30px;
    border-top: 2px solid #eee;
  }

  .analyze-btn {
    background: linear-gradient(135deg, #2196F3 0%, #1976D2 100%);
    padding: 15px 30px;
    font-size: 17px;
    min-width: 250px;
    border: none;
    border-radius: 8px;
    cursor: pointer;
    font-weight: 500;
    transition: all 0.3s;
    color: white;
  }

  .analyze-btn:hover:not(:disabled) {
    background: linear-gradient(135deg, #1976D2 0%, #1565c0 100%);
    transform: translateY(-2px);
    box-shadow: 0 5px 15px rgba(33, 150, 243, 0.3);
  }

  .analyze-btn:disabled {
    background: #cccccc;
    cursor: not-allowed;
    opacity: 0.7;
  }

  .alert {
    padding: 15px;
    border-radius: 8px;
    margin-top: 20px;
  }

  .alert-danger {
    background-color: #f8d7da;
    border: 1px solid #f5c6cb;
    color: #721c24;
  }

  .spinner-border {
    display: inline-block;
    width: 1rem;
    height: 1rem;
    border: 0.2em solid currentColor;
    border-right-color: transparent;
    border-radius: 50%;
    animation: spinner-border .75s linear infinite;
  }

  @keyframes spinner-border {
    to { transform: rotate(360deg); }
  }

  .me-2 {
    margin-right: 0.5rem;
  }
</style>
