<template>
  <div id="wrapper">
    <nav class="navbar is-dark">
      <div class="navbar-brand">
        <a class="navbar-burger" aria-label="menu" aria-expanded="false" data-target="navbar-menu">
          <span aria-hidden="true"></span>
          <span aria-hidden="true"></span>
          <span aria-hidden="true"></span>
        </a>
      </div>

      <div class="navbar-menu" id="navbar-menu">
        <div class="navbar-start">

          <router-link to="/" class="navbar-item" :class="{ 'is-active': $route.path === '/' }">
            Главная
          </router-link>
          <router-link
            v-if="hasFile"
            to="/catalogs"
            class="navbar-item"
            :class="{ 'is-active': $route.path === '/catalogs' }"
          >
            Каталоги
          </router-link>
          <router-link
           to="/keyword-search"
           class="navbar-item">
           Поиск по словам
          </router-link>
        </div>
      </div>
    </nav>

    <section class="section">
      <div class="container">
        <router-view/>
      </div>
    </section>

    <footer class="footer">
      <div class="container">
        <p class="has-text-centered">Copyright @2026</p>
      </div>
    </footer>
  </div>
</template>

<script>
import { mapState } from 'pinia'
import { useUploadStore } from '@/stores/uploaded'

export default {
  name: 'App',
  computed: {
    ...mapState(useUploadStore, ['hasFile', 'catalogsCount'])
  },
  watch: {
    hasFile(newValue) {
      if (newValue) {
        console.log('Файл загружен, перенаправляем на страницу каталогов')
        this.$router.push('/catalogs')
      }
    }
  },
  mounted() {
    console.log('App mounted')
  }
}
</script>

<style>
  @import "bulma/css/bulma.min.css";
  html, body {
    margin: 0;
    padding: 0;
    width: 100%;
  }

  #app, #wrapper {
    width: 100%;
    min-height: 100vh;
    display: flex;
    flex-direction: column;
  }

  .navbar {
    width: 100%;
    padding-left: 0;
    padding-right: 0;
    border-radius: 0;
  }

  /* Левая часть меню */
  .navbar-start {
    margin-left: 0;
    padding-left: 0.75rem;
  }

  .navbar-item {
    transition: all 0.2s ease;
    position: relative;
  }

  .navbar-item::after {
    content: '';
    position: absolute;
    bottom: 0;
    left: 50%;
    width: 0;
    height: 2px;
    transition: all 0.2s ease;
    transform: translateX(-50%);
  }

  .navbar-item:hover::after {
    width: 80%;
  }

  .section {
    width: 100%;
    padding-left: 0;
    padding-right: 0;
    flex: 1;
    background: #f5f5f5;
  }

  .footer {
    width: 100%;
    padding-left: 0;
    padding-right: 0;
    border-radius: 0;
  }

  @media (max-width: 768px) {
    .wordcloud-frame {
      min-height: 400px;
      padding: 10px;
    }
    .wordcloud-stats p {
      font-size: 0.9em;
    }
  }
</style>
