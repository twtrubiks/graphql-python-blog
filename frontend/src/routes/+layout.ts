import type { LayoutLoad } from './$types';

// 預設啟用 SSR 和 CSR
export const ssr = true;
export const csr = true;

// 預載入資料設定
export const prerender = false;

// 載入函數（如果需要全局資料）
export const load: LayoutLoad = async ({ url, fetch }) => {
	// 可以在這裡載入全局需要的資料
	// 例如：用戶資訊、網站配置等

	return {
		// 返回當前 URL 資訊
		url: url.pathname
	};
};