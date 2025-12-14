<script lang="ts">
	import { GetPostStore, AddCommentStore, LikePostStore, UnlikePostStore, CommentAddedStore } from '$houdini';
	import { page } from '$app/state';
	import { auth } from '$lib/stores/auth.svelte';
	import { notifications } from '$lib/stores/notifications.svelte';
	import { goto } from '$app/navigation';
	import { onMount, onDestroy } from 'svelte';

	const postStore = new GetPostStore();
	const addCommentStore = new AddCommentStore();
	const likePostStore = new LikePostStore();
	const unlikePostStore = new UnlikePostStore();
	const commentAddedStore = new CommentAddedStore();

	let post = $state<any>(null);
	let isLoading = $state(true);
	let error = $state('');

	let newComment = $state('');
	let isSubmittingComment = $state(false);
	let isLiking = $state(false);

	// Subscription 狀態管理
	let subscriptionStatus = $state<'idle' | 'connecting' | 'connected' | 'error'>('idle');
	let isSubscriptionActive = $state(false);
	let lastCommentId = $state<string | null>(null);
	let storeUnsubscribe: (() => void) | null = null;
	let currentPostId = $state<string | null>(null);

	// 重連機制
	const MAX_RECONNECT_ATTEMPTS = 3;
	let reconnectAttempts = $state(0);

	// 載入文章資料
	$effect(() => {
		loadPost();
	});

	// 當 post ID 變化時建立 subscription
	$effect(() => {
		// 防禦性檢查
		if (!post?.id || isLoading) {
			return;
		}

		const postId = String(post.id);
		if (!postId || postId === 'undefined') {
			console.error('[Subscription] Invalid post ID');
			return;
		}

		// 只有當 postId 真正改變時才重新建立 subscription
		if (currentPostId === postId) {
			return;
		}

		currentPostId = postId;

		// 如果有舊的 subscription，先清理
		if (isSubscriptionActive && commentAddedStore.unlisten) {
			console.log('[Subscription] Cleaning up old subscription');
			commentAddedStore.unlisten();
			isSubscriptionActive = false;
		}

		console.log('[Subscription] Starting subscription for post:', postId);
		console.log('[Subscription] Current user:', auth.user?.username || 'Unknown');
		subscriptionStatus = 'connecting';
		isSubscriptionActive = true;

		try {
			// 觸發 subscription 開始監聽
			commentAddedStore.listen({
				postId: postId
			}).then(() => {
				subscriptionStatus = 'connected';
				console.log('[Subscription] Successfully connected for post:', postId);
				console.log('[Subscription] Ready to receive comments');
			}).catch((error) => {
				console.error('[Subscription] Failed to connect:', error);
				subscriptionStatus = 'error';
				isSubscriptionActive = false;
			});
		} catch (error) {
			console.error('[Subscription] Error starting subscription:', error);
			subscriptionStatus = 'error';
			isSubscriptionActive = false;
		}
	});

	// 監聽 subscription store 資料變化
	onMount(() => {
		// 使用 onMount 來建立 store subscription，避免重複建立
		storeUnsubscribe = commentAddedStore.subscribe((value: any) => {
			// 只檢查 value 是否存在，不檢查 isSubscriptionActive
			if (!value) return;

			// 檢查是否有新評論
			if (value.data?.commentAdded) {
				const newComment = value.data.commentAdded;

				// 避免重複處理同一則評論
				if (newComment.id !== lastCommentId) {
					lastCommentId = newComment.id;
					console.log('[Subscription] Processing new comment:', newComment.id);
					handleNewComment({ commentAdded: newComment });
				}
			}

			// 處理錯誤
			if (value.error) {
				console.error('[Subscription] Error:', value.error);
				subscriptionStatus = 'error';
			}
		});

		return () => {
			// onMount 的 cleanup
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
		if (isSubscriptionActive && commentAddedStore.unlisten) {
			await commentAddedStore.unlisten();
			isSubscriptionActive = false;
			subscriptionStatus = 'idle';
		}
	});

	async function loadPost() {
		isLoading = true;
		error = '';

		try {
			// In Svelte 5, page is a state object, not a store
			const postId = page.params.slug;
			const result = await postStore.fetch({
				variables: {
					id: postId
				}
			});

			if (result.data?.post) {
				post = result.data.post;
				// subscription 會透過 $effect 自動建立
			} else {
				error = '文章不存在';
			}
		} catch (err) {
			error = '載入文章失敗';
			console.error('Failed to load post:', err);
		} finally {
			isLoading = false;
		}
	}

	async function handleAddComment() {
		if (!auth.isAuthenticated) {
			notifications.warning('請先登入才能留言', { duration: 3000 });
			await goto('/login');
			return;
		}

		if (!newComment.trim()) {
			return;
		}

		isSubmittingComment = true;
		try {
			// Houdini expects variables directly, not wrapped in a variables object
			const result = await addCommentStore.mutate({
				postId: post.id,
				content: newComment
			});

			if (result.data?.addComment) {
				// 不要在這裡直接加入評論，讓 subscription 統一處理
				// 這樣可以避免重複，並確保所有用戶看到一致的結果
				console.log('[AddComment] Comment sent successfully, waiting for subscription update');
				newComment = '';
			}
		} catch (err) {
			console.error('Failed to add comment:', err);
		} finally {
			isSubmittingComment = false;
		}
	}

	async function handleLike() {
		if (!auth.isAuthenticated) {
			notifications.warning('請先登入才能按讚', { duration: 3000 });
			await goto('/login');
			return;
		}

		isLiking = true;
		try {
			if (post.isLiked) {
				// Houdini expects variables directly, not wrapped in a variables object
				const result = await unlikePostStore.mutate({
					postId: post.id
				});
				if (result.data?.unlikePost?.success) {
					post.isLiked = false;
					post.likesCount -= 1;
				}
			} else {
				// Houdini expects variables directly, not wrapped in a variables object
				const result = await likePostStore.mutate({
					postId: post.id
				});
				if (result.data?.likePost) {
					post.isLiked = true;
					post.likesCount += 1;
				}
			}
		} catch (err) {
			console.error('Failed to toggle like:', err);
		} finally {
			isLiking = false;
		}
	}

	function formatDate(dateString: string) {
		const date = new Date(dateString);
		return new Intl.DateTimeFormat('zh-TW', {
			year: 'numeric',
			month: 'long',
			day: 'numeric',
			hour: '2-digit',
			minute: '2-digit'
		}).format(date);
	}

	// 處理新評論
	function handleNewComment(data: any) {
		console.log('[Subscription] New comment received:', data);

		const newComment = data?.commentAdded;
		if (!newComment || newComment.isDeleted) {
			console.log('[Subscription] Comment is null or deleted, skipping');
			return;
		}

		// 防止重複添加
		const exists = post.comments?.some((c: any) => c.id === newComment.id);
		if (exists) {
			console.log('[Subscription] Comment already exists, skipping');
			return;
		}

		console.log('[Subscription] Adding comment to list:', {
			id: newComment.id,
			author: newComment.author?.username,
			content: newComment.content.substring(0, 30)
		});

		// 更新狀態
		post = {
			...post,
			comments: [...(post.comments || []), newComment],
			totalComments: newComment.post?.totalComments ?? (post.totalComments + 1)
		};

		// 檢查是否需要顯示通知
		console.log('[Notification] Checking notification conditions:', {
			authorUsername: newComment.author?.username,
			currentUser: auth.user?.username,
			isOwnComment: newComment.author?.username === auth.user?.username
		});

		// 顯示通知（使用統一的通知系統）
		if (newComment.author?.username && newComment.author.username !== auth.user?.username) {
			console.log(`[Notification] Showing notification for comment from ${newComment.author.username}`);

			// 使用統一的通知系統，顯示在畫面右上角
			notifications.info(
				`${newComment.author.username} 發表了新評論：${newComment.content.substring(0, 50)}${newComment.content.length > 50 ? '...' : ''}`,
				{
					duration: 6000,
					link: null  // 已經在同一頁面，不需要連結
				}
			);
		} else {
			console.log('[Notification] Not showing notification (own comment or missing author)');
		}
	}

	function renderMarkdown(content: string) {
		// 簡單的 markdown 轉換，實際專案應使用 markdown 函式庫
		return content
			.replace(/^### (.*$)/gim, '<h3 class="text-xl font-semibold mt-4 mb-2">$1</h3>')
			.replace(/^## (.*$)/gim, '<h2 class="text-2xl font-semibold mt-6 mb-3">$1</h2>')
			.replace(/^# (.*$)/gim, '<h1 class="text-3xl font-bold mt-8 mb-4">$1</h1>')
			.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
			.replace(/\*(.+?)\*/g, '<em>$1</em>')
			.replace(/\[(.+?)\]\((.+?)\)/g, '<a href="$2" class="link text-primary-600">$1</a>')
			.replace(/\n\n/g, '</p><p class="mb-4">')
			.replace(/^/, '<p class="mb-4">')
			.replace(/$/, '</p>');
	}
</script>

<svelte:head>
	{#if post}
		<title>{post.title} - GraphQL Blog</title>
		<meta name="description" content={post.excerpt || post.title} />
	{:else}
		<title>載入中... - GraphQL Blog</title>
	{/if}
</svelte:head>

<div class="max-w-4xl mx-auto">
	{#if isLoading}
		<div class="animate-pulse">
			<div class="h-8 bg-gray-200 rounded w-3/4 mb-4"></div>
			<div class="h-4 bg-gray-200 rounded w-1/2 mb-8"></div>
			<div class="space-y-3">
				<div class="h-3 bg-gray-200 rounded"></div>
				<div class="h-3 bg-gray-200 rounded"></div>
				<div class="h-3 bg-gray-200 rounded w-5/6"></div>
			</div>
		</div>
	{:else if error}
		<div class="card bg-red-50 border-red-200">
			<p class="text-red-600">{error}</p>
			<a href="/posts" class="btn btn-secondary mt-4">返回文章列表</a>
		</div>
	{:else if post}
		<article>
			<!-- Article Header -->
			<header class="mb-8">
				<h1 class="text-4xl font-bold mb-4">{post.title}</h1>

				<div class="flex items-center gap-4 text-gray-600">
					<div class="flex items-center gap-2">
						{#if post.author.avatarUrl}
							<img
								src={post.author.avatarUrl}
								alt={post.author.username}
								class="w-10 h-10 rounded-full"
							/>
						{:else}
							<div class="w-10 h-10 rounded-full bg-primary-100 flex items-center justify-center">
								<span class="text-lg font-medium text-primary-600">
									{post.author.username.charAt(0).toUpperCase()}
								</span>
							</div>
						{/if}
						<div>
							<p class="font-medium text-gray-900">{post.author.fullName || post.author.username}</p>
							<p class="text-sm">@{post.author.username}</p>
						</div>
					</div>

					<time datetime={post.publishedAt || post.createdAt} class="text-sm">
						{formatDate(post.publishedAt || post.createdAt)}
					</time>
				</div>

				{#if post.tags?.length > 0}
					<div class="flex flex-wrap gap-2 mt-4">
						{#each post.tags as tag}
							<span class="px-3 py-1 bg-gray-100 text-gray-700 rounded-full text-sm">
								#{tag.name}
							</span>
						{/each}
					</div>
				{/if}
			</header>

			<!-- Article Content -->
			<div class="prose prose-lg max-w-none mb-8">
				{@html renderMarkdown(post.content)}
			</div>

			<!-- Article Actions -->
			<div class="flex items-center gap-4 py-4 border-y mb-8">
				<button
					onclick={handleLike}
					disabled={isLiking}
					class="flex items-center gap-2 px-4 py-2 rounded-md hover:bg-gray-100 transition-colors"
					class:text-red-600={post.isLiked}
				>
					<span class="text-xl">{post.isLiked ? '❤️' : '🤍'}</span>
					<span>{post.likesCount} 個讚</span>
				</button>

				<div class="flex items-center gap-2 text-gray-600">
					<span>💬</span>
					<span>{post.totalComments} 則留言</span>
				</div>
			</div>

			<!-- Author Info Card -->
			{#if post.author.bio}
				<div class="card bg-gray-50 mb-8">
					<h3 class="font-semibold mb-2">關於作者</h3>
					<div class="flex items-start gap-4">
						{#if post.author.avatarUrl}
							<img
								src={post.author.avatarUrl}
								alt={post.author.username}
								class="w-16 h-16 rounded-full"
							/>
						{:else}
							<div class="w-16 h-16 rounded-full bg-primary-100 flex items-center justify-center">
								<span class="text-2xl font-medium text-primary-600">
									{post.author.username.charAt(0).toUpperCase()}
								</span>
							</div>
						{/if}
						<div class="flex-1">
							<p class="font-medium">{post.author.fullName || post.author.username}</p>
							<p class="text-sm text-gray-600 mb-2">@{post.author.username}</p>
							<p class="text-gray-700">{post.author.bio}</p>
							<div class="flex gap-4 mt-3 text-sm text-gray-600">
								<span>{post.author.followersCount} 個粉絲</span>
								<span>{post.author.followingCount} 個追蹤</span>
							</div>
						</div>
					</div>
				</div>
			{/if}

			<!-- Comments Section -->
			<section>
				<div class="flex items-center justify-between mb-6">
					<h2 class="text-2xl font-semibold">留言區</h2>

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
							{#if reconnectAttempts < MAX_RECONNECT_ATTEMPTS}
								<div class="flex items-center gap-2 text-orange-500">
									<div class="animate-spin w-4 h-4 border-2 border-orange-300 border-t-orange-600 rounded-full"></div>
									<span>重新連線中... (嘗試 {reconnectAttempts}/{MAX_RECONNECT_ATTEMPTS})</span>
								</div>
							{:else}
								<div class="flex items-center gap-2 text-red-500">
									<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
										<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
									</svg>
									<span>即時更新暫時無法使用</span>
								</div>
							{/if}
						{/if}
					</div>
				</div>

				<!-- Add Comment Form -->
				{#if auth.isAuthenticated}
					<div class="card mb-6">
						<textarea
							bind:value={newComment}
							placeholder="分享你的想法..."
							class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
							rows="3"
							disabled={isSubmittingComment}
						></textarea>
						<div class="mt-3 flex justify-end">
							<button
								onclick={handleAddComment}
								disabled={isSubmittingComment || !newComment.trim()}
								class="btn btn-primary"
							>
								{isSubmittingComment ? '發表中...' : '發表留言'}
							</button>
						</div>
					</div>
				{:else}
					<div class="card bg-gray-50 mb-6">
						<p class="text-gray-600 mb-3">請登入後發表留言</p>
						<a href="/login" class="btn btn-primary">登入</a>
					</div>
				{/if}

				<!-- Comments List -->
				{#if post.comments?.length > 0}
					<div class="space-y-4">
						{#each post.comments as comment}
							{#if !comment.isDeleted}
								<div class="card">
									<div class="flex items-start gap-3">
										{#if comment.author.avatarUrl}
											<img
												src={comment.author.avatarUrl}
												alt={comment.author.username}
												class="w-8 h-8 rounded-full"
											/>
										{:else}
											<div class="w-8 h-8 rounded-full bg-gray-200 flex items-center justify-center">
												<span class="text-sm font-medium">
													{comment.author.username.charAt(0).toUpperCase()}
												</span>
											</div>
										{/if}
										<div class="flex-1">
											<div class="flex items-center gap-2 mb-1">
												<span class="font-medium">{comment.author.username}</span>
												<time class="text-xs text-gray-500">
													{formatDate(comment.createdAt)}
												</time>
												{#if comment.updatedAt !== comment.createdAt}
													<span class="text-xs text-gray-500">(已編輯)</span>
												{/if}
											</div>
											<p class="text-gray-700">{comment.content}</p>
										</div>
									</div>
								</div>
							{/if}
						{/each}
					</div>
				{:else}
					<p class="text-center text-gray-500 py-8">還沒有留言，來當第一個留言的人吧！</p>
				{/if}
			</section>
		</article>
	{/if}
</div>