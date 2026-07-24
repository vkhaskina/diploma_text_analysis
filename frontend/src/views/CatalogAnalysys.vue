<template>
  <div class="analysis-container">
    <div class="back-button">
      <button @click="goBackToCatalogs" class="btn-back">
        ← К списку каталогов
      </button>
    </div>

    <div v-if="loading" class="loading-overlay">
      <div class="loading-spinner-large"></div>
      <p>Загрузка результатов анализа...</p>
    </div>

    <div v-else-if="analysisResults" class="analysis-results" :class="{ 'fade-in': !loading }">
      <h2 class="analysis-title">{{ analysisResults.catalogName }}</h2>

      <div class="catalog-path-breadcrumb">
        <span>Путь: </span>
        <span v-for="(part, index) in analysisResults.pathParts" :key="index">
          <a href="#" @click.prevent="navigateToPathPart(part, index)" class="path-part">
            {{ part }}
          </a>
          <span v-if="index < analysisResults.pathParts.length - 1" class="path-separator"> / </span>
        </span>
      </div>

      <div class="files-count">
        <div class="count-badge">
          <span class="count-number">{{ analysisResults.filesCount }}</span>
          <span class="count-label">файлов для анализа</span>
        </div>
        <p class="count-description">
          Будут проанализированы все текстовые файлы в выбранном каталоге
        </p>
      </div>

      <div class="wordcloud-section">
        <h3>Облако слов из файлов каталога</h3>
        <div class="wordcloud-frame">
          <div v-if="analysisResults.wordcloud" class="wordcloud-content">
            <WordCloud
              :wordsData="analysisResults.wordcloud.words"
              :width="wordcloudWidth"
              :height="400"
              :minFontSize="14"
              :maxFontSize="60"
              :colors="wordColors"
            />
            <div class="wordcloud-stats">
              <p>Всего слов: {{ analysisResults.wordcloud.totalWords }}</p>
              <p>Уникальных слов: {{ analysisResults.wordcloud.uniqueWords }}</p>
              <p>Самые частые: {{ analysisResults.wordcloud.topWords.join(', ') }}</p>
            </div>
          </div>
          <div v-else class="wordcloud-placeholder">
            <div class="wordcloud-loading">
              <div class="loading-spinner"></div>
              <p>Генерация облака слов...</p>
            </div>
          </div>
        </div>
      </div>

      <div class="similar-catalogs-section" v-if="!isDocumentMode">
        <div class="section-header" @click="toggleSimilarCatalogs">
          <h3>Похожие каталоги в архиве</h3>
          <button class="toggle-btn">{{ similarCatalogsVisible ? '▼' : '▶' }}</button>
        </div>
        <transition name="slide">
          <div v-show="similarCatalogsVisible" class="similar-catalogs-frame">
            <div v-if="analysisResults.similar_by_name && analysisResults.similar_by_name.length > 0"
                 class="similar-catalogs-list">
              <div v-for="(catalog, index) in analysisResults.similar_by_name" :key="index" class="similar-catalog-item">
                <div class="similar-catalog-name"><strong>{{ catalog.name }}</strong></div>
                <div class="similar-catalog-path">{{ catalog.path }}</div>
                <div class="similar-catalog-info">Файлов: {{ catalog.filesCount }}</div>
                <button @click="analyzeSimilarCatalog(catalog)" class="similar-catalog-btn" :disabled="loading">
                  <span v-if="loading && selectedCatalog?.path === catalog.path" class="spinner-border spinner-border-sm me-2"></span>
                  Анализировать
                </button>
              </div>
            </div>
            <div v-else class="no-similar-catalogs">Каталогов с таким же названием не найдено</div>
          </div>
        </transition>
      </div>

      <div class="clusters-section" v-if="analysisResults.clustering">
        <div class="section-header" @click="toggleClusters">
          <h3>Тематические кластеры</h3>
          <button class="toggle-btn">{{ clustersVisible ? '▼' : '▶' }}</button>
        </div>
        <transition name="slide">
          <div v-show="clustersVisible">
            <div class="clusters-controls">
              <div class="control-group">
                <label>Алгоритм:</label>
                <select v-model="clusterParams.method">
                  <option value="kmeans">K-Means</option>
                  <option value="dbscan">DBSCAN</option>
                </select>
              </div>
              <div v-if="clusterParams.method === 'dbscan'" class="control-group">
                <label>eps:</label>
                <input type="number" v-model.number="clusterParams.eps" step="0.1" min="0.1" max="2">
                <label>min_samples:</label>
                <input type="number" v-model.number="clusterParams.min_samples" min="1" max="10">
              </div>
              <div v-else class="control-group">
                <label>Количество кластеров:</label>
                <input type="range" v-model.number="clusterParams.n_clusters" min="2" :max="Math.min(8, analysisResults.clustering?.statistics?.total_words || 10)">
                <span class="value">{{ clusterParams.n_clusters }}</span>
              </div>
              <div class="control-group">
                <label><input type="checkbox" v-model="clusterParams.auto_clusters"> Автоподбор</label>
              </div>
              <button @click="runClustering" class="cluster-btn" :disabled="clusteringLoading">
                <span v-if="clusteringLoading" class="spinner-border spinner-border-sm me-2"></span>
                {{ clusteringLoading ? 'Кластеризация...' : 'Перекластеризовать' }}
              </button>
            </div>

            <div class="clusters-stats" v-if="analysisResults.clustering.statistics">
              <p>Всего слов: {{ analysisResults.clustering.statistics.total_words }}</p>
              <p>Метод: {{ analysisResults.clustering.statistics.method }}</p>
              <p v-if="analysisResults.clustering.statistics.silhouette_score !== undefined && analysisResults.clustering.statistics.silhouette_score !== null">
                Силуэт: {{ analysisResults.clustering.statistics.silhouette_score.toFixed(3) }}
              </p>
              <p v-if="analysisResults.clustering.statistics.method === 'kmeans'">Кластеров: {{ analysisResults.clustering.statistics.n_clusters }}</p>
              <p v-if="analysisResults.clustering.statistics.method === 'dbscan'">Кластеров: {{ analysisResults.clustering.statistics.n_clusters }}</p>
              <p v-if="analysisResults.clustering.statistics.inertia !== undefined">Инерция: {{ analysisResults.clustering.statistics.inertia.toFixed(2) }}</p>
            </div>

            <div class="clusters-container">
              <div v-for="cluster in analysisResults.clustering.clusters" :key="cluster.id" class="cluster-card">
                <div class="cluster-header">
                  <h4>Кластер {{ cluster.id + 1 }} <span class="cluster-size">({{ cluster.size }} слов)</span></h4>
                </div>
                <div class="cluster-body">
                  <div class="cluster-words-list">
                    <div v-for="(word, idx) in cluster.words.slice(0, 10)" :key="idx" class="cluster-word-item" @click="searchWord(word)">
                      <span class="cluster-word">{{ word }}</span>
                      <span v-if="idx < cluster.words.slice(0, 10).length - 1" class="word-separator">•</span>
                    </div>
                  </div>
                  <div class="cluster-top-words" v-if="cluster.top_words">
                    <h5>Ключевые слова:</h5>
                    <div class="top-words-list">
                      <div v-for="word in cluster.top_words" :key="word.word" class="top-word-item">
                        <span class="word">{{ word.word }}</span>
                        <span class="frequency">{{ word.frequency }}</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div v-if="analysisResults.clustering && analysisResults.clustering.projection && analysisResults.clustering.projection.length"
                class="clusters-viz-section">
              <div class="section-header" @click="toggleViz">
                <h3>Визуализация кластеров (2D проекция)</h3>
                <button class="toggle-btn">{{ vizVisible ? '▼' : '▶' }}</button>
              </div>
              <transition name="slide">
                <div v-show="vizVisible" class="viz-layout">
                  <div class="viz-chart-container">
                    <div ref="scatterChart" style="width: 100%; height: 500px;"></div>
                  </div>
                  <div class="viz-keywords-panel">
                    <h4>Ключевые слова кластеров</h4>
                    <div v-for="cluster in analysisResults.clustering.clusters" :key="cluster.id" class="cluster-keywords-card">
                      <div class="cluster-title" :style="{ borderLeftColor: cluster.color }">
                        Кластер {{ cluster.id + 1 }} ({{ cluster.size }} слов)
                      </div>
                      <div class="cluster-keywords-list">
                        <span v-for="word in (cluster.top_words || []).slice(0,5)" :key="word.word" class="keyword-badge">
                          {{ word.word }} ({{ word.frequency }})
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              </transition>
            </div>

            <div class="trend-section">
              <div class="section-header" @click="toggleTrend">
                <h3>Динамика темы по времени</h3>
                <button class="toggle-btn">{{ trendVisible ? '▼' : '▶' }}</button>
              </div>
              <transition name="slide">
                <div v-show="trendVisible" class="trend-content">
                  <div class="trend-controls">
                    <select v-model="selectedClusterId">
                      <option v-for="cluster in analysisResults.clustering.clusters" :key="cluster.id" :value="cluster.id">
                        Кластер {{ cluster.id + 1 }} ({{ cluster.size }} слов)
                      </option>
                    </select>
                    <button @click="loadTrend" :disabled="trendLoading">
                      {{ trendLoading ? 'Загрузка...' : 'Показать динамику' }}
                    </button>

                  </div>
                    <div class="cluster-keywords" v-if="selectedClusterKeywords">
                      <strong>Ключевые слова кластера:</strong> {{ selectedClusterKeywords }}
                    </div>
                  <div ref="trendChart" style="width: 100%; height: 400px;"></div>
                </div>
              </transition>
            </div>
          </div>
        </transition>
      </div>

      <div class="similar-catalogs-section" v-if="!isDocumentMode">
        <div class="section-header" @click="toggleSemanticCatalogs">
          <h3>Семантически похожие каталоги</h3>
          <button class="toggle-btn">{{ semanticCatalogsVisible ? '▼' : '▶' }}</button>
        </div>
        <transition name="slide">
          <div v-show="semanticCatalogsVisible" class="similar-catalogs-frame">
            <div v-if="analysisResults.similar_catalogs && analysisResults.similar_catalogs.length > 0" class="similar-catalogs-list">
              <div v-for="(catalog, index) in analysisResults.similar_catalogs" :key="index" class="similar-catalog-item">
                <div class="similar-catalog-name"><strong>{{ catalog.name }}</strong></div>
                <div class="similar-catalog-path">{{ catalog.path }}</div>
                <div class="similar-catalog-info">
                  <span v-if="catalog.similarity !== undefined">Схожесть: {{ (catalog.similarity * 100).toFixed(0) }}%</span>
                  <span v-else>Файлов: {{ catalog.filesCount }}</span>
                </div>
                <button @click="analyzeSimilarCatalog(catalog)" class="similar-catalog-btn" :disabled="loading">
                  <span v-if="loading && selectedCatalog?.path === catalog.path" class="spinner-border spinner-border-sm me-2"></span>
                  Анализировать
                </button>
              </div>
            </div>
            <div v-else class="no-similar-catalogs">Семантически похожих каталогов не найдено</div>
          </div>
        </transition>
      </div>
    </div>

    <div v-else-if="error" class="error-state">
      <p class="error-message">{{ error }}</p>
      <button @click="retryAnalysis" class="btn-retry">Повторить</button>
    </div>
  </div>
