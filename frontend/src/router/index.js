import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '../views/HomeView.vue'
import CatalogsView from '../views/CatalogsView.vue'
import CatalogAnalysys from '../views/CatalogAnalysys.vue'
import KeywordSearch from '@/views/KeywordSearch.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'home',
      component: HomeView,
    },
    {
      path: '/catalogs',
      name: 'catalogs',
      component: CatalogsView
    },
    {
      path: '/analysis',
      name: 'analysis',
      component: CatalogAnalysys
    },
    {
      path: '/keyword-search',
      name: 'keyword-search',
      component: KeywordSearch
    },
    {
      path: '/document/:id',
      name: 'document-analysis',
      component: CatalogAnalysys,
      props: true
    },
    {
      path: '/about',
      name: 'about',

      component: () => import('../views/AboutView.vue'),
    },
  ],
})

export default router
