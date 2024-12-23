import {createRouter, createWebHashHistory, RouteRecordRaw} from 'vue-router';
import Home from '../pages/home.vue';

const routes: RouteRecordRaw[] = [
    {
        path: '/',
        name: 'Home',
        component: Home,
        children: [
            {
                path: '',
                redirect: '/mode',
            },
            {
                path: '/mode',
                name: 'Mode',
                meta: {
                    title: '登录',
                },
                component: () => import(/* webpackChunkName: "mode" */ '../pages/mode.vue'),
            },
           
            {
                // path: '/interaction',
                path: '/conference',
                name: 'Interaction',
                meta: {
                    title: 'On Meeting',
                    permiss: '2',
                },
                component: () => import(/* webpackChunkName: "mode" */ '../pages/conference.vue'),
            },
        ],
    },
    {
        path: '/403',
        name: '403',
        meta: {
            title: '没有权限',
        },
        component: () => import(/* webpackChunkName: "403" */ '../components/403.vue'),
    },
];

const router = createRouter({
    history: createWebHashHistory(),
    routes,
});

export default router;