</template>

<script>
import { mapState, mapActions } from 'pinia'
import { useUploadStore } from '@/stores/uploaded'
import WordCloud from '@/components/WordCloud.vue'
import * as echarts from 'echarts'

export default {
  name: 'CatalogAnalysis',
  components: { WordCloud },

  data() {
    return {
      loading: true,
      error: null,
      analysisResults: null,
      isTransitioning: false,

      wordcloudWidth: 800,
      wordColors: [
        '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
        '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf',
        '#3498db', '#e74c3c', '#2ecc71', '#f39c12', '#9b59b6',
        '#34495e', '#16a085', '#27ae60', '#2980b9', '#8e44ad'
      ],
      clusteringLoading: false,
      clusterParams: {
        n_clusters: 5,
        auto_clusters: true,
        method: 'kmeans',
        eps: 0.5,
        min_samples: 2
      },
      similarCatalogsVisible: true,
      clustersVisible: true,
      semanticCatalogsVisible: true,
      trendVisible: false,
      trendLoading: false,
      selectedClusterId: null,
      trendChartInstance: null,
      vizVisible: true,
      scatterChartInstance: null,
      documentId: null,
      isDocumentMode: false,
    }
  },

  computed: {
    ...mapState(useUploadStore, [
      'selectedCatalog',
      'fileInfo',
      'processingResults'
    ]),
    selectedClusterKeywords() {
      if (!this.analysisResults?.clustering?.clusters || this.selectedClusterId === null) return '';
      const cluster = this.analysisResults.clustering.clusters.find(c => c.id === this.selectedClusterId);
      if (!cluster) return '';
      const topWords = cluster.top_words || [];
      return topWords.slice(0, 5).map(w => w.word).join(', ');
    }
  },

  mounted() {
    this.updateWordcloudWidth()
    window.addEventListener('resize', this.updateWordcloudWidth)

    if (this.$route.params.id) {
      this.documentId = this.$route.params.id
      this.isDocumentMode = true
      this.fetchDocumentAnalysis()
    } else if (this.selectedCatalog) {
      this.fetchAnalysisResults()
    } else {
      this.error = 'Каталог не выбран'
      this.loading = false
    }
  },

  watch: {
    'selectedCatalog': {
      handler(newCatalog, oldCatalog) {
        if (newCatalog && (!oldCatalog || newCatalog.path !== oldCatalog?.path)) {
          this.isTransitioning = true
          this.loading = true
          this.analysisResults = null
          this.fetchAnalysisResults()
        }
      },
      deep: true
    },
    'clusterParams.auto_clusters'(newVal) {
      if (newVal) this.runClustering()
    },
    'analysisResults.clustering': {
      handler(newVal) {
        if (newVal && newVal.clusters && newVal.clusters.length && this.selectedClusterId === null) {
          this.selectedClusterId = newVal.clusters[0].id;
          this.$nextTick(() => this.renderScatterChart());
        }
      },
      deep: true
    },
    selectedClusterId(newVal) {
      if (newVal !== null && this.trendVisible && !this.trendChartInstance) {
        this.loadTrend()
      }
    }
  },

  methods: {
    ...mapActions(useUploadStore, [
      'setProcessingResults',
      'setStatus',
      'setError',
      'selectCatalog'
    ]),

    updateWordcloudWidth() {
      const container = document.querySelector('.wordcloud-frame')
      if (container) this.wordcloudWidth = container.clientWidth - 40
    },

    scrollToTop() {
      window.scrollTo({ top: 0, behavior: 'smooth' })
    },

    async fetchDocumentAnalysis() {
      this.error = null
      this.loading = true
      try {
        const response = await fetch('http://localhost:8000/api/analyze/', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify({ document_id: this.documentId })
        })
        const result = await response.json()
        if (response.ok) {
          this.analysisResults = {
            catalogName: result.file_name,
            fullPath: result.catalog_path,
            pathParts: result.catalog_path.split('/'),
            filesCount: 1,
            wordcloud: result.wordcloud,
            all_top_words: result.top_words,
            clustering: null,
            similar_catalogs: [],
            similar_by_name: []
          }
          this.isDocumentMode = true
        } else {
          throw new Error(result.error || 'Ошибка загрузки документа')
        }
      } catch (err) {
        this.error = err.message
      } finally {
        this.loading = false
      }
    },

    async fetchAnalysisResults() {
      this.error = null
      try {
        if (!this.selectedCatalog) throw new Error('Каталог не выбран')
        const requestData = { catalog_path: this.selectedCatalog.path }
        const response = await fetch('http://localhost:8000/api/analyze/', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify(requestData)
        })
        const result = await response.json()
        if (response.ok) {
          this.analysisResults = result
          if (this.analysisResults.clustering && this.analysisResults.clustering.projection && this.vizVisible) {
            this.$nextTick(() => this.renderScatterChart());
          }
          this.setProcessingResults(result)
          this.setStatus('analysis_complete')
          this.$nextTick(() => {
            this.scrollToTop()
            setTimeout(() => (this.isTransitioning = false), 300)
          })
        } else {
          throw new Error(result.error || 'Ошибка при загрузке результатов')
        }
      } catch (err) {
        this.error = err.message
        this.setError(this.error)
      } finally {
        this.loading = false
      }
    },

    goBackToCatalogs() {
      this.$router.push('/catalogs')
    },

    navigateToPathPart(part, index) {
      const pathParts = this.analysisResults.pathParts.slice(0, index + 1)
      const newPath = pathParts.join('/')
      this.scrollToTop()
      this.selectCatalog({ name: part, path: newPath })
    },

    analyzeSimilarCatalog(catalog) {
      this.scrollToTop()
      this.selectCatalog(catalog)
    },

    retryAnalysis() {
      this.fetchAnalysisResults()
    },

    async runClustering() {
      this.clusteringLoading = true
      try {
        const payload = {
          catalog_path: this.analysisResults.fullPath,
          method: this.clusterParams.method,
          force: true
        }
        if (this.clusterParams.method === 'kmeans') {
          payload.n_clusters = this.clusterParams.auto_clusters ? null : this.clusterParams.n_clusters
          payload.auto_clusters = this.clusterParams.auto_clusters
        } else {
          payload.eps = this.clusterParams.eps
          payload.min_samples = this.clusterParams.min_samples
        }
        const response = await fetch('http://localhost:8000/api/analyze/', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify(payload)
        })
        const result = await response.json()
        if (response.ok) {
          this.analysisResults = result
          if (this.analysisResults.clustering?.projection && this.vizVisible) {
            this.$nextTick(() => this.renderScatterChart());
          }
          this.$nextTick(() => this.scrollToClusters())
        } else {
          console.error('Ошибка кластеризации:', result)
        }
      } catch (err) {
        console.error(err)
      } finally {
        this.clusteringLoading = false
      }
    },

    scrollToClusters() {
      const section = this.$el.querySelector('.clusters-section')
      if (section) section.scrollIntoView({ behavior: 'smooth', block: 'start' })
    },

    searchWord(word) {
      console.log('Поиск слова:', word)
    },

    toggleSimilarCatalogs() { this.similarCatalogsVisible = !this.similarCatalogsVisible },
    toggleClusters() { this.clustersVisible = !this.clustersVisible },
    toggleSemanticCatalogs() { this.semanticCatalogsVisible = !this.semanticCatalogsVisible },

    toggleTrend() {
      this.trendVisible = !this.trendVisible
      if (this.trendVisible && !this.trendChartInstance) {
        this.loadTrend()
      }
    },

    async loadTrend() {
      if (this.selectedClusterId === null && this.analysisResults.clustering.clusters.length) {
        this.selectedClusterId = this.analysisResults.clustering.clusters[0].id
      }
      if (this.selectedClusterId === null) return
      this.trendLoading = true
      try {
        const response = await fetch('http://localhost:8000/api/cluster-trend/', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify({
            catalog_path: this.analysisResults.fullPath,
            cluster_id: this.selectedClusterId,
            method: this.clusterParams.method
          })
        })
        const data = await response.json()
        if (response.ok) {
          this.renderTrendChart(data)
        } else {
          console.error('Ошибка получения тренда:', data)
        }
      } catch (err) {
        console.error(err)
      } finally {
        this.trendLoading = false
      }
    },

  renderTrendChart(data) {
    if (this.trendChartInstance) this.trendChartInstance.dispose()
    const chartDom = this.$refs.trendChart
    if (!chartDom) return
    this.trendChartInstance = echarts.init(chartDom)
    const option = {
      title: { text: 'Динамика кластера', left: 'center' },
      tooltip: { trigger: 'item', axisPointer: { type: 'shadow' } },
      legend: { data: ['Количество документов'], left: 'left' },
      xAxis: {
        type: 'category',
        data: data.map(d => `${d.year} Q${d.quarter}`),
        name: 'Период',
        nameLocation: 'middle',
        nameGap: 35,
        axisLabel: {
          rotate: 45,
          margin: 10,
          fontSize: 10,
          interval: 5,
          hideOverlap: true
        }
      },
      yAxis: {
        type: 'value',
        name: 'Количество документов',
        position: 'left'
      },
      series: [
        {
          name: 'Количество документов',
          type: 'line',
          data: data.map(d => d.count),
          smooth: true,
          lineStyle: { color: '#3498db', width: 2 },
          symbol: 'circle',
          symbolSize: 8
        }
      ],
      grid: {
        containLabel: true,
        left: '8%',
        right: '8%',
        top: '15%',
        bottom: '18%'
      }
    }
    this.trendChartInstance.setOption(option)
    window.addEventListener('resize', () => this.trendChartInstance?.resize())
  },

    toggleViz() {
      this.vizVisible = !this.vizVisible;
      if (this.vizVisible && !this.scatterChartInstance) {
        this.$nextTick(() => this.renderScatterChart());
      }
    },
    renderScatterChart() {
      if (this.scatterChartInstance) {
        this.scatterChartInstance.dispose();
      }
      const chartDom = this.$refs.scatterChart;
      if (!chartDom) return;
      const projection = this.analysisResults.clustering.projection;
      if (!projection || !projection.length) return;

      const clustersMap = new Map();
      projection.forEach(p => {
        const clusterId = p.cluster;
        if (!clustersMap.has(clusterId)) clustersMap.set(clusterId, []);
        clustersMap.get(clusterId).push([p.x, p.y, p.word]);
      });

      const clusterColors = {};
      this.analysisResults.clustering.clusters.forEach(c => {
        clusterColors[c.id] = c.color;
      });
      if (clustersMap.has(-1)) clusterColors[-1] = '#cccccc';

      const series = Array.from(clustersMap.entries()).map(([clusterId, points]) => ({
        name: clusterId === -1 ? 'Шум' : `Кластер ${clusterId + 1}`,
        type: 'scatter',
        data: points.map(p => ({ value: [p[0], p[1]], name: p[2] })),
        symbolSize: 12,
        itemStyle: { color: clusterColors[clusterId] || '#333' },
        emphasis: { scale: true, label: { show: true, formatter: (params) => params.data.name, position: 'top' } }
      }));

      const option = {
        title: { text: '2D-проекция слов (PCA)', left: 'center' },
        tooltip: { trigger: 'item', formatter: (params) => `${params.data.name}<br/>Кластер: ${params.seriesName}` },
        xAxis: { name: 'PC1', type: 'value', splitLine: { show: false } },
        yAxis: { name: 'PC2', type: 'value', splitLine: { show: false } },
        series: series,
        grid: { containLabel: true, left: '8%', right: '8%', top: '15%', bottom: '10%' },
        legend: { data: series.map(s => s.name), left: 'left' }
      };
      this.scatterChartInstance = echarts.init(chartDom);
      this.scatterChartInstance.setOption(option);
      window.addEventListener('resize', () => this.scatterChartInstance?.resize());
    }
  }
}
</script>

