<script lang="ts">
	import { SearchContentStore } from '$houdini';
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import PostCard from '$lib/components/PostCard.svelte';
	import UserCard from '$lib/components/UserCard.svelte';

	const searchStore = new SearchContentStore();

	let searchTerm = $state('');
	let isLoading = $state(false);
	let searchResults = $state<any[]>([]);
	let hasSearched = $state(false);
	let error = $state<string | null>(null);

	// 追蹤上一次的 URL，避免重複處理
	let lastUrl = $state('');

	// 區分文章與用戶結果
	let postResults = $derived(
		searchResults.filter(r => r.__typename === 'PostType')
	);

	let userResults = $derived(
		searchResults.filter(r => r.__typename === 'UserType')
	);

	// 從 URL 讀取搜尋詞
	$effect(() => {
		const currentUrl = page.url.href;

		// 避免重複處理相同的 URL
		if (currentUrl === lastUrl) return;
		lastUrl = currentUrl;

		const q = page.url.searchParams.get('q');
		if (q) {
			searchTerm = q;
			performSearch();
		}
	});

	async function performSearch() {
		if (!searchTerm.trim()) return;

		isLoading = true;
		hasSearched = true;
		error = null;

		try {
			const result = await searchStore.fetch({
				variables: { term: searchTerm.trim() }
			});
			searchResults = result.data?.search || [];
		} catch (err) {
			console.error('Search failed:', err);
			error = '搜尋時發生錯誤，請稍後再試';
			searchResults = [];
		} finally {
			isLoading = false;
		}
	}

	async function handleSearch() {
		if (!searchTerm.trim()) return;

		// 更新 URL
		const url = new URL(page.url);
		url.searchParams.set('q', searchTerm.trim());
		await goto(url.toString(), { keepFocus: true, replaceState: false });

		await performSearch();
	}

	function handleKeydown(event: KeyboardEvent) {
		if (event.key === 'Enter') {
			handleSearch();
		}
	}
</script>

<svelte:head>
	<title>{searchTerm ? `搜尋「${searchTerm}」` : '搜尋'} - GraphQL Blog</title>
	<meta name="description" content="搜尋文章與用戶" />
</svelte:head>

<div class="max-w-6xl mx-auto">
	<!-- 標題 -->
	<div class="mb-8">
		<h1 class="text-4xl font-bold mb-4">搜尋</h1>
		<p class="text-gray-600">搜尋文章與用戶，體驗 GraphQL Union Type 的強大功能</p>
	</div>

	<!-- 搜尋欄 -->
	<div class="card mb-8">
		<div class="flex flex-col md:flex-row gap-4">
			<div class="flex-1">
				<input
					type="text"
					bind:value={searchTerm}
					onkeydown={handleKeydown}
					placeholder="輸入關鍵字搜尋文章或用戶..."
					class="w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
				/>
			</div>
			<button
				onclick={handleSearch}
				class="btn btn-primary"
				disabled={isLoading || !searchTerm.trim()}
			>
				{#if isLoading}
					搜尋中...
				{:else}
					🔍 搜尋
				{/if}
			</button>
		</div>
	</div>

	<!-- 載入中 -->
	{#if isLoading}
		<div class="space-y-8">
			<!-- 文章骨架屏 -->
			<div>
				<h2 class="text-xl font-semibold mb-4 text-gray-400">文章</h2>
				<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
					{#each Array(3) as _}
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
			</div>
			<!-- 用戶骨架屏 -->
			<div>
				<h2 class="text-xl font-semibold mb-4 text-gray-400">用戶</h2>
				<div class="grid grid-cols-1 md:grid-cols-2 gap-6">
					{#each Array(2) as _}
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
			</div>
		</div>

	<!-- 錯誤狀態 -->
	{:else if error}
		<div class="card text-center py-12">
			<p class="text-red-600 mb-4">{error}</p>
			<button onclick={handleSearch} class="btn btn-secondary">
				重試
			</button>
		</div>

	<!-- 有搜尋結果 -->
	{:else if hasSearched && searchResults.length > 0}
		<div class="space-y-8">
			<!-- 搜尋結果摘要 -->
			<div class="text-gray-600">
				找到 <strong>{searchResults.length}</strong> 筆結果
				（{postResults.length} 篇文章、{userResults.length} 位用戶）
			</div>

			<!-- 文章區塊 -->
			{#if postResults.length > 0}
				<section>
					<h2 class="text-2xl font-semibold mb-4 flex items-center gap-2">
						<span>📝</span>
						<span>文章</span>
						<span class="text-sm font-normal text-gray-500">({postResults.length})</span>
					</h2>
					<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
						{#each postResults as post}
							<PostCard
								postId={post.postId}
								title={post.title}
								slug={post.slug}
								excerpt={post.excerpt}
								createdAt={post.createdAt}
								author={post.author}
								tags={post.tags}
								totalComments={post.totalComments}
								likesCount={post.likesCount}
								searchQuery={searchTerm}
							/>
						{/each}
					</div>
				</section>
			{/if}

			<!-- 用戶區塊 -->
			{#if userResults.length > 0}
				<section>
					<h2 class="text-2xl font-semibold mb-4 flex items-center gap-2">
						<span>👤</span>
						<span>用戶</span>
						<span class="text-sm font-normal text-gray-500">({userResults.length})</span>
					</h2>
					<div class="grid grid-cols-1 md:grid-cols-2 gap-6">
						{#each userResults as user}
							<UserCard
								userId={user.userId}
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
				</section>
			{/if}
		</div>

	<!-- 無搜尋結果 -->
	{:else if hasSearched && searchResults.length === 0}
		<div class="card text-center py-12">
			<p class="text-gray-600 mb-4">
				找不到符合「<strong>{searchTerm}</strong>」的結果
			</p>
			<p class="text-sm text-gray-500 mb-6">
				試試其他關鍵字，或瀏覽所有文章
			</p>
			<a href="/posts" class="btn btn-secondary">
				瀏覽文章
			</a>
		</div>

	<!-- 初始狀態 -->
	{:else}
		<div class="card text-center py-12">
			<div class="text-6xl mb-4">🔍</div>
			<p class="text-gray-600 mb-2">輸入關鍵字搜尋文章或用戶</p>
			<p class="text-sm text-gray-500">
				這個搜尋功能使用 GraphQL Union Type，可以同時搜尋不同類型的內容
			</p>
		</div>
	{/if}
</div>
