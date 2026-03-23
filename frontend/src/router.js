import { createRouter, createWebHashHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'Home',
    component: () => import('./views/Home.vue'),
  },
  {
    path: '/account-profiles',
    name: 'AccountProfiles',
    component: () => import('./views/AccountProfiles.vue'),
  },
  {
    path: '/account-list',
    name: 'AccountList',
    component: () => import('./views/AccountList.vue'),
  },
  {
    path: '/articles',
    name: 'Articles',
    component: () => import('./views/Articles.vue'),
  },
  {
    path: '/downloads',
    name: 'Downloads',
    component: () => import('./views/Downloads.vue'),
  },
  {
    path: '/debug',
    name: 'Debug',
    component: () => import('./views/Debug.vue'),
  },
  {
    path: '/settings',
    name: 'Settings',
    component: () => import('./views/Settings.vue'),
  },
]

const router = createRouter({
  history: createWebHashHistory(),
  routes,
})

export default router