<style scoped>
.analysis-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
  position: relative;
  min-height: 100vh;
}

.loading-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(255, 255, 255, 0.9);
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  z-index: 1000;
  backdrop-filter: blur(5px);
}

.loading-spinner-large {
  border: 5px solid #f3f3f3;
  border-top: 5px solid #3498db;
  border-radius: 50%;
  width: 60px;
  height: 60px;
  animation: spin 1s linear infinite;
  margin-bottom: 20px;
}

.loading-overlay p {
  font-size: 1.2em;
  color: #2c3e50;
  font-weight: 500;
}

.fade-in {
  animation: fadeIn 0.5s ease-in;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.back-button {
  margin-bottom: 20px;
}

.btn-back {
  padding: 10px 20px;
  background: #6c757d;
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 16px;
  transition: all 0.3s;
}

.btn-back:hover {
  background: #5a6268;
  transform: translateY(-2px);
  box-shadow: 0 5px 15px rgba(108, 117, 125, 0.3);
}

.analysis-results {
  background: white;
  border-radius: 15px;
  padding: 30px;
  box-shadow: 0 5px 20px rgba(0,0,0,0.1);
}

.analysis-title {
  color: #2c3e50;
  font-size: 2.2em;
  margin-bottom: 20px;
  padding-bottom: 15px;
  border-bottom: 3px solid #3498db;
}

.catalog-path-breadcrumb {
  background: #f8f9fa;
  padding: 15px;
  border-radius: 8px;
  margin-bottom: 25px;
  font-size: 16px;
  color: #666;
}

.path-part {
  color: #3498db;
  text-decoration: none;
  cursor: pointer;
  transition: color 0.3s;
}

.path-part:hover {
  color: #2980b9;
  text-decoration: underline;
}

.path-separator {
  color: #95a5a6;
  margin: 0 5px;
}

.files-count {
  text-align: center;
  margin-bottom: 30px;
}

.count-badge {
  display: inline-block;
  background: linear-gradient(135deg, #3498db, #2980b9);
  color: white;
  padding: 20px 40px;
  border-radius: 50px;
  margin-bottom: 15px;
}

.count-number {
  font-size: 3em;
  font-weight: bold;
  margin-right: 10px;
}

.count-label {
  font-size: 1.2em;
}

.count-description {
  color: #7f8c8d;
  font-size: 1.1em;
}

.wordcloud-section {
  margin-top: 40px;
}

.wordcloud-section h3 {
  color: #34495e;
  margin-bottom: 20px;
  font-size: 1.5em;
}

.wordcloud-frame {
  background: #f8f9fa;
  border-radius: 10px;
  padding: 20px;
  min-height: 500px;
  display: flex;
  flex-direction: column;
}

.wordcloud-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 500px;
}

.wordcloud-stats {
  margin-top: 20px;
  padding: 15px;
  background: white;
  border-radius: 8px;
  border-left: 4px solid #3498db;
  box-shadow: 0 2px 8px rgba(0,0,0,0.05);
}

.wordcloud-stats p {
  margin: 5px 0;
  color: #555;
  font-size: 1em;
}

.wordcloud-loading {
  text-align: center;
  padding: 50px;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  cursor: pointer;
  padding: 10px 0;
  user-select: none;
}

.section-header h3 {
  margin: 0;
  color: #34495e;
  font-size: 1.3em;
}

.toggle-btn {
  background: none;
  border: none;
  font-size: 1.2em;
  color: #3498db;
  cursor: pointer;
  padding: 5px 10px;
  transition: transform 0.2s;
}

.toggle-btn:hover {
  transform: scale(1.1);
}

.slide-enter-active,
.slide-leave-active {
  transition: all 0.3s ease;
  max-height: 1000px;
  overflow: hidden;
}

.slide-enter-from,
.slide-leave-to {
  max-height: 0;
  opacity: 0;
  margin-top: 0;
  margin-bottom: 0;
}

.similar-catalogs-section {
  margin-top: 40px;
}

.similar-catalogs-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
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
  box-shadow: 0 10px 20px rgba(52, 152, 219, 0.2);
  border-color: #3498db;
}

