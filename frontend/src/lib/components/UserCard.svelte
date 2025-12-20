<script lang="ts">
	import { goto } from '$app/navigation';
	import { FollowUserStore, UnfollowUserStore } from '$houdini';
	import { auth } from '$lib/stores/auth.svelte';
	import { notifications } from '$lib/stores/notifications.svelte';

	interface Props {
		userId: string;
		username: string;
		fullName?: string | null;
		bio?: string | null;
		avatarUrl?: string | null;
		followersCount: number;
		followingCount: number;
		isFollowedByMe?: boolean;
	}

	let {
		userId,
		username,
		fullName,
		bio,
		avatarUrl,
		followersCount,
		followingCount,
		isFollowedByMe = false
	}: Props = $props();

	// 本地狀態管理
	let localFollowersCount = $state(followersCount);
	let localIsFollowedByMe = $state(isFollowedByMe);
	let isFollowing = $state(false);

	// 當 props 變化時更新本地狀態
	$effect(() => {
		localFollowersCount = followersCount;
		localIsFollowedByMe = isFollowedByMe;
	});

	const followStore = new FollowUserStore();
	const unfollowStore = new UnfollowUserStore();

	// 判斷是否為當前登入用戶
	let isCurrentUser = $derived(auth.user?.id === userId);

	async function handleFollow() {
		if (!auth.isAuthenticated) {
			notifications.warning('請先登入才能追蹤用戶', { duration: 3000 });
			await goto('/login');
			return;
		}

		isFollowing = true;
		try {
			if (localIsFollowedByMe) {
				// 取消追蹤
				const result = await unfollowStore.mutate({ userId });
				if (result.data?.unfollowUser?.success) {
					localIsFollowedByMe = false;
					localFollowersCount -= 1;
					notifications.success('已取消追蹤');
				} else {
					notifications.error(result.data?.unfollowUser?.message || '取消追蹤失敗');
				}
			} else {
				// 追蹤
				const result = await followStore.mutate({ userId });
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
</script>

<article class="card hover:shadow-lg transition-shadow">
	<div class="flex items-start gap-4">
		<!-- Avatar -->
		{#if avatarUrl}
			<img
				src={avatarUrl}
				alt={username}
				class="w-16 h-16 rounded-full flex-shrink-0"
			/>
		{:else}
			<div class="w-16 h-16 rounded-full bg-primary-100 flex items-center justify-center flex-shrink-0">
				<span class="text-2xl font-bold text-primary-600">
					{username.charAt(0).toUpperCase()}
				</span>
			</div>
		{/if}

		<div class="flex-1 min-w-0">
			<!-- Username & Full Name -->
			<div class="flex items-center justify-between">
				<div>
					<h3 class="text-lg font-semibold text-gray-900">
						<a href="/users/{username}" class="hover:text-primary-600 transition-colors">
							{username}
						</a>
					</h3>
					{#if fullName}
						<p class="text-sm text-gray-600">{fullName}</p>
					{/if}
				</div>

				<!-- 追蹤按鈕 (不顯示在自己的卡片上) -->
				{#if !isCurrentUser}
					<button
						onclick={handleFollow}
						disabled={isFollowing}
						class="px-4 py-1.5 text-sm font-medium rounded-full transition-colors {localIsFollowedByMe
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

			<!-- Bio -->
			{#if bio}
				<p class="mt-2 text-gray-600 text-sm line-clamp-2">
					{bio}
				</p>
			{/if}

			<!-- Stats -->
			<div class="mt-3 flex items-center gap-4 text-sm text-gray-500">
				<span>
					<strong class="text-gray-900">{localFollowersCount}</strong> 追蹤者
				</span>
				<span>
					<strong class="text-gray-900">{followingCount}</strong> 追蹤中
				</span>
			</div>
		</div>
	</div>
</article>

<style>
	.line-clamp-2 {
		overflow: hidden;
		display: -webkit-box;
		-webkit-line-clamp: 2;
		-webkit-box-orient: vertical;
	}
</style>
