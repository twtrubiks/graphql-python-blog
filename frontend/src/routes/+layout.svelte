<script lang="ts">
	import '../app.css';
	import { page } from '$app/state';
	import { auth } from '$lib/stores/auth.svelte';
	import { notifications } from '$lib/stores/notifications.svelte';
	import RealtimeNotification from '$lib/components/RealtimeNotification.svelte';
	import { PostPublishedStore, FollowedUserPostedStore } from '$houdini';
	import { onMount, onDestroy } from 'svelte';
	import type { LayoutProps } from './$types';

	// Svelte 5 syntax - using $props
	let { children }: LayoutProps = $props();

	let showUserMenu = $state(false);
	let menuContainer: HTMLDivElement | null = $state(null);
	let postPublishedStore: any = null;
	let isSubscriptionActive = $state(false);
	let lastPostId: string | null = null;
	let storeUnsubscribe: (() => void) | null = null;
	let tokenCheckInterval: ReturnType<typeof setInterval> | null = null;

	// 追蹤用戶發文訂閱狀態
	let followedPostsStore: FollowedUserPostedStore | null = null;
	let isFollowedSubscriptionActive = $state(false);
	let lastFollowedPostId: string | null = null;
	let followedStoreUnsubscribe: (() => void) | null = null;

	async function handleLogout() {
		await auth.logout();
		showUserMenu = false;
	}

	// 當用戶登入狀態改變時，啟動或停止追蹤訂閱
	$effect(() => {
		if (auth.isAuthenticated && auth.user?.id && !isFollowedSubscriptionActive) {
			// 用戶剛登入，啟動訂閱
			initFollowedUserSubscription();
		} else if (!auth.isAuthenticated && isFollowedSubscriptionActive) {
			// 用戶登出，停止訂閱
			if (followedStoreUnsubscribe) {
				followedStoreUnsubscribe();
				followedStoreUnsubscribe = null;
			}
			if (followedPostsStore) {
				followedPostsStore.unlisten();
				followedPostsStore = null;
			}
			isFollowedSubscriptionActive = false;
			lastFollowedPostId = null;
		}
	});

	// 點擊外部關閉選單
	$effect(() => {
		if (!showUserMenu) return;

		function handleClickOutside(event: MouseEvent) {
			if (menuContainer && !menuContainer.contains(event.target as Node)) {
				showUserMenu = false;
			}
		}

		document.addEventListener('click', handleClickOutside);
		return () => document.removeEventListener('click', handleClickOutside);
	});

	onMount(async () => {
		// 初始化 postPublished subscription
		postPublishedStore = new PostPublishedStore();

		// 建立 store subscription
		storeUnsubscribe = postPublishedStore.subscribe((value: any) => {
			if (!value || !isSubscriptionActive) return;

			// 檢查是否有新文章
			if (value.data?.postPublished) {
				const post = value.data.postPublished;

				// 避免重複處理
				if (post.id !== lastPostId) {
					lastPostId = post.id;

					// 排除自己發的文章（不通知作者本人）
					if (auth.user?.id && post.author?.id === auth.user.id) {
						console.log('[Subscription] Skipping notification for own post');
						return;
					}

					const authorName = post.author?.fullName || post.author?.username || '某用戶';

					console.log('[Subscription] New post published:', post);

					// 顯示通知
					notifications.info(
						`${authorName} 發表了新文章：${post.title}`,
						{
							duration: 8000,
							link: {
								text: '立即查看',
								href: `/posts/${post.slug || post.id}`
							}
						}
					);

					// 如果在文章列表頁，可以考慮重新載入
					if (page.url.pathname === '/posts' || page.url.pathname === '/') {
						console.log('[Info] New post available. Consider refreshing the list.');
					}
				}
			}

			// 處理錯誤
			if (value.error) {
				console.error('[Subscription] Error:', value.error);
			}
		});

		// 啟動 subscription
		subscribeToNewPosts();

		// 初始化追蹤用戶發文訂閱（僅限已登入用戶）
		if (auth.isAuthenticated && auth.user?.id) {
			initFollowedUserSubscription();
		}

		// 設定定期檢查 token 過期
		tokenCheckInterval = setInterval(() => {
			if (auth.isAuthenticated) {
				// 檢查 token 是否即將過期（1天內）
				if (auth.isTokenExpiringSoon()) {
					notifications.warning('您的登入將在 24 小時內過期，建議重新登入以保持登入狀態', {
						duration: 10000
					});
				}

				// 檢查 token 是否已過期（這會自動觸發登出）
				const validToken = auth.validToken;
				if (!validToken && auth.isAuthenticated) {
					console.log('[Layout] Token expired during session');
					notifications.error('登入已過期，請重新登入');
				}
			}
		}, 3600000); // 每小時檢查一次（適合 7 天的 token 週期）

		return () => {
			// onMount cleanup
			if (storeUnsubscribe) {
				storeUnsubscribe();
				storeUnsubscribe = null;
			}
			if (followedStoreUnsubscribe) {
				followedStoreUnsubscribe();
				followedStoreUnsubscribe = null;
			}
			if (tokenCheckInterval) {
				clearInterval(tokenCheckInterval);
				tokenCheckInterval = null;
			}
		};
	});

	onDestroy(async () => {
		// 清理 subscription
		if (storeUnsubscribe) {
			storeUnsubscribe();
			storeUnsubscribe = null;
		}
		if (postPublishedStore && isSubscriptionActive) {
			await postPublishedStore.unlisten();
			isSubscriptionActive = false;
		}
		// 清理追蹤用戶發文訂閱
		if (followedStoreUnsubscribe) {
			followedStoreUnsubscribe();
			followedStoreUnsubscribe = null;
		}
		if (followedPostsStore && isFollowedSubscriptionActive) {
			await followedPostsStore.unlisten();
			isFollowedSubscriptionActive = false;
		}
		// 清理 token 檢查 interval
		if (tokenCheckInterval) {
			clearInterval(tokenCheckInterval);
			tokenCheckInterval = null;
		}
	});

	async function subscribeToNewPosts() {
		if (!postPublishedStore || isSubscriptionActive) return;

		console.log('[Subscription] Starting post published subscription');
		isSubscriptionActive = true;

		try {
			// 觸發 subscription
			await postPublishedStore.listen({});
			console.log('[Subscription] Post published subscription connected');
		} catch (error) {
			console.error('[Subscription] Failed to start subscription:', error);
			isSubscriptionActive = false;
		}
	}

	function initFollowedUserSubscription() {
		if (!auth.user?.id) return;

		followedPostsStore = new FollowedUserPostedStore();

		// 監聽訂閱資料
		followedStoreUnsubscribe = followedPostsStore.subscribe((value: any) => {
			if (!value || !isFollowedSubscriptionActive) return;

			if (value.data?.followedUserPosted) {
				const newPost = value.data.followedUserPosted;

				// 避免重複處理
				if (newPost.id !== lastFollowedPostId) {
					lastFollowedPostId = newPost.id;
					handleFollowedUserPost(newPost);
				}
			}

			if (value.error) {
				console.error('[FollowedUserPosted] Error:', value.error);
			}
		});

		// 啟動訂閱
		startFollowedUserSubscription();
	}

	async function startFollowedUserSubscription() {
		if (!followedPostsStore || isFollowedSubscriptionActive || !auth.user?.id) return;

		console.log('[FollowedUserPosted] Starting subscription for user:', auth.user.id);
		isFollowedSubscriptionActive = true;

		try {
			await followedPostsStore.listen({
				userId: auth.user.id
			});
			console.log('[FollowedUserPosted] Subscription connected');
		} catch (error) {
			console.error('[FollowedUserPosted] Failed to connect:', error);
			isFollowedSubscriptionActive = false;
		}
	}

	function handleFollowedUserPost(post: any) {
		// 排除自己發的文章（不通知作者本人）
		if (auth.user?.id && post.author?.id === auth.user.id) {
			console.log('[FollowedUserPosted] Skipping notification for own post');
			return;
		}

		// 如果當前在追蹤動態頁面，不顯示通知（頁面會自動更新）
		if (page.url.pathname === '/following') {
			console.log('[FollowedUserPosted] On following page, skipping notification');
			return;
		}

		const authorName = post.author?.fullName || post.author?.username || '某用戶';

		console.log('[FollowedUserPosted] New post from followed user:', post);

		// 顯示特別的追蹤通知
		notifications.info(
			`您追蹤的 ${authorName} 發布了新文章：${post.title}`,
			{
				duration: 8000,
				link: {
					text: '立即查看',
					href: `/posts/${post.slug || post.id}`
				}
			}
		);
	}

