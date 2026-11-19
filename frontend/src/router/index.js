// ========================================
// File:
// Pulsar/frontend/src/router/index.js
//
// Description:
// Define routes and protect authenticated pages
//
// Author: MHKolahi@gmail.com
// In collaboration with GPT4 Chat Assistant: Bahram
// ========================================
import {
  createRouter,
  createWebHistory
} from 'vue-router'
import login_page from '../pages/login_page.vue'
import register_page from '../pages/register_page.vue'
import Profile from '../views/profile.vue'
import {
  getAuthToken
} from '@/utils/authToken'

const routes = [
  {
    path: '/',
    redirect: '/login'
  },
  {
    path: '/login',
    name: 'Login',
    component: login_page
  },
  {
    path: '/register',
    name: 'Register',
    component: register_page
  },
  {
    path: '/profile',
    name: 'Profile',
    component: Profile,
    meta: {
      requiresAuth: true
    }
  },
  {
    path: '/profile/create',
    name: 'ProfileCreate',
    component: () =>
      import('@/pages/profile_create_page.vue'),
    meta: {
      requiresAuth: true
    }
  },
  {
    path: '/dashboard',
    name: 'dashboard_page',
    component: () =>
      import('@/pages/dashboard_page.vue'),
    meta: {
      requiresAuth: true
    }
  },
  // ----------------------------------------
  // Dynamic Page Runtime
  // ----------------------------------------
  {
    path: '/pages/:page_key',
    name: 'dynamic-page',
    component: () =>
      import(
        '@/components/pages/dynamic_page.vue'
      ),
    props: route => ({
      pageKey:
        route.params.page_key
    }),
    meta: {
      requiresAuth: true
    }
  }
]

const router = createRouter({
  history: createWebHistory(
    import.meta.env.BASE_URL
  ),
  routes
})

// ----------------------------------------
// Navigation Guard
// ----------------------------------------
router.beforeEach(
  (to, from, next) => {
    const requiresAuth =
      to.matched.some(
        record =>
          record.meta.requiresAuth
      )

    const token =
      getAuthToken()

    if (
      requiresAuth &&
      !token
    ) {
      next('/login')
      return
    }

    if (
      to.path === '/login' &&
      token
    ) {
      next('/dashboard')
      return
    }

    next()
  }
)

// ----------------------------------------
// Important Learning Points
// ----------------------------------------
// 1. Dynamic pages require authentication.
// 2. Dashboard and profile creation require authentication.
// 3. Route query data remains available to dynamic_page.vue.
// 4. selected_record and context are transported through the route
//    without router-level interpretation.
// 5. primary_key, where_clause, and parm[n] semantics do not belong
//    to the router.
// 6. Authentication is validated through the centralized in-memory JWT.
// 7. The router does not read or write the JWT directly from localStorage.
// 8. authToken.js is the shared authentication boundary for the frontend.

export default router