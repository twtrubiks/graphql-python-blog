<script lang="ts">
	import { page } from '$app/state';
	import { GetUserFollowersStore } from '$houdini';
	import { notifications } from '$lib/stores/notifications.svelte';
	import UserCard from '$lib/components/UserCard.svelte';

	const followersStore = new GetUserFollowersStore();

	let isLoading = $state(true);
	let userData = $state<any>(null);
	let activeTab = $state<'followers' | 'following'>('following');
	let notFound = $state(false);

	// 載入用戶追蹤資料
	$effect(() => {
		loadFollowData();
	});

	async function loadFollowData() {
		isLoading = true;
		notFound = false;
		try {
			const result = await followersStore.fetch({
				variables: { username: page.params.username }
			});
			userData = result.data?.user;
			if (!userData) {
				notFound = true;
			}
		} catch (error) {
			console.error('Failed to load follow data:', error);
			notifications.error('載入追蹤資料失敗');
		} finally {
			isLoading = false;
		}
	}

	// 當前顯示的用戶列表
	let displayUsers = $derived(
		activeTab === 'followers' ? userData?.followers || [] : userData?.following || []
	);
</script>

<svelte:head>
	<title>{userData?.username || '用戶'} 的追蹤中 - GraphQL Blog</title>
</svelte:head>

<div class="max-w-4xl mx-auto">
	<!-- 返回連結 -->
	<div class="mb-6">
		<a href="/users/{page.params.username}" class="text-primary-600 hover:text-primary-800 transition-colors">
			← 返回 {page.params.username} 的個人資料
		</a>
	</div>

	{#if notFound}
		<div class="card text-center py-12">
			<div class="text-6xl mb-4">😕</div>
			<h1 class="text-2xl font-bold mb-2">找不到此用戶</h1>
			<p class="text-gray-600 mb-6">用戶 "{page.params.username}" 不存在</p>
			<a href="/" class="btn btn-primary">返回首頁</a>
		</div>
	{:else}
		<h1 class="text-3xl font-bold mb-6">{page.params.username} 的追蹤</h1>

		<!-- 標籤切換 -->
		<div class="flex border-b mb-6">
			<button
				onclick={() => activeTab = 'followers'}
				class="px-6 py-3 text-sm font-medium transition-colors
					{activeTab === 'followers'
						? 'border-b-2 border-primary-600 text-primary-600'
						: 'text-gray-600 hover:text-gray-900'}"
			>
				追蹤者 ({userData?.followersCount || 0})
			</button>
			<button
				onclick={() => activeTab = 'following'}
				class="px-6 py-3 text-sm font-medium transition-colors
					{activeTab === 'following'
						? 'border-b-2 border-primary-600 text-primary-600'
						: 'text-gray-600 hover:text-gray-900'}"
			>
				追蹤中 ({userData?.followingCount || 0})
			</button>
		</div>

		<!-- 用戶列表 -->
		{#if isLoading}
			<div class="grid grid-cols-1 md:grid-cols-2 gap-6">
				{#each Array(4) as _}
					<div class="card animate-pulse">
						<div class="flex items-start gap-4">
							<div class="w-16 h-16 bg-gray-200 rounded-full"></div>
							<div class="flex-1">
								<div class="h-4 bg-gray-200 rounded w-1/3 mb-2"></div>
								<div class="h-3 bg-gray-200 rounded w-1/2"></div>
							</div>
						</div>
					</div>
				{/each}
			</div>
		{:else if displayUsers.length > 0}
			<div class="grid grid-cols-1 md:grid-cols-2 gap-6">
				{#each displayUsers as user}
					<UserCard
						userId={user.id}
						username={user.username}
						fullName={user.fullName}
						bio={user.bio}
						avatarUrl={user.avatarUrl}
						followersCount={user.followersCount}
						followingCount={user.followingCount}
						isFollowedByMe={user.isFollowedByMe}
					/>
				{/each}
			</div>
		{:else}
			<div class="card text-center py-12">
				<div class="text-6xl mb-4">{activeTab === 'followers' ? '👥' : '🔍'}</div>
				<p class="text-gray-600 mb-4">
					{activeTab === 'followers' ? '還沒有人追蹤此用戶' : '此用戶還沒有追蹤任何人'}
				</p>
			</div>
		{/if}
	{/if}
</div>
