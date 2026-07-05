import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';
import houdini from 'houdini/vite';
import tailwindcss from '@tailwindcss/vite';

export default defineConfig({
	// vite 8 起 postcss.config.js 的 @tailwindcss/postcss 不再被載入，改用官方 vite plugin
	plugins: [tailwindcss(), houdini(), sveltekit()],
	server: {
		port: 5173,
		host: true,
		watch: {
			// 忽略 node_modules 和 dist，但不要忽略 .houdini 和 .svelte-kit
			// ignored: ['**/node_modules/**', '**/dist/**'],
			// 使用輪詢方式避免 EMFILE 錯誤
			usePolling: true,
			// 輪詢間隔（毫秒）
			interval: 1000
		}
	}
});