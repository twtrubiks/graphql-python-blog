<script lang="ts">
	import { PUBLIC_APP_NAME, PUBLIC_APP_DESCRIPTION } from '$env/static/public';
	import { GetPostsStore } from '$houdini';
	import type { PageData } from './$types';

	// Svelte 5: 使用 $props 接收資料
	let { data }: { data: PageData } = $props();

	// 建立 Houdini store
	const postsStore = new GetPostsStore();

	// Svelte 5: 使用 $state rune
	let isLoading = $state(true);
	let postsData = $state<any>(null);

	// 載入文章資料
	$effect(() => {
		loadPosts();
	});

	async function loadPosts() {
		isLoading = true;
		try {
			const result = await postsStore.fetch({
				variables: {
					page: 1,
					limit: 6 // 首頁顯示 6 篇精選文章
				}
			});
			postsData = result.data?.posts;
		} catch (error) {
			console.error('Failed to load posts:', error);
		} finally {
			isLoading = false;
		}
	}

	// Svelte 5: 使用 $derived 處理衍生狀態
	let featuredPosts = $derived(
		postsData?.edges?.map(edge => ({
			id: edge.node.id,
			title: edge.node.title,
			slug: edge.node.slug,
			excerpt: edge.node.excerpt || '',
			author: edge.node.author.username,
			totalComments: edge.node.totalComments,
			likesCount: edge.node.likesCount
		})) || []
	);
</script>

<svelte:head>
	<title>{PUBLIC_APP_NAME} - 首頁</title>
	<meta name="description" content={PUBLIC_APP_DESCRIPTION} />
</svelte:head>

<div class="space-y-12">
	<!-- Hero Section -->
	<section class="text-center py-12">
		<h1 class="text-5xl font-bold mb-4 bg-gradient-to-r from-primary-600 to-primary-800 bg-clip-text text-transparent">
			歡迎來到 {PUBLIC_APP_NAME}
		</h1>
		<p class="text-xl text-gray-600 mb-8 max-w-2xl mx-auto">
			{PUBLIC_APP_DESCRIPTION}
		</p>
		<div class="flex gap-4 justify-center">
			<a href="/posts" class="btn btn-primary text-base">
				瀏覽文章
			</a>
			<a href="/posts/new" class="btn btn-secondary text-base">
				開始寫作
			</a>
		</div>
	</section>

	<!-- Featured Posts -->
	<section>
		<h2 class="text-3xl font-bold mb-6">精選文章</h2>
		{#if isLoading}
			<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
				{#each [1, 2, 3] as _}
					<div class="card animate-pulse">
						<div class="h-4 bg-gray-200 rounded mb-3"></div>
						<div class="h-3 bg-gray-200 rounded mb-2"></div>
						<div class="h-3 bg-gray-200 rounded w-2/3"></div>
					</div>
				{/each}
			</div>
		{:else if featuredPosts.length > 0}
			<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
				{#each featuredPosts as post}
					<article class="card hover:shadow-lg transition-shadow">
						<h3 class="text-xl font-semibold mb-2">
							<a href="/posts/{post.slug || post.id}" class="hover:text-primary-600 transition-colors">
								{post.title}
							</a>
						</h3>
						<p class="text-gray-600 mb-3">{post.excerpt}</p>
						<div class="flex items-center justify-between text-sm text-gray-500">
							<div class="flex items-center gap-4">
								<span>作者：{post.author}</span>
								<span>💬 {post.totalComments}</span>
								<span>👍 {post.likesCount}</span>
							</div>
							<a href="/posts/{post.slug || post.id}" class="link text-primary-600">
								閱讀更多 →
							</a>
						</div>
					</article>
				{/each}
			</div>
		{:else}
			<div class="text-center py-8">
				<p class="text-gray-600 mb-4">目前還沒有文章</p>
				<a href="/posts/new" class="btn btn-primary">撰寫第一篇文章</a>
			</div>
		{/if}
	</section>

	<!-- Features Section -->
	<section class="bg-gray-50 -mx-4 px-4 py-12 rounded-lg">
		<h2 class="text-3xl font-bold mb-8 text-center">平台特色</h2>
		<div class="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-4xl mx-auto">
			<div class="text-center">
				<div class="text-4xl mb-3">⚡</div>
				<h3 class="text-lg font-semibold mb-2">極速效能</h3>
				<p class="text-gray-600">使用 SvelteKit SSR 提供最佳載入速度</p>
			</div>
			<div class="text-center">
				<div class="text-4xl mb-3">🔥</div>
				<h3 class="text-lg font-semibold mb-2">即時更新</h3>
				<p class="text-gray-600">透過 GraphQL Subscriptions 實現即時互動</p>
			</div>
			<div class="text-center">
				<div class="text-4xl mb-3">📱</div>
				<h3 class="text-lg font-semibold mb-2">響應式設計</h3>
				<p class="text-gray-600">完美支援各種裝置尺寸</p>
			</div>
		</div>
	</section>
</div>