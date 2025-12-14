<script lang="ts">
	import { GetPostsByTagStore } from '$houdini';
	import { page } from '$app/state';
	import { goto } from '$app/navigation';

	const store = new GetPostsByTagStore();

	let currentPage = $state(1);
	let limit = $state(10);
	let isLoading = $state(false);
	let postsData = $state<any>(null);

	// 從 URL 取得 tag slug
	let tagSlug = $derived(page.params.slug);

	// 當 tagSlug 或頁碼變化時重新載入
	$effect(() => {
		const urlPage = parseInt(page.url.searchParams.get('page') || '1');
		currentPage = urlPage;
		loadPosts();
	});

	async function loadPosts() {
		if (!tagSlug) return;

		isLoading = true;
		try {
			const result = await store.fetch({
				variables: {
					tagSlug: tagSlug,
					page: currentPage,
					limit: limit
				}
			});
			postsData = result.data?.postsByTag;
		} catch (error) {
			console.error('Failed to load posts by tag:', error);
		} finally {
			isLoading = false;
		}
	}

	async function handlePageChange(newPage: number) {
		const url = new URL(page.url);
		url.searchParams.set('page', newPage.toString());
		await goto(url.toString(), { keepFocus: true, replaceState: false });
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
	<title>#{tagSlug} 相關文章 - GraphQL Blog</title>
	<meta name="description" content="瀏覽標籤 #{tagSlug} 的所有相關文章" />
</svelte:head>

<div class="max-w-6xl mx-auto">
	<!-- 頁面標題 -->
	<div class="mb-8">
		<nav class="text-sm text-gray-500 mb-4">
			<a href="/posts" class="hover:text-primary-600">文章列表</a>
			<span class="mx-2">/</span>
			<span>標籤</span>
		</nav>
		<h1 class="text-4xl font-bold mb-4 flex items-center gap-3">
			<span class="text-primary-600">#{tagSlug}</span>
		</h1>
		{#if postsData?.pageInfo}
			<p class="text-gray-600">
				共 {postsData.pageInfo.totalCount} 篇文章
			</p>
		{/if}
	</div>

	<!-- 返回連結 -->
	<div class="mb-6">
		<a href="/posts" class="btn btn-secondary">
			← 返回全部文章
		</a>
	</div>

	<!-- 文章列表 -->
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
					<h2 class="text-xl font-semibold mb-2">
						<a href="/posts/{post.slug || post.id}" class="hover:text-primary-600 transition-colors">
							{post.title}
						</a>
					</h2>

					<p class="text-gray-600 mb-4 line-clamp-3">
						{post.excerpt || '暫無摘要'}
					</p>

					{#if post.tags?.length > 0}
						<div class="flex flex-wrap gap-2 mb-4">
							{#each post.tags as tag}
								<a
									href="/posts/tag/{tag.slug}"
									class="text-xs px-2 py-1 rounded-full transition-colors
										{tag.slug === tagSlug
											? 'bg-primary-500 text-white'
											: 'bg-gray-100 text-gray-600 hover:bg-primary-100 hover:text-primary-600'}"
								>
									#{tag.name}
								</a>
							{/each}
						</div>
					{/if}

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

		<!-- 分頁 -->
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
							{:else if Math.abs((pageNum + 1) - currentPage) <= 2 || pageNum === 0 || pageNum === postsData.pageInfo.totalPages - 1}
								<button
									onclick={() => handlePageChange(pageNum + 1)}
									class="px-3 py-1 hover:bg-gray-100 rounded"
								>
									{pageNum + 1}
								</button>
							{:else if Math.abs((pageNum + 1) - currentPage) === 3}
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
			<p class="text-gray-600 mb-4">目前沒有 #{tagSlug} 標籤的文章</p>
			<a href="/posts" class="btn btn-primary">瀏覽所有文章</a>
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
