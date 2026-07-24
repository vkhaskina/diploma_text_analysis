<template>
  <div class="keyword-search-container">
    <div class="search-panel">
      <h2>Поиск документов по ключевым словам</h2>
      <div class="search-input-group">
        <input
          type="text"
          v-model="query"
          placeholder="Введите ключевые слова (через пробел, запятую)"
          @keyup.enter="search"
        />
        <button @click="search" :disabled="loading">
          {{ loading ? 'Поиск...' : 'Найти' }}
        </button>
      </div>
    </div>

    <div class="results-panel">
      <h3 v-if="results.length">Результаты ({{ results.length }})</h3>
      <div v-if="results.length" class="similar-catalogs-list">
        <div v-for="doc in results" :key="doc.id" class="similar-catalog-item">
          <div class="similar-catalog-name">
            <strong>{{ doc.file_name }}</strong>
            <span class="match-badge">Совпадений: {{ doc.match_count }}</span>
          </div>
          <div class="similar-catalog-path">{{ doc.catalog_path }}</div>
          <div class="similar-catalog-info">Размер текста: {{ doc.text_length }} символов</div>
          <button @click="goToDocument(doc.id)" class="similar-catalog-btn">
            Анализировать файл
          </button>
        </div>
      </div>
      <div v-else-if="searched && !loading" class="no-similar-catalogs">
        Ничего не найдено.
      </div>
    </div>
  </div>
</template>

<script>

export default {
  name: 'KeywordSearch',
  data() {
    return {
      query: '',
      results: [],
      loading: false,
      searched: false
    }
  },
  methods: {
    async search() {
      if (!this.query.trim()) return
      this.loading = true
      try {
        const response = await fetch('http://localhost:8000/api/keyword-search/', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify({ query: this.query })
        })
        const data = await response.json()
        if (Array.isArray(data)) {
          this.results = data
        } else {
          console.error('Ошибка поиска:', data)
          this.results = []
        }
        this.searched = true
      } catch (err) {
        console.error('Ошибка поиска:', err)
      } finally {
        this.loading = false
      }
    },
    goToDocument(docId) {
      this.$router.push(`/document/${docId}`)
    }
  }
}
</script>

<style scoped>
.keyword-search-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
}
.search-panel {
  background: white;
  padding: 20px;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  margin-bottom: 20px;
}
.search-panel h2 {
  margin-top: 0;
  margin-bottom: 15px;
  font-size: 1.8rem;
  color: #2c3e50;
}
.search-input-group {
  display: flex;
  gap: 10px;
  margin-top: 15px;
}
.search-input-group input {
  flex: 1;
  padding: 10px;
  border: 1px solid #ccc;
  border-radius: 6px;
  font-size: 16px;
}
.search-input-group button {
  padding: 10px 24px;
  background: #3498db;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
}
.search-input-group button:hover:not(:disabled) {
  background: #2980b9;
}
.similar-catalogs-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 20px;
  margin-top: 20px;
}
.similar-catalog-item {
  background: white;
  padding: 20px;
  border-radius: 10px;
  border: 1px solid #e0e0e0;
  transition: all 0.3s;
}
.similar-catalog-item:hover {
  transform: translateY(-5px);
  box-shadow: 0 10px 20px rgba(52,152,219,0.2);
  border-color: #3498db;
}
.similar-catalog-name {
  font-size: 18px;
  margin-bottom: 8px;
  color: #2c3e50;
  font-weight: 600;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
}
.match-badge {
  background: #f0f0f0;
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 0.8em;
  font-weight: normal;
  color: #2c3e50;
}
.similar-catalog-path {
  font-size: 13px;
  color: #7f8c8d;
  margin-bottom: 10px;
  word-break: break-all;
}
.similar-catalog-info {
  font-size: 13px;
  color: #95a5a6;
  margin-bottom: 15px;
}
.similar-catalog-btn {
  width: 100%;
  padding: 8px;
  background: #3498db;
  color: white;
  border: none;
  border-radius: 5px;
  cursor: pointer;
  transition: all 0.3s;
  font-size: 14px;
}
.similar-catalog-btn:hover {
  background: #2980b9;
  transform: translateY(-2px);
  box-shadow: 0 5px 15px rgba(52,152,219,0.3);
}
.no-similar-catalogs {
  text-align: center;
  padding: 40px;
  color: #95a5a6;
  font-style: italic;
}
</style>
