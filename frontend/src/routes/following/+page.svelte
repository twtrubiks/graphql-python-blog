<script lang="ts">
	import { GetFollowingPostsStore, FollowedUserPostedStore } from '$houdini';
	import { goto } from '$app/navigation';
	import { auth } from '$lib/stores/auth.svelte';
	import { notifications } from '$lib/stores/notifications.svelte';
	import { onMount, onDestroy } from 'svelte';

	const postsStore = new GetFollowingPostsStore();

	let currentPage = $state(1);
	let limit = $state(10);
	let isLoading = $state(true);
	let postsData = $state<any>(null);

	// Subscription 狀態
	let followedPostsStore: FollowedUserPostedStore | null = null;
	let isSubscriptionActive = $state(false);
	let subscriptionStatus = $state<'idle' | 'connecting' | 'connected' | 'error'>('idle');
	let lastPostId: string | null = null;
	let storeUnsubscribe: (() => void) | null = null;

	// 檢查登入狀態
	$effect(() => {
		if (!auth.isAuthenticated) {
			notifications.warning('請先登入才能查看追蹤動態');
			goto('/login');
		}
	});

	// 載入文章
	$effect(() => {
		if (auth.isAuthenticated) {
			loadPosts();
		}
	});

	onMount(() => {
		if (!auth.isAuthenticated || !auth.user?.id) return;

		// 初始化 subscription
		followedPostsStore = new FollowedUserPostedStore();

		// 監聽 subscription 資料
		storeUnsubscribe = followedPostsStore.subscribe((value: any) => {
			if (!value || !isSubscriptionActive) return;

			if (value.data?.followedUserPosted) {
				const newPost = value.data.followedUserPosted;

				// 避免重複處理
				if (newPost.id !== lastPostId) {
					lastPostId = newPost.id;
					handleNewPost(newPost);
				}
			}

			if (value.error) {
				console.error('[FollowedUserPosted] Error:', value.error);
				subscriptionStatus = 'error';
			}
		});

		// 啟動 subscription
		startSubscription();

		return () => {
			if (storeUnsubscribe) {
				storeUnsubscribe();
				storeUnsubscribe = null;
			}
		};
	});

	onDestroy(async () => {
		if (storeUnsubscribe) {
			storeUnsubscribe();
			storeUnsubscribe = null;
		}
		if (followedPostsStore && isSubscriptionActive) {
			await followedPostsStore.unlisten();
			isSubscriptionActive = false;
			subscriptionStatus = 'idle';
		}
	});

	async function startSubscription() {
		if (!followedPostsStore || isSubscriptionActive || !auth.user?.id) return;

		console.log('[FollowedUserPosted] Starting subscription...');
		subscriptionStatus = 'connecting';
		isSubscriptionActive = true;

		try {
			await followedPostsStore.listen({
				userId: auth.user.id
			});
			subscriptionStatus = 'connected';
			console.log('[FollowedUserPosted] Successfully connected');
		} catch (error) {
			console.error('[FollowedUserPosted] Failed to connect:', error);
			subscriptionStatus = 'error';
			isSubscriptionActive = false;
		}
	}

	function handleNewPost(newPost: any) {
		console.log('[FollowedUserPosted] New post received:', newPost);

		// 檢查是否已存在
		const exists = postsData?.edges?.some((edge: any) => edge.node.id === newPost.id);
		if (exists) return;

		// 將新文章加入列表頂部
		postsData = {
			...postsData,
			edges: [{ node: newPost }, ...(postsData?.edges || []).slice(0, limit - 1)],
			pageInfo: {
				...postsData?.pageInfo,
				totalCount: (postsData?.pageInfo?.totalCount || 0) + 1
			}
		};

		// 顯示通知
		const authorName = newPost.author?.fullName || newPost.author?.username || '某用戶';
		notifications.info(`${authorName} 發布了新文章：${newPost.title}`, {
			duration: 6000,
			link: {
				text: '立即查看',
				href: `/posts/${newPost.slug || newPost.id}`
			}
		});
	}

	async function loadPosts(page: number = currentPage) {
		isLoading = true;
		try {
			const result = await postsStore.fetch({
				variables: {
					page,
					limit
				}
			});
			postsData = result.data?.followingPosts;
			currentPage = page;
		} catch (error) {
			console.error('Failed to load following posts:', error);
			notifications.error('載入追蹤動態失敗');
		} finally {
			isLoading = false;
		}
	}

	function handlePageChange(newPage: number) {
		loadPosts(newPage);
	}

	function formatDate(dateString: string) {
		const date = new Date(dateString);
		return new Intl.DateTimeFormat('zh-TW', {
			year: 'numeric',
			month: 'long',
			day: 'numeric'
		}).format(date);
	}
</script>

<svelte:head>
	<title>追蹤動態 - GraphQL Blog</title>
	<meta name="description" content="查看您追蹤用戶的最新文章" />
</svelte:head>

