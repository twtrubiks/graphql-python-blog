<script lang="ts">
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import { GetUserProfileStore, GetUserPostsStore, FollowUserStore, UnfollowUserStore } from '$houdini';
	import { auth } from '$lib/stores/auth.svelte';
	import { notifications } from '$lib/stores/notifications.svelte';
	import PostCard from '$lib/components/PostCard.svelte';

	const userProfileStore = new GetUserProfileStore();
	const userPostsStore = new GetUserPostsStore();
	const followStore = new FollowUserStore();
	const unfollowStore = new UnfollowUserStore();

	let isLoading = $state(true);
	let isPostsLoading = $state(true);
	let userData = $state<any>(null);
	let postsData = $state<any>(null);
	let currentPage = $state(1);
	let limit = $state(10);
	let notFound = $state(false);

	// 本地追蹤狀態（樂觀 UI）
	let localFollowersCount = $state(0);
	let localIsFollowedByMe = $state(false);
	let isFollowing = $state(false);

	// 判斷是否為自己的頁面
	let isOwnProfile = $derived(
		auth.isAuthenticated &&
		auth.user?.username === page.params.username
	);

	// 載入用戶資料
	$effect(() => {
		loadUserProfile();
	});

	// 當用戶資料載入後，同步追蹤狀態
	$effect(() => {
		if (userData) {
			localFollowersCount = userData.followersCount;
			localIsFollowedByMe = userData.isFollowedByMe ?? false;
		}
	});

	async function loadUserProfile() {
		isLoading = true;
		notFound = false;
		try {
			const result = await userProfileStore.fetch({
				variables: { username: page.params.username! }
			});
			userData = result.data?.user;
			if (!userData) {
				notFound = true;
			} else {
				// 載入用戶的文章
				await loadUserPosts();
			}
		} catch (error) {
			console.error('Failed to load user profile:', error);
			notifications.error('載入用戶資料失敗');
		} finally {
			isLoading = false;
		}
	}

	async function loadUserPosts(pg: number = 1) {
		isPostsLoading = true;
		try {
			const result = await userPostsStore.fetch({
				variables: {
					authorUsername: page.params.username!,
					page: pg,
					limit
				}
			});
			postsData = result.data?.postsByAuthor;
			currentPage = pg;
		} catch (error) {
			console.error('Failed to load user posts:', error);
		} finally {
			isPostsLoading = false;
		}
	}

	async function handleFollow() {
		if (!auth.isAuthenticated) {
			notifications.warning('請先登入才能追蹤用戶');
			await goto('/login');
			return;
		}

		if (!userData) return;

		isFollowing = true;
		try {
			if (localIsFollowedByMe) {
				// 取消追蹤
				const result = await unfollowStore.mutate({ userId: userData.id });
				if (result.data?.unfollowUser?.success) {
					localIsFollowedByMe = false;
					localFollowersCount -= 1;
					notifications.success('已取消追蹤');
				} else {
					notifications.error(result.data?.unfollowUser?.message || '取消追蹤失敗');
				}
			} else {
				// 追蹤
				const result = await followStore.mutate({ userId: userData.id });
				if (result.data?.followUser?.success) {
					localIsFollowedByMe = true;
					localFollowersCount += 1;
					notifications.success('追蹤成功');
				} else {
					notifications.error(result.data?.followUser?.message || '追蹤失敗');
				}
			}
		} catch (err) {
			console.error('Follow toggle failed:', err);
			notifications.error('操作失敗，請稍後再試');
		} finally {
			isFollowing = false;
		}
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
	<title>{userData?.username || '用戶'} - GraphQL Blog</title>
</svelte:head>

<div class="max-w-4xl mx-auto">
	{#if isLoading}
		<!-- Loading skeleton -->
		<div class="card animate-pulse mb-8">
			<div class="flex items-start gap-6">
				<div class="w-24 h-24 bg-gray-200 rounded-full"></div>
				<div class="flex-1">
					<div class="h-6 bg-gray-200 rounded w-1/3 mb-3"></div>
					<div class="h-4 bg-gray-200 rounded w-1/2 mb-4"></div>
					<div class="h-3 bg-gray-200 rounded w-2/3"></div>
				</div>
			</div>
		</div>
	{:else if notFound}
		<!-- User not found -->
		<div class="card text-center py-12">
			<div class="text-6xl mb-4">😕</div>
			<h1 class="text-2xl font-bold mb-2">找不到此用戶</h1>
			<p class="text-gray-600 mb-6">用戶 "{page.params.username}" 不存在</p>
			<a href="/" class="btn btn-primary">返回首頁</a>
		</div>
	{:else if userData}
		<!-- User Profile Header -->
		<div class="card mb-8">
			<div class="flex flex-col md:flex-row md:items-start gap-6">
				<!-- Avatar -->
				{#if userData.avatarUrl}
					<img
						src={userData.avatarUrl}
						alt={userData.username}
						class="w-24 h-24 rounded-full flex-shrink-0"
					/>
				{:else}
					<div class="w-24 h-24 rounded-full bg-primary-100 flex items-center justify-center flex-shrink-0">
						<span class="text-3xl font-bold text-primary-600">
							{userData.username.charAt(0).toUpperCase()}
						</span>
					</div>
				{/if}

				<div class="flex-1">
					<!-- Username & Full Name -->
					<div class="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-4">
						<div>
							<h1 class="text-2xl font-bold">{userData.username}</h1>
							{#if userData.fullName}
								<p class="text-gray-600">{userData.fullName}</p>
							{/if}
						</div>

						<!-- Action Buttons -->
						<div class="flex items-center gap-3">
							{#if isOwnProfile}
								<a href="/settings" class="btn btn-secondary">
									編輯個人資料
								</a>
							{:else}
								<button
									onclick={handleFollow}
									disabled={isFollowing}
									class="px-6 py-2 font-medium rounded-full transition-colors {localIsFollowedByMe
										? 'bg-gray-200 text-gray-700 hover:bg-gray-300'
										: 'bg-primary-600 text-white hover:bg-primary-700'}"
								>
									{#if isFollowing}
										<span class="inline-block w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin"></span>
									{:else if localIsFollowedByMe}
										追蹤中
									{:else}
										追蹤
									{/if}
								</button>
							{/if}
						</div>
					</div>

					<!-- Bio -->
					{#if userData.bio}
						<p class="text-gray-700 mb-4">{userData.bio}</p>
					{/if}

					<!-- Stats -->
					<div class="flex items-center gap-6 text-sm">
						<a href="/users/{userData.username}/followers" class="hover:text-primary-600 transition-colors">
							<strong class="text-gray-900">{localFollowersCount}</strong>
							<span class="text-gray-600">追蹤者</span>
						</a>
						<a href="/users/{userData.username}/following" class="hover:text-primary-600 transition-colors">
							<strong class="text-gray-900">{userData.followingCount}</strong>
							<span class="text-gray-600">追蹤中</span>
						</a>
						<span class="text-gray-500">
							加入於 {formatDate(userData.createdAt)}
						</span>
					</div>
				</div>
			</div>
		</div>

		<!-- User Posts Section -->
		<div class="mb-6">
			<h2 class="text-xl font-semibold mb-4">
				{isOwnProfile ? '我的文章' : `${userData.username} 的文章`}
			</h2>
		</div>

		{#if isPostsLoading}
			<div class="space-y-4">
				{#each Array(3) as _}
					<div class="card animate-pulse">
						<div class="h-5 bg-gray-200 rounded w-1/2 mb-3"></div>
						<div class="h-3 bg-gray-200 rounded w-3/4 mb-2"></div>
						<div class="h-3 bg-gray-200 rounded w-1/4"></div>
					</div>
				{/each}
			</div>
		{:else if postsData?.edges?.length > 0}
			<div class="space-y-6">
				{#each postsData.edges as { node: post }}
					<PostCard
						postId={post.id}
						title={post.title}
						slug={post.slug}
						excerpt={post.excerpt}
						createdAt={post.createdAt}
						author={post.author}
						tags={post.tags}
						totalComments={post.totalComments}
						likesCount={post.likesCount}
					/>
				{/each}
			</div>

			<!-- Pagination -->
			{#if postsData?.pageInfo && postsData.pageInfo.totalPages > 1}
				<div class="mt-8 flex justify-center">
					<div class="flex items-center gap-2">
						<button
							onclick={() => loadUserPosts(currentPage - 1)}
							disabled={!postsData.pageInfo.hasPreviousPage || isPostsLoading}
							class="btn btn-secondary disabled:opacity-50 disabled:cursor-not-allowed"
						>
							上一頁
						</button>

						<span class="px-4 text-gray-600">
							第 {postsData.pageInfo.currentPage} / {postsData.pageInfo.totalPages} 頁
						</span>

						<button
							onclick={() => loadUserPosts(currentPage + 1)}
							disabled={!postsData.pageInfo.hasNextPage || isPostsLoading}
							class="btn btn-secondary disabled:opacity-50 disabled:cursor-not-allowed"
						>
							下一頁
						</button>
					</div>
				</div>
			{/if}
		{:else}
			<div class="card text-center py-12">
				<div class="text-6xl mb-4">📝</div>
				<p class="text-gray-600">
					{isOwnProfile ? '您還沒有發布任何文章' : '此用戶尚未發布任何文章'}
				</p>
				{#if isOwnProfile}
					<a href="/posts/new" class="btn btn-primary mt-4">撰寫第一篇文章</a>
				{/if}
			</div>
		{/if}
	{/if}
</div>