.similar-catalog-name {
  font-size: 18px;
  margin-bottom: 8px;
  color: #2c3e50;
  font-weight: 600;
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

.similar-catalog-btn:hover:not(:disabled) {
  background: #2980b9;
  transform: translateY(-2px);
  box-shadow: 0 5px 15px rgba(52, 152, 219, 0.3);
}

.similar-catalog-btn:disabled {
  background: #95a5a6;
  cursor: not-allowed;
  opacity: 0.7;
}

.no-similar-catalogs {
  text-align: center;
  padding: 40px;
  color: #95a5a6;
  font-style: italic;
}

.clusters-section {
  margin-top: 40px;
  padding-top: 20px;
  border-top: 2px solid #eee;
}

.clusters-controls {
  background: #f8f9fa;
  padding: 20px;
  border-radius: 10px;
  margin: 20px 0;
  display: flex;
  gap: 20px;
  align-items: center;
  flex-wrap: wrap;
}

.control-group {
  display: flex;
  align-items: center;
  gap: 10px;
}

.control-group label {
  font-weight: 500;
  color: #555;
}

.control-group input[type="range"] {
  width: 200px;
}

.control-group .value {
  min-width: 30px;
  text-align: center;
  font-weight: bold;
  color: #3498db;
}

.cluster-btn {
  background: #3498db;
  color: white;
  border: none;
  padding: 10px 20px;
  border-radius: 5px;
  cursor: pointer;
  font-weight: 500;
  transition: all 0.3s;
}

.cluster-btn:hover:not(:disabled) {
  background: #2980b9;
  transform: translateY(-2px);
}

.cluster-btn:disabled {
  background: #95a5a6;
  cursor: not-allowed;
}

.clusters-stats {
  background: #fff;
  padding: 15px;
  border-radius: 8px;
  margin-bottom: 20px;
  border-left: 4px solid #3498db;
  font-size: 0.9em;
  color: #666;
}

.clusters-container {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
  gap: 25px;
}

.cluster-card {
  background: white;
  border-radius: 10px;
  padding: 0;
  box-shadow: 0 3px 10px rgba(0,0,0,0.1);
  border: 1px solid #e0e0e0;
  transition: all 0.3s;
  overflow: hidden;
}

.cluster-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 5px 20px rgba(52, 152, 219, 0.15);
  border-color: #3498db;
}