</script>

<div class="min-h-screen flex flex-col">
	<!-- Navigation Header -->
	<header class="sticky top-0 z-50 w-full border-b bg-white/95 backdrop-blur supports-[backdrop-filter]:bg-white/60">
		<div class="container mx-auto flex h-16 items-center px-4">
			<nav class="flex items-center gap-6">
				<a href="/" class="flex items-center gap-2 font-semibold">
					<span class="text-xl">📝</span>
					<span>GraphQL Blog</span>
				</a>

				<div class="flex items-center gap-4 text-sm">
					<a
						href="/"
						class="transition-colors hover:text-primary-600 {page.url.pathname === '/' ? 'text-primary-600 font-medium' : 'text-gray-600'}"
					>
						首頁
					</a>
					<a
						href="/posts"
						class="transition-colors hover:text-primary-600 {page.url.pathname.startsWith('/posts') ? 'text-primary-600 font-medium' : 'text-gray-600'}"
					>
						文章
					</a>
					<a
						href="/search"
						class="transition-colors hover:text-primary-600 {page.url.pathname === '/search' ? 'text-primary-600 font-medium' : 'text-gray-600'}"
						title="搜尋文章與用戶"
					>
						🔍 搜尋
					</a>
					{#if auth.isAuthenticated}
						<a
							href="/following"
							class="transition-colors hover:text-primary-600 {page.url.pathname === '/following' ? 'text-primary-600 font-medium' : 'text-gray-600'}"
							title="查看追蹤用戶的文章"
						>
							👥 追蹤動態
						</a>
					{/if}
					<!-- 關於頁面 - 不在實作範圍內
					<a
						href="/about"
						class="transition-colors hover:text-primary-600 {page.url.pathname === '/about' ? 'text-primary-600 font-medium' : 'text-gray-600'}"
					>
						關於
					</a>
					-->
				</div>
			</nav>

			<div class="ml-auto flex items-center gap-4">
				{#if auth.isAuthenticated}
					<a href="/posts/new" class="btn btn-ghost">
						撰寫文章
					</a>
					<div class="relative" bind:this={menuContainer}>
						<button
							onclick={() => showUserMenu = !showUserMenu}
							class="flex items-center gap-2 px-3 py-2 rounded-md hover:bg-gray-100 transition-colors"
						>
							{#if auth.user?.avatarUrl}
								<img
									src={auth.user.avatarUrl}
									alt={auth.user.username}
									class="w-8 h-8 rounded-full"
								/>
							{:else}
								<div class="w-8 h-8 rounded-full bg-primary-100 flex items-center justify-center">
									<span class="text-sm font-medium text-primary-600">
										{auth.user?.username?.charAt(0).toUpperCase() || 'U'}
									</span>
								</div>
							{/if}
							<span class="text-sm font-medium">{auth.user?.username}</span>
							<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path>
							</svg>
						</button>

						{#if showUserMenu}
							<div class="absolute right-0 mt-2 w-48 bg-white rounded-md shadow-lg py-1 z-50 border">
								<a
									href="/my-posts"
									class="flex items-center gap-2 px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
									onclick={() => showUserMenu = false}
								>
									<span>📝</span>
									<span>我的文章</span>
								</a>
								<a
									href="/my-drafts"
									class="flex items-center gap-2 px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
									onclick={() => showUserMenu = false}
								>
									<span>📄</span>
									<span>我的草稿</span>
								</a>
								<hr class="my-1" />
								<a
									href="/profile/followers"
									class="flex items-center gap-2 px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
									onclick={() => showUserMenu = false}
								>
									<span>👥</span>
									<span>追蹤者/追蹤中</span>
								</a>
								<a
									href="/settings"
									class="flex items-center gap-2 px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
									onclick={() => showUserMenu = false}
								>
									<span>⚙️</span>
									<span>個人設定</span>
								</a>
								<hr class="my-1" />
								<button
									onclick={handleLogout}
									class="flex items-center gap-2 w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
								>
									<span>🚪</span>
									<span>登出</span>
								</button>
							</div>
						{/if}
					</div>
				{:else}
					<a href="/login" class="btn btn-ghost">
						登入
					</a>
					<a href="/register" class="btn btn-primary">
						註冊
					</a>
				{/if}
			</div>
		</div>
	</header>

	<!-- Main Content -->
	<main class="flex-1 container mx-auto px-4 py-8">
		{@render children()}
	</main>

	<!-- Footer -->
	<footer class="border-t bg-gray-50">
		<div class="container mx-auto px-4 py-6">
			<div class="flex flex-col items-center justify-between gap-4 md:flex-row">
				<p class="text-sm text-gray-600">
					© 2025 GraphQL Blog. All rights reserved.
				</p>
				<!-- 暫時註解：隱私政策和服務條款尚未實作
				<div class="flex gap-4 text-sm">
					<a href="/privacy" class="link">隱私政策</a>
					<a href="/terms" class="link">服務條款</a>
				</div>
				-->
			</div>
		</div>
	</footer>
</div>

<!-- 全站通知容器 -->
<div class="notification-stack fixed top-4 right-4 z-[100] flex flex-col gap-2">
	{#each notifications.notifications as notification (notification.id)}
		<RealtimeNotification
			message={notification.message}
			type={notification.type}
			duration={notification.duration}
			link={notification.link}
			onClose={() => notifications.remove(notification.id)}
		/>
	{/each}
</div>