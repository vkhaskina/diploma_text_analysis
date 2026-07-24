<template>
  <div class="wordcloud-component">
    <div ref="wordcloudContainer" class="wordcloud-container"></div>
    <div v-if="!wordsData || wordsData.length === 0" class="wordcloud-empty">
      <p>Нет данных для отображения облака слов</p>
    </div>
  </div>
</template>

<script>
import * as d3 from 'd3'
import cloud from 'd3-cloud'

export default {
  name: 'WordCloud',

  props: {
    wordsData: {
      type: Array,
      default: () => []
    },
    width: {
      type: Number,
      default: 800
    },
    height: {
      type: Number,
      default: 400
    },
    minFontSize: {
      type: Number,
      default: 12
    },
    maxFontSize: {
      type: Number,
      default: 60
    },
    colors: {
      type: Array,
      default: () => [
        '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
        '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf',
        '#3498db', '#e74c3c', '#2ecc71', '#f39c12', '#9b59b6'
      ]
    }
  },

  data() {
    return {
      isLoading: true
    }
  },

  watch: {
    wordsData: {
      handler() {
        this.generateWordCloud()
      },
      deep: true
    },
    width() {
      this.generateWordCloud()
    },
    height() {
      this.generateWordCloud()
    }
  },

  mounted() {
    this.generateWordCloud()
    window.addEventListener('resize', this.handleResize)
  },

  beforeUnmount() {
    window.removeEventListener('resize', this.handleResize)
  },

  methods: {
    handleResize() {
      clearTimeout(this.resizeTimer)
      this.resizeTimer = setTimeout(() => {
        this.generateWordCloud()
      }, 250)
    },

    generateWordCloud() {
      if (!this.$refs.wordcloudContainer) return

      const container = this.$refs.wordcloudContainer
      const containerWidth = container.clientWidth || this.width
      const containerHeight = container.clientHeight || this.height

      // Очищаем контейнер
      container.innerHTML = ''

      if (!this.wordsData || this.wordsData.length === 0) {
        return
      }

      this.isLoading = true

      // Подготавливаем данные для облака
      const words = this.wordsData.map(w => ({
        text: w.text,
        size: w.weight || w.size || 20,
        weight: w.weight || w.count || w.size || 20
      }))

      // Нормализуем веса
      const maxWeight = Math.max(...words.map(w => w.weight))
      const normalizedWords = words.map(w => ({
        ...w,
        size: this.minFontSize + (w.weight / maxWeight) * (this.maxFontSize - this.minFontSize)
      }))

      // Настраиваем и запускаем d3-cloud
      const layout = cloud()
        .size([containerWidth, containerHeight])
        .words(normalizedWords.map(w => ({
          text: w.text,
          size: w.size,
          weight: w.weight
        })))
        .padding(5)
        .rotate(() => 0) // Все слова горизонтально
        .font('Arial')
        .fontSize(d => d.size)
        .on('end', this.drawWordCloud)

      layout.start()
    },

    drawWordCloud(words) {
      const container = this.$refs.wordcloudContainer
      if (!container) return

      const containerWidth = container.clientWidth || this.width
      const containerHeight = container.clientHeight || this.height

      // Создаем SVG элемент
      const svg = d3.select(container)
        .append('svg')
        .attr('width', containerWidth)
        .attr('height', containerHeight)
        .attr('viewBox', `0 0 ${containerWidth} ${containerHeight}`)
        .style('display', 'block')
        .style('margin', '0 auto')

      // Создаем группу с трансляцией в центр
      const g = svg.append('g')
        .attr('transform', `translate(${containerWidth / 2},${containerHeight / 2})`)

      // Рисуем слова - БЕЗ ОБРАБОТЧИКОВ СОБЫТИЙ
      g.selectAll('text')
        .data(words)
        .enter()
        .append('text')
        .style('font-size', d => d.size + 'px')
        .style('font-family', 'Arial, sans-serif')
        .style('fill', (d, i) => this.colors[i % this.colors.length])
        .style('cursor', 'default')
        .style('transition', 'none')
        .attr('text-anchor', 'middle')
        .attr('transform', d => `translate(${d.x}, ${d.y}) rotate(${d.rotate})`)
        .text(d => d.text)

      this.isLoading = false
    }
  }
}
</script>

<style scoped>
.wordcloud-component {
  width: 100%;
  height: 100%;
  min-height: 400px;
  position: relative;
}

.wordcloud-container {
  width: 100%;
  height: 100%;
  min-height: 400px;
  background: white;
  border-radius: 8px;
  overflow: hidden;
}

.wordcloud-empty {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  color: #95a5a6;
  font-style: italic;
  text-align: center;
}
</style>