.cluster-header {
  background: linear-gradient(135deg, #3498db, #2980b9);
  padding: 15px 20px;
  color: white;
}

.cluster-header h4 {
  margin: 0;
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 1.2em;
  color: white;
}

.cluster-header .cluster-size {
  font-size: 0.8em;
  font-weight: normal;
  color: rgba(255, 255, 255, 0.9);
}

.cluster-body {
  padding: 20px;
}

.cluster-words-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 5px;
  padding: 0 0 15px 0;
  border-bottom: 1px solid #eee;
  min-height: 60px;
  align-items: center;
}

.cluster-word-item {
  display: inline-flex;
  align-items: center;
  cursor: pointer;
  transition: all 0.2s;
}

.cluster-word {
  color: #2c3e50;
  font-size: 14px;
  padding: 2px 4px;
  transition: all 0.2s;
}

.cluster-word-item:hover .cluster-word {
  color: #3498db;
  text-decoration: underline;
  transform: scale(1.05);
}

.word-separator {
  color: #ccc;
  margin: 0 4px;
  font-size: 12px;
}

.cluster-top-words {
  margin-top: 15px;
}

.cluster-top-words h5 {
  color: #7f8c8d;
  font-size: 0.9em;
  margin: 0 0 10px 0;
}

.top-words-list {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.top-word-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 5px 0;
  border-bottom: 1px dashed #eee;
}

