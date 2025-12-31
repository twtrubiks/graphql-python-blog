<script lang="ts">
	import { page } from '$app/state';

	// Svelte 5: 使用 $derived rune
	// page.status 是 HTTP 狀態碼，page.error 是錯誤物件
	let statusCode = $derived(page.status);
	let message = $derived(page.error?.message || '發生未知錯誤');
</script>

<div class="flex flex-col items-center justify-center min-h-[50vh] text-center">
	<h1 class="text-6xl font-bold text-gray-300 mb-4">{statusCode}</h1>
	<h2 class="text-2xl font-semibold mb-2">糟糕！出現問題了</h2>
	<p class="text-gray-600 mb-6 max-w-md">{message}</p>

	<div class="flex gap-4">
		<a href="/" class="btn btn-primary">
			返回首頁
		</a>
		<button onclick={() => history.back()} class="btn btn-secondary">
			返回上一頁
		</button>
	</div>
</div>