<div class="max-w-6xl mx-auto">
	<div class="mb-8 flex items-center justify-between">
		<div>
			<h1 class="text-4xl font-bold mb-2">追蹤動態</h1>
			<p class="text-gray-600">您追蹤用戶的最新文章</p>
		</div>

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

	<!-- Posts Grid -->
	{#if isLoading}
		<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
			{#each Array(6) as _}
				<div class="card animate-pulse">
					<div class="h-4 bg-gray-200 rounded w-3/4 mb-3"></div>
					<div class="h-3 bg-gray-200 rounded mb-2"></div>
					<div class="h-3 bg-gray-200 rounded w-5/6 mb-4"></div>
					<div class="flex gap-2">
						<div class="h-8 bg-gray-200 rounded-full w-8"></div>
						<div class="h-3 bg-gray-200 rounded w-24 self-center"></div>
					</div>
				</div>
			{/each}
		</div>
	{:else if postsData?.edges?.length > 0}
		<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
			{#each postsData.edges as { node: post }}
				<article class="card hover:shadow-lg transition-shadow">
					<!-- Post Title -->
					<h2 class="text-xl font-semibold mb-2">
						<a href="/posts/{post.slug || post.id}" class="hover:text-primary-600 transition-colors">
							{post.title}
						</a>
					</h2>

					<!-- Post Excerpt -->
					<p class="text-gray-600 mb-4 line-clamp-3">
						{post.excerpt || '暫無摘要'}
					</p>

					<!-- Post Tags -->
					{#if post.tags?.length > 0}
						<div class="flex flex-wrap gap-2 mb-4">
							{#each post.tags as tag}
								<a
									href="/posts?tags={tag.slug}"
									class="text-xs px-2 py-1 rounded-full bg-gray-100 text-gray-600 hover:bg-primary-100 hover:text-primary-600 transition-colors"
								>
									#{tag.name}
								</a>
							{/each}
						</div>
					{/if}

					<!-- Post Meta -->
					<div class="flex items-center justify-between text-sm text-gray-500">
						<div class="flex items-center gap-2">
							{#if post.author?.avatarUrl}
								<img src={post.author.avatarUrl} alt={post.author.username} class="w-6 h-6 rounded-full" />
							{:else}
								<div class="w-6 h-6 rounded-full bg-primary-100 flex items-center justify-center">
									<span class="text-xs font-medium text-primary-600">
										{post.author?.username?.charAt(0).toUpperCase() || 'U'}
									</span>
								</div>
							{/if}
							<span>{post.author?.fullName || post.author?.username}</span>
						</div>
						<time datetime={post.publishedAt || post.createdAt}>
							{formatDate(post.publishedAt || post.createdAt)}
						</time>
					</div>

					<!-- Post Stats -->
					<div class="mt-4 pt-4 border-t flex items-center gap-4 text-sm text-gray-500">
						<span class="flex items-center gap-1">
							<span>💬</span>
							<span>{post.totalComments || 0}</span>
						</span>
						<span class="flex items-center gap-1">
							<span>{post.isLiked ? '❤️' : '🤍'}</span>
							<span>{post.likesCount || 0}</span>
						</span>
						<a href="/posts/{post.slug || post.id}" class="ml-auto link text-primary-600">
							閱讀更多 →
						</a>
					</div>
				</article>
			{/each}
		</div>

		<!-- Pagination -->
		{#if postsData?.pageInfo}
			<div class="mt-8 flex justify-center">
				<div class="flex items-center gap-2">
					<button
						onclick={() => handlePageChange(currentPage - 1)}
						disabled={!postsData.pageInfo.hasPreviousPage || isLoading}
						class="btn btn-secondary disabled:opacity-50 disabled:cursor-not-allowed"
					>
						上一頁
					</button>

					<div class="flex items-center gap-1">
						{#each Array(postsData.pageInfo.totalPages).keys() as pageNum}
							{#if pageNum + 1 === currentPage}
								<span class="px-3 py-1 bg-primary-600 text-white rounded">
									{pageNum + 1}
								</span>
							{:else if Math.abs(pageNum + 1 - currentPage) <= 2 || pageNum === 0 || pageNum === postsData.pageInfo.totalPages - 1}
								<button onclick={() => handlePageChange(pageNum + 1)} class="px-3 py-1 hover:bg-gray-100 rounded">
									{pageNum + 1}
								</button>
							{:else if Math.abs(pageNum + 1 - currentPage) === 3}
								<span class="px-2">...</span>
							{/if}
						{/each}
					</div>

					<button
						onclick={() => handlePageChange(currentPage + 1)}
						disabled={!postsData.pageInfo.hasNextPage || isLoading}
						class="btn btn-secondary disabled:opacity-50 disabled:cursor-not-allowed"
					>
						下一頁
					</button>
				</div>
			</div>

			<div class="mt-4 text-center text-sm text-gray-600">
				第 {postsData.pageInfo.currentPage} 頁，共 {postsData.pageInfo.totalPages} 頁
				（總計 {postsData.pageInfo.totalCount} 篇文章）
			</div>
		{/if}
	{:else}
		<div class="card text-center py-12">
			<div class="text-6xl mb-4">📭</div>
			<p class="text-gray-600 mb-4">目前沒有追蹤動態</p>
			<p class="text-sm text-gray-500 mb-6">開始追蹤一些用戶，這裡就會顯示他們的最新文章！</p>
			<a href="/search" class="btn btn-primary">
				搜尋用戶
			</a>
		</div>
	{/if}
</div>

<style>
	.line-clamp-3 {
		overflow: hidden;
		display: -webkit-box;
		-webkit-line-clamp: 3;
		-webkit-box-orient: vertical;
	}
</style>