.top-word-item .word {
  font-weight: 500;
  color: #2c3e50;
}

.top-word-item .frequency {
  background: #f0f0f0;
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 0.8em;
  color: #666;
}

.loading-state,
.error-state {
  text-align: center;
  padding: 60px;
  background: white;
  border-radius: 15px;
  box-shadow: 0 5px 20px rgba(0,0,0,0.1);
}

.loading-spinner {
  border: 4px solid #f3f3f3;
  border-top: 4px solid #3498db;
  border-radius: 50%;
  width: 50px;
  height: 50px;
  animation: spin 1s linear infinite;
  margin: 0 auto 20px;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.error-message {
  color: #e74c3c;
  font-size: 1.2em;
  margin-bottom: 20px;
}

.btn-retry {
  padding: 10px 30px;
  background: #3498db;
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 16px;
  transition: all 0.3s;
}

.btn-retry:hover {
  background: #2980b9;
  transform: translateY(-2px);
  box-shadow: 0 5px 15px rgba(52, 152, 219, 0.3);
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

.silhouette-hint, .noise-hint {
  font-size: 0.8em;
  color: #7f8c8d;
  margin-left: 8px;
}
.trend-section {
  margin-top: 40px;
  padding-top: 20px;
  border-top: 2px solid #eee;
}
.trend-content {
  margin-top: 20px;
}
.trend-controls {
  display: flex;
  gap: 10px;
  align-items: center;
  flex-wrap: wrap;
}
.trend-controls select {
  padding: 8px;
  border-radius: 5px;
  border: 1px solid #ccc;
}
.trend-controls button {
  background: #3498db;
  color: white;
  border: none;
  border-radius: 5px;
  cursor: pointer;
}

.cluster-keywords {
  margin-top: 12px;
  font-size: 0.9rem;
  color: #2c3e50;
  font-weight: normal;
  letter-spacing: normal;
  opacity: 1;
}
.cluster-keywords strong {
  font-weight: 600;
  color: #2c3e50;
}

.viz-layout {
  display: flex;
  gap: 20px;
  margin-top: 20px;
  flex-wrap: wrap;
}

.viz-chart-container {
  flex: 3;
  min-width: 300px;
}

.viz-keywords-panel {
  flex: 1;
  min-width: 220px;
  background: #fafafa;
  border-radius: 10px;
  padding: 15px;
  border: 1px solid #e0e0e0;
  max-height: 500px;
  overflow-y: auto;
}

.viz-keywords-panel h4 {
  margin-top: 0;
  margin-bottom: 15px;
  color: #2c3e50;
  font-size: 1.1rem;
}

.cluster-keywords-card {
  margin-bottom: 20px;
  padding-bottom: 10px;
  border-bottom: 1px solid #eee;
}

.cluster-title {
  font-weight: 700;
  font-size: 1rem;
  color: #1e2a36;
  margin-bottom: 10px;
  padding-left: 12px;
  border-left: 4px solid;
  letter-spacing: 0.3px;
}

.cluster-keywords-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.keyword-badge {
  background: #f0f0f0;
  padding: 4px 8px;
  border-radius: 12px;
  font-size: 0.8rem;
  color: #2c3e50;
}

@keyframes spinner-border {
  to { transform: rotate(360deg); }
}

.me-2 {
  margin-right: 0.5rem;
}

@media (max-width: 768px) {
  .analysis-container {
    padding: 10px;
  }

  .analysis-results {
    padding: 15px;
  }

  .analysis-title {
    font-size: 1.8em;
  }

  .clusters-controls {
    flex-direction: column;
    align-items: stretch;
  }

  .clusters-container {
    grid-template-columns: 1fr;
  }

  .similar-catalogs-list {
    grid-template-columns: 1fr;
  }

  .control-group {
    flex-direction: column;
    align-items: flex-start;
  }

  .control-group input[type="range"] {
    width: 100%;
  }

  .count-badge {
    padding: 15px 25px;
  }

  .count-number {
    font-size: 2.5em;
  }

  .count-label {
    font-size: 1em;
  }
}

@media (max-width: 480px) {
  .section-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 10px;
  }

  .cluster-words-list {
    gap: 5px;
  }

  .cluster-word {
    font-size: 12px;
  }

  .word-separator {
    margin: 0 2px;
  }

  .clusters-viz-section {
    margin-top: 40px;
    padding-top: 20px;
    border-top: 2px solid #eee;
  }
  .viz-container {
    width: 100%;
    min-height: 500px;
    margin-top: 20px;
  }
}
</style>
