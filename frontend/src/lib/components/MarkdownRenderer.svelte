<script lang="ts">
	import { marked } from 'marked';
	import DOMPurify from 'dompurify';
	import { browser } from '$app/environment';

	interface Props {
		content: string;
		class?: string;
	}

	let { content, class: className = '' }: Props = $props();

	// 配置 marked
	marked.setOptions({
		breaks: true,
		gfm: true
	});

	// marked 不會消毒 HTML，必須用 DOMPurify 清除惡意內容（防止儲存型 XSS）
	// DOMPurify 需要瀏覽器 DOM，SSR 時輸出空字串，待客戶端 hydration 後渲染
	let html = $derived(
		browser ? DOMPurify.sanitize(marked.parse(content || '') as string) : ''
	);
</script>

<div class="prose prose-lg max-w-none prose-headings:font-bold prose-a:text-primary-600 hover:prose-a:text-primary-800 prose-code:before:content-none prose-code:after:content-none prose-pre:bg-gray-900 prose-pre:text-gray-100 {className}">
	{@html html}
</div>

<style>
	/* 只針對行內程式碼（不在 pre 內的 code）設定背景樣式 */
	:global(.prose code:not(pre code)) {
		background-color: rgb(243 244 246);
		padding: 0.125rem 0.25rem;
		border-radius: 0.25rem;
	}
</style>
