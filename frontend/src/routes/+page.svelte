<script lang="ts">
	import { PUBLIC_APP_NAME, PUBLIC_APP_DESCRIPTION } from '$env/static/public';
	import { GetPostsStore, PostPublishedStore } from '$houdini';
	import { notifications } from '$lib/stores/notifications.svelte';
	import { onMount, onDestroy } from 'svelte';
	import type { PageData } from './$types';

	// Svelte 5: 使用 $props 接收資料
	let { data }: { data: PageData } = $props();

	// 建立 Houdini stores
	const postsStore = new GetPostsStore();
	const postPublishedStore = new PostPublishedStore();

	// Svelte 5: 使用 $state rune
	let isLoading = $state(true);
	let postsData = $state<any>(null);

	// Subscription 狀態管理
	let subscriptionStatus = $state<'idle' | 'connecting' | 'connected' | 'error'>('idle');
	let isSubscriptionActive = $state(false);
	let lastPostId = $state<string | null>(null);
	let storeUnsubscribe: (() => void) | null = null;

	// 載入文章資料
	$effect(() => {
		loadPosts();
	});

	// 啟動 subscription
	$effect(() => {
		// 等待首次載入完成才啟動 subscription
		if (isLoading) return;

		// 避免重複建立 subscription
		if (isSubscriptionActive) return;

		console.log('[PostPublished] Starting subscription...');
		subscriptionStatus = 'connecting';
		isSubscriptionActive = true;

		try {
			postPublishedStore.listen().then(() => {
				subscriptionStatus = 'connected';
				console.log('[PostPublished] Successfully connected');
			}).catch((error) => {
				console.error('[PostPublished] Failed to connect:', error);
				subscriptionStatus = 'error';
				isSubscriptionActive = false;
			});
		} catch (error) {
			console.error('[PostPublished] Error starting subscription:', error);
			subscriptionStatus = 'error';
			isSubscriptionActive = false;
		}
	});

	// 監聽 subscription store 資料變化
	onMount(() => {
		storeUnsubscribe = postPublishedStore.subscribe((value: any) => {
			if (!value) return;

			// 檢查是否有新文章
			if (value.data?.postPublished) {
				const newPost = value.data.postPublished;

				// 避免重複處理同一篇文章
				if (newPost.id !== lastPostId) {
					lastPostId = newPost.id;
					console.log('[PostPublished] New post received:', newPost.title);
					handleNewPost(newPost);
				}
			}

			// 處理錯誤
			if (value.error) {
				console.error('[PostPublished] Error:', value.error);
				subscriptionStatus = 'error';
			}
		});

		return () => {
			if (storeUnsubscribe) {
				storeUnsubscribe();
				storeUnsubscribe = null;
			}
		};
	});

	onDestroy(async () => {
		// 元件銷毀時停止訂閱
		if (storeUnsubscribe) {
			storeUnsubscribe();
			storeUnsubscribe = null;
		}
		if (isSubscriptionActive && postPublishedStore.unlisten) {
			await postPublishedStore.unlisten();
			isSubscriptionActive = false;
			subscriptionStatus = 'idle';
		}
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

	// 處理新發布的文章
	function handleNewPost(newPost: any) {
		console.log('[PostPublished] Processing new post:', newPost);

		// 檢查文章是否已存在於列表中
		const exists = postsData?.edges?.some((edge: any) => edge.node.id === newPost.id);
		if (exists) {
			console.log('[PostPublished] Post already exists, skipping');
			return;
		}

		// 將新文章加入列表頂部（保持 6 篇）
		postsData = {
			...postsData,
			edges: [
				{ node: newPost },
				...(postsData?.edges || []).slice(0, 5)
			]
		};

		// 顯示通知
		notifications.info(
			`${newPost.author?.username || '某人'} 發布了新文章：${newPost.title}`,
			{
				duration: 6000,
				link: `/posts/${newPost.slug}`
			}
		);
	}

	// Svelte 5: 使用 $derived 處理衍生狀態
	let featuredPosts = $derived(
		postsData?.edges?.map((edge: any) => ({
			id: edge.node.id,
			title: edge.node.title,
			slug: edge.node.slug,
			excerpt: edge.node.excerpt || '',
			author: edge.node.author?.username || '未知作者',
			totalComments: edge.node.totalComments || 0,
			likesCount: edge.node.likesCount || 0
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
		<div class="flex items-center justify-between mb-6">
			<h2 class="text-3xl font-bold">精選文章</h2>

			<!-- Subscription 狀態指示器 -->
			<div class="flex items-center gap-2 text-sm">
				{#if subscriptionStatus === 'connecting'}
					<div class="flex items-center gap-2 text-gray-500">
						<div class="animate-spin w-4 h-4 border-2 border-gray-300 border-t-gray-600 rounded-full"></div>
						<span>即時更新連線中...</span>
					</div>
				{:else if subscriptionStatus === 'connected'}
					<div class="flex items-center gap-2 text-green-600">
						<div class="w-2 h-2 bg-green-600 rounded-full animate-pulse"></div>
						<span>即時更新已連線</span>
					</div>
				{:else if subscriptionStatus === 'error'}
					<div class="flex items-center gap-2 text-red-500">
						<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
						</svg>
						<span>即時更新暫時無法使用</span>
					</div>
				{/if}
			</div>
		</div>
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