import { fileURLToPath, URL } from 'node:url';

import vue from '@vitejs/plugin-vue';
import { defineConfig } from 'vite';

/** 模块 id 是否位于 node_modules/<pkg>/ 下（兼容 pnpm 的 .pnpm/<pkg>@x/node_modules/<pkg>/ 布局与 Windows 分隔符）。 */
function inPackage(id: string, pkg: string): boolean {
  return id.replace(/\\/g, '/').includes(`/node_modules/${pkg}/`);
}

// base './'：同一份 dist 既能被 webui 托管在根路径，也能被桌面壳经 tauri
// 协议从资源目录离线加载（方案 §4 D1 / §11.3）。路由是 hash 模式，相对
// base 不会破坏深链。
export default defineConfig({
  base: './',
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    port: 5173,
    // 开发期反代到本机 Bot 进程（WEBUI_SERVE_DIST=false 时后端只出 API）
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8080',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    // 首屏分包（M5）：vuetify/apexcharts 体量大且极少变动，独立成块后
    // 业务代码更新不再打穿长缓存。Vite 8 改用 Rolldown：manualChunks 不再
    // 支持对象写法（函数写法也已 deprecated），改为 codeSplitting.groups，
    // 按 node_modules 路径归组（pnpm 布局下包目录同样以 node_modules/<pkg>/ 结尾）。
    // apexcharts 的 SSR 构建（apexcharts.ssr.*）只被 vue3-apexcharts 动态 import，
    // 浏览器里不会走到；排除在外让它保持懒加载，否则首屏多载 ~870 KB。
    rolldownOptions: {
      output: {
        codeSplitting: {
          groups: [
            { name: 'vuetify', test: (id) => inPackage(id, 'vuetify') },
            {
              name: 'charts',
              test: (id) =>
                inPackage(id, 'vue3-apexcharts')
                || (inPackage(id, 'apexcharts') && !/apexcharts\.ssr\./.test(id)),
            },
          ],
        },
      },
    },
  },
});
