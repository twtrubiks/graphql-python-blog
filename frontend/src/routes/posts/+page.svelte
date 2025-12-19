<script lang="ts">
	import { GetPostsStore, GetPostsByTagsStore, GetAllTagsStore } from '$houdini';
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import { untrack } from 'svelte';
	import TagFilter from '$lib/components/TagFilter.svelte';

	const postsStore = new GetPostsStore();
	const taggedPostsStore = new GetPostsByTagsStore();
	const allTagsStore = new GetAllTagsStore();

	let currentPage = $state(1);
	let limit = $state(10);
	let isLoading = $state(false);

	let searchQuery = $state('');

	// 標籤篩選狀態
	let selectedTags = $state<string[]>([]);
	let requireAll = $state(false);

	// 所有可用標籤（從 GetAllTags 查詢取得）
	let availableTags = $state<Array<{ id: string; name: string; slug: string }>>([]);

	let postsData = $state<any>(null);

	// 載入所有標籤
	$effect(() => {
		loadAllTags();
	});

	async function loadAllTags() {
		try {
			const result = await allTagsStore.fetch();
			if (result.data?.tags) {
				availableTags = result.data.tags;
			}
		} catch (error) {
			console.error('Failed to load tags:', error);
		}
	}

	// 追蹤上一次的 URL，避免重複載入
	let lastUrl = $state('');

	$effect(() => {
		// 只依賴 page.url.href
		const currentUrl = page.url.href;

		// 避免重複處理相同的 URL
		if (currentUrl === lastUrl) return;

		// 從 URL 讀取篩選狀態
		const urlPage = parseInt(page.url.searchParams.get('page') || '1');
		const urlLimit = parseInt(page.url.searchParams.get('limit') || '10');
		const urlTags = page.url.searchParams.get('tags');
		const urlRequireAll = page.url.searchParams.get('requireAll') === 'true';
		const urlSearch = page.url.searchParams.get('search') || '';

		// 使用 untrack 避免循環依賴
		untrack(() => {
			lastUrl = currentUrl;
			currentPage = urlPage;
			limit = urlLimit;
			selectedTags = urlTags ? urlTags.split(',').filter(Boolean) : [];
			requireAll = urlRequireAll;
			searchQuery = urlSearch;
		});

		loadPosts(urlTags ? urlTags.split(',').filter(Boolean) : [], urlRequireAll, urlPage, urlLimit, urlSearch);
	});

	async function loadPosts(
		tags: string[] = selectedTags,
		reqAll: boolean = requireAll,
		pg: number = currentPage,
		lim: number = limit,
		search: string = searchQuery
	) {
		isLoading = true;
		try {
			let result;

			if (tags.length > 0) {
				// 使用標籤篩選查詢
				result = await taggedPostsStore.fetch({
					variables: {
						tagSlugs: tags,
						requireAll: reqAll,
						page: pg,
						limit: lim
					}
				});
				postsData = result.data?.postsByTags;
			} else {
				// 使用一般文章查詢
				result = await postsStore.fetch({
					variables: {
						page: pg,
						limit: lim,
						search: search || null
					}
				});
				postsData = result.data?.posts;
			}
		} catch (error) {
			console.error('Failed to load posts:', error);
		} finally {
			isLoading = false;
		}
	}

	// 更新 URL 參數
	async function updateURL() {
		const url = new URL(page.url);

		// 設定標籤參數
		if (selectedTags.length > 0) {
			url.searchParams.set('tags', selectedTags.join(','));
			if (requireAll) {
				url.searchParams.set('requireAll', 'true');
			} else {
				url.searchParams.delete('requireAll');
			}
			// 清除搜尋（標籤篩選和搜尋互斥）
			url.searchParams.delete('search');
		} else {
			url.searchParams.delete('tags');
			url.searchParams.delete('requireAll');
			// 設定搜尋參數
			if (searchQuery) {
				url.searchParams.set('search', searchQuery);
			} else {
				url.searchParams.delete('search');
			}
		}

		// 重設頁碼
		url.searchParams.set('page', '1');

		await goto(url.toString(), { keepFocus: true, replaceState: false });
	}

	function handleTagToggle(slug: string) {
		if (selectedTags.includes(slug)) {
			selectedTags = selectedTags.filter((t) => t !== slug);
		} else {
			selectedTags = [...selectedTags, slug];
		}
		updateURL();
	}

	function handleRequireAllToggle() {
		requireAll = !requireAll;
		updateURL();
	}

	function handleClearTags() {
		selectedTags = [];
		requireAll = false;
		updateURL();
	}

	async function handlePageChange(newPage: number) {
		const url = new URL(page.url);
		url.searchParams.set('page', newPage.toString());
		await goto(url.toString(), { keepFocus: true, replaceState: false });
	}

	async function handleSearch() {
		// 清除標籤篩選（搜尋和標籤篩選互斥）
		selectedTags = [];
		requireAll = false;
		currentPage = 1;
		await updateURL();
	}

	function handleSearchKeydown(event: KeyboardEvent) {
		if (event.key === 'Enter') {
			handleSearch();
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

	// 高亮搜尋結果工具函數
	function escapeHtml(str: string): string {
		const map: Record<string, string> = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };
		return str.replace(/[&<>"']/g, (m) => map[m]);
	}

	function escapeRegex(str: string): string {
		return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
	}

	function highlightText(text: string, query: string): string {
		if (!text) return '';
		if (!query?.trim()) return escapeHtml(text);
		const escaped = escapeHtml(text);
		const regex = new RegExp(`(${escapeRegex(query.trim())})`, 'gi');
		return escaped.replace(regex, '<mark class="bg-yellow-200 px-0.5 rounded">$1</mark>');
	}
</script>

<svelte:head>
	<title>文章列表 - GraphQL Blog</title>
	<meta name="description" content="瀏覽所有文章，發現精彩內容" />
</svelte:head>

<div class="max-w-6xl mx-auto">
	<div class="mb-8">
		<h1 class="text-4xl font-bold mb-4">文章列表</h1>
		<p class="text-gray-600">探索社群分享的精彩文章</p>
	</div>

	<!-- Search Bar -->
	<div class="card mb-4">
		<div class="flex flex-col md:flex-row gap-4">
			<div class="flex-1">
				<input
					type="text"
					bind:value={searchQuery}
					onkeydown={handleSearchKeydown}
					placeholder="搜尋文章..."
					class="w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
					disabled={selectedTags.length > 0}
				/>
			</div>
			<button onclick={handleSearch} class="btn btn-primary" disabled={isLoading || selectedTags.length > 0}>
				搜尋
			</button>
		</div>
		{#if selectedTags.length > 0}
			<p class="text-xs text-gray-500 mt-2">提示：標籤篩選時無法使用搜尋功能</p>
		{/if}
	</div>

	<!-- Tag Filter -->
	<TagFilter
		{availableTags}
		{selectedTags}
		{requireAll}
		onTagToggle={handleTagToggle}
		onRequireAllToggle={handleRequireAllToggle}
		onClear={handleClearTags}
	/>

	<!-- 顯示目前篩選狀態 -->
	{#if selectedTags.length > 0}
		<div class="mb-4 p-3 bg-blue-50 rounded-lg text-sm">
			<span class="text-blue-700">
				目前篩選：{selectedTags.map((s) => `#${s}`).join(requireAll ? ' AND ' : ' OR ')}
				{#if postsData?.pageInfo}
					（找到 {postsData.pageInfo.totalCount} 篇文章）
				{/if}
			</span>
		</div>
	{/if}

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
					<!-- Post Status Badge -->
					{#if post.status === 'DRAFT'}
						<span
							class="inline-block px-2 py-1 text-xs font-medium bg-yellow-100 text-yellow-800 rounded-full mb-2"
						>
							草稿
						</span>
					{/if}

					<!-- Post Title -->
					<h2 class="text-xl font-semibold mb-2">
						<a href="/posts/{post.slug || post.id}" class="hover:text-primary-600 transition-colors">
							{@html highlightText(post.title, searchQuery)}
						</a>
					</h2>

					<!-- Post Excerpt -->
					<p class="text-gray-600 mb-4 line-clamp-3">
						{@html highlightText(post.excerpt || '暫無摘要', searchQuery)}
					</p>

					<!-- Post Tags -->
					{#if post.tags?.length > 0}
						<div class="flex flex-wrap gap-2 mb-4">
							{#each post.tags as tag}
								<a
									href="/posts/tag/{tag.slug}"
									class="text-xs px-2 py-1 rounded-full transition-colors
									{selectedTags.includes(tag.slug)
										? 'bg-primary-500 text-white'
										: 'bg-gray-100 text-gray-600 hover:bg-primary-100 hover:text-primary-600'}"
								>
									#{tag.name}
								</a>
							{/each}
						</div>
					{/if}

					<!-- Post Meta -->
					<div class="flex items-center justify-between text-sm text-gray-500">
						<div class="flex items-center gap-2">
							{#if post.author.avatarUrl}
								<img src={post.author.avatarUrl} alt={post.author.username} class="w-6 h-6 rounded-full" />
							{:else}
								<div class="w-6 h-6 rounded-full bg-primary-100 flex items-center justify-center">
									<span class="text-xs font-medium text-primary-600">
										{post.author.username.charAt(0).toUpperCase()}
									</span>
								</div>
							{/if}
							<span>{post.author.username}</span>
						</div>
						<time datetime={post.publishedAt || post.createdAt}>
							{formatDate(post.publishedAt || post.createdAt)}
						</time>
					</div>

					<!-- Post Stats -->
					<div class="mt-4 pt-4 border-t flex items-center gap-4 text-sm text-gray-500">
						<span class="flex items-center gap-1">
							<span>💬</span>
							<span>{post.totalComments}</span>
						</span>
						<span class="flex items-center gap-1">
							<span>{post.isLiked ? '❤️' : '🤍'}</span>
							<span>{post.likesCount}</span>
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
			{#if selectedTags.length > 0}
				<p class="text-gray-600 mb-4">
					找不到符合 {selectedTags.map((s) => `#${s}`).join(requireAll ? ' AND ' : ' OR ')} 的文章
				</p>
				<button onclick={handleClearTags} class="btn btn-secondary"> 清除篩選 </button>
			{:else if searchQuery}
				<p class="text-gray-600 mb-4">找不到符合「{searchQuery}」的文章</p>
				<button
					onclick={() => {
						searchQuery = '';
						handleSearch();
					}}
					class="btn btn-secondary"
				>
					清除搜尋
				</button>
			{:else}
				<p class="text-gray-600 mb-4">目前還沒有文章</p>
				<a href="/posts/new" class="btn btn-primary"> 撰寫第一篇文章 </a>
			{/if}
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
