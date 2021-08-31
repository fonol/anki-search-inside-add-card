import Vue from 'vue'

Vue.config.productionTip = false

window.Vue = Vue;

Vue.component('siac-md-tree', require('@/components/MDTree.vue').default);
Vue.component('siac-md-tree-node', require('@/components/MDTreeNode.vue').default);