<script lang="ts">
	import '../app.css';
	import { page } from '$app/state';
	import { auth } from '$lib/stores/auth.svelte';
	import { notifications } from '$lib/stores/notifications.svelte';
	import { userStatusStore } from '$lib/stores/userStatus.svelte';
	import { followedFeed } from '$lib/stores/followedFeed.svelte';
	import RealtimeNotification from '$lib/components/RealtimeNotification.svelte';
	import {
		PostPublishedStore,
		FollowedUserPostedStore,
		UserStatusChangedStore,
		GetOnlineUsersStore
	} from '$houdini';
	import { createSubscriptionManager } from '$lib/utils/subscriptionManager.svelte';
	import { onMount, onDestroy } from 'svelte';
	import type { LayoutProps } from './$types';

	// Svelte 5 syntax - using $props
	let { children }: LayoutProps = $props();

	let showUserMenu = $state(false);
	let menuContainer: HTMLDivElement | null = $state(null);
	let tokenCheckInterval: ReturnType<typeof setInterval> | null = null;

	// 用於去重的追蹤變數
	let lastPostId: string | null = null;
	let lastFollowedPostId: string | null = null;

	async function handleLogout() {
		await auth.logout();
		showUserMenu = false;
	}

	// ===== 使用訂閱管理器 =====

	// PostPublished 訂閱管理器（公開，不需認證）
	const postPublishedManager = createSubscriptionManager<{ postPublished?: any }>({
		name: 'PostPublished',
		createStore: () => new PostPublishedStore(),
		getListenParams: () => ({}),
		requiresAuth: false,
		onData: (data) => {
			if (data.postPublished) {
				const post = data.postPublished;
				if (post.id !== lastPostId) {
					lastPostId = post.id;
					handleNewPost(post);
				}
			}
		},
		onError: (error) => console.error('[PostPublished] Error:', error)
	});

	// FollowedUserPosted 訂閱管理器（需認證）
	const followedUserManager = createSubscriptionManager<{ followedUserPosted?: any }>({
		name: 'FollowedUserPosted',
		createStore: () => new FollowedUserPostedStore(),
		getListenParams: () => (auth.user?.id ? { userId: auth.user.id } : null),
		requiresAuth: true,
		onData: (data) => {
			if (data.followedUserPosted) {
				const newPost = data.followedUserPosted;
				if (newPost.id !== lastFollowedPostId) {
					lastFollowedPostId = newPost.id;
					// 寫入共用 store，讓 /following 頁面即時更新列表（不需自行重複訂閱）
					followedFeed.latestPost = newPost;
					handleFollowedUserPost(newPost);
				}
			}
		},
		onError: (error) => console.error('[FollowedUserPosted] Error:', error),
		onStatusChange: (status) => {
			followedFeed.status = status;
		},
		onCleanup: () => {
			lastFollowedPostId = null;
			followedFeed.reset();
		}
	});

	// UserStatus 訂閱管理器（需認證）
	const userStatusManager = createSubscriptionManager<{ userStatusChanged?: any }>({
		name: 'UserStatus',
		createStore: () => new UserStatusChangedStore(),
		getListenParams: () =>
			auth.user?.id && auth.user?.username
				? { userId: auth.user.id, username: auth.user.username }
				: null,
		requiresAuth: true,
		onData: (data) => {
			if (data.userStatusChanged) {
				const { userId, status, username } = data.userStatusChanged;
				userStatusStore.updateStatus(userId, status);
				console.log('[UserStatus] Status changed:', username, status);
			}
		},
		onError: (error) => console.error('[UserStatus] Error:', error),
		onCleanup: () => userStatusStore.clear()
	});

	// 統一的認證狀態變更處理（合併原本兩個 $effect）
	$effect(() => {
		if (auth.isAuthenticated && auth.user?.id) {
			// 用戶已登入，初始化需認證的訂閱
			if (!followedUserManager.isInitialized) {
				followedUserManager.init();
			}
			if (!userStatusManager.isInitialized) {
				initUserStatusWithInitialState();
			}
		} else if (!auth.isAuthenticated) {
			// 用戶登出，清理訂閱
			followedUserManager.cleanup();
			userStatusManager.cleanup();
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
		// 刷新用戶資料（驗證 token 並同步伺服器資訊）
		if (auth.isAuthenticated) {
			console.log('[Layout] Refreshing user data on mount');
			await auth.refreshUser();
		}

		// 初始化公開訂閱（PostPublished 不需認證）
		postPublishedManager.init();

		// 注意：需認證的訂閱由 $effect 處理，不在此處重複初始化
		// 這樣避免了 $effect/onMount 競爭條件

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
	});

	onDestroy(async () => {
		// 統一清理所有訂閱
		await postPublishedManager.cleanup();
		await followedUserManager.cleanup();
		await userStatusManager.cleanup();

		// 清理 token 檢查 interval
		if (tokenCheckInterval) {
			clearInterval(tokenCheckInterval);
			tokenCheckInterval = null;
		}
	});

	// ===== 事件處理函數 =====

	/**
	 * 處理新文章發布事件
	 */
	function handleNewPost(post: any) {
		// 排除自己發的文章（不通知作者本人）
		if (auth.user?.id && post.author?.id === auth.user.id) {
			console.log('[PostPublished] Skipping notification for own post');
			return;
		}

		const authorName = post.author?.fullName || post.author?.username || '某用戶';
		console.log('[PostPublished] New post published:', post);

		// 顯示通知
		notifications.info(`${authorName} 發表了新文章：${post.title}`, {
			duration: 8000,
			link: {
				text: '立即查看',
				href: `/posts/${post.slug || post.id}`
			}
		});

		// 如果在文章列表頁，可以考慮重新載入
		if (page.url.pathname === '/posts' || page.url.pathname === '/') {
			console.log('[Info] New post available. Consider refreshing the list.');
		}
	}

	/**
	 * 處理追蹤用戶發文事件
	 */
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

	/**
	 * 初始化用戶狀態訂閱（包含初始狀態載入）
	 * 解決「缺少初始狀態」問題：先查詢當前在線用戶，再啟動訂閱
	 */
	async function initUserStatusWithInitialState() {
		if (userStatusManager.isInitialized) return;

		try {
			// 先獲取當前在線用戶列表
			const onlineUsersStore = new GetOnlineUsersStore();
			const result = await onlineUsersStore.fetch();

			if (result.data?.onlineUsers) {
				// 設置初始狀態
				userStatusStore.setInitialStatuses(
					result.data.onlineUsers.map((u: { userId: string; username: string }) => ({
						userId: u.userId,
						status: 'ONLINE' as const
					}))
				);
				console.log('[UserStatus] Initial online users loaded:', result.data.onlineUsers.length);
			}
		} catch (error) {
			console.error('[UserStatus] Failed to fetch initial online users:', error);
		}

		// 然後啟動訂閱監聽後續狀態變更
		userStatusManager.init();
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
<div class="notification-stack fixed top-4 right-4 z-[100] flex flex-col gap-2 w-full max-w-sm">
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