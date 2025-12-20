<script lang="ts">
	import { GetMyPostsStore, DeletePostStore } from '$houdini';
	import { goto } from '$app/navigation';
	import { auth } from '$lib/stores/auth.svelte';
	import { notifications } from '$lib/stores/notifications.svelte';

	const postsStore = new GetMyPostsStore();
	const deleteStore = new DeletePostStore();

	let currentPage = $state(1);
	let limit = $state(10);
	let isLoading = $state(true);
	let postsData = $state<any>(null);

	// 狀態篩選: 'all' | 'PUBLISHED' | 'DRAFT'
	let statusFilter = $state<string>('all');

	// 檢查登入狀態
	$effect(() => {
		if (!auth.isAuthenticated) {
			notifications.warning('請先登入');
			goto('/login');
		} else {
			loadPosts();
		}
	});

	async function loadPosts(page: number = currentPage) {
		isLoading = true;
		try {
			const result = await postsStore.fetch({
				variables: {
					page,
					limit,
					status: statusFilter === 'all' ? null : statusFilter
				}
			});
			postsData = result.data?.myPosts;
			currentPage = page;
		} catch (error) {
			console.error('Failed to load posts:', error);
			notifications.error('載入文章失敗');
		} finally {
			isLoading = false;
		}
	}

	function handleStatusChange(newStatus: string) {
		statusFilter = newStatus;
		loadPosts(1);
	}

	async function handleDelete(postId: string, postTitle: string) {
		if (!confirm(`確定要刪除「${postTitle}」嗎？`)) return;

		try {
			const result = await deleteStore.mutate({ id: postId });
			if (result.data?.deletePost?.success) {
				notifications.success('文章已刪除');
				loadPosts();
			} else {
				notifications.error(result.data?.deletePost?.message || '刪除失敗');
			}
		} catch (error) {
			notifications.error('刪除文章時發生錯誤');
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

	// 統計數據
	let stats = $derived({
		total: postsData?.pageInfo?.totalCount || 0
	});
</script>

<svelte:head>
	<title>我的文章 - GraphQL Blog</title>
</svelte:head>

<div class="max-w-6xl mx-auto">
	<div class="mb-8 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
		<div>
			<h1 class="text-3xl font-bold">我的文章</h1>
			<p class="text-gray-600 mt-1">
				共 {stats.total} 篇文章
			</p>
		</div>
		<a href="/posts/new" class="btn btn-primary">
			✏️ 撰寫新文章
		</a>
	</div>

	<!-- 狀態篩選標籤 -->
	<div class="flex border-b mb-6">
		<button
			onclick={() => handleStatusChange('all')}
			class="px-6 py-3 text-sm font-medium transition-colors
				{statusFilter === 'all'
					? 'border-b-2 border-primary-600 text-primary-600'
					: 'text-gray-600 hover:text-gray-900'}"
		>
			全部
		</button>
		<button
			onclick={() => handleStatusChange('PUBLISHED')}
			class="px-6 py-3 text-sm font-medium transition-colors
				{statusFilter === 'PUBLISHED'
					? 'border-b-2 border-primary-600 text-primary-600'
					: 'text-gray-600 hover:text-gray-900'}"
		>
			已發布
		</button>
		<button
			onclick={() => handleStatusChange('DRAFT')}
			class="px-6 py-3 text-sm font-medium transition-colors
				{statusFilter === 'DRAFT'
					? 'border-b-2 border-primary-600 text-primary-600'
					: 'text-gray-600 hover:text-gray-900'}"
		>
			草稿
		</button>
	</div>

	<!-- 文章列表 -->
	{#if isLoading}
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
		<div class="space-y-4">
			{#each postsData.edges as { node: post }}
				<article class="card hover:shadow-md transition-shadow">
					<div class="flex flex-col md:flex-row md:items-start md:justify-between gap-4">
						<div class="flex-1">
							<!-- 狀態標籤 -->
							<div class="flex items-center gap-2 mb-2">
								{#if post.status === 'DRAFT'}
									<span class="px-2 py-1 text-xs font-medium bg-yellow-100 text-yellow-800 rounded-full">
										草稿
									</span>
								{:else}
									<span class="px-2 py-1 text-xs font-medium bg-green-100 text-green-800 rounded-full">
										已發布
									</span>
								{/if}
							</div>

							<!-- 標題 -->
							<h2 class="text-xl font-semibold mb-2">
								<a href="/posts/{post.slug || post.id}" class="hover:text-primary-600 transition-colors">
									{post.title}
								</a>
							</h2>

							<!-- 摘要 -->
							{#if post.excerpt}
								<p class="text-gray-600 mb-3 line-clamp-2">{post.excerpt}</p>
							{/if}

							<!-- 標籤 -->
							{#if post.tags?.length > 0}
								<div class="flex flex-wrap gap-2 mb-3">
									{#each post.tags as tag}
										<span class="text-xs px-2 py-1 bg-gray-100 text-gray-600 rounded-full">
											#{tag.name}
										</span>
									{/each}
								</div>
							{/if}

							<!-- Meta 資訊 -->
							<div class="flex items-center gap-4 text-sm text-gray-500">
								<time datetime={post.createdAt}>
									建立於 {formatDate(post.createdAt)}
								</time>
								{#if post.publishedAt}
									<span>·</span>
									<time datetime={post.publishedAt}>
										發布於 {formatDate(post.publishedAt)}
									</time>
								{/if}
								<span>·</span>
								<span>💬 {post.totalComments}</span>
								<span>❤️ {post.likesCount}</span>
							</div>
						</div>

						<!-- 操作按鈕 -->
						<div class="flex items-center gap-2">
							<a
								href="/posts/{post.slug || post.id}/edit"
								class="btn btn-secondary text-sm"
							>
								編輯
							</a>
							<button
								onclick={() => handleDelete(post.id, post.title)}
								class="btn btn-ghost text-sm text-red-600 hover:bg-red-50"
							>
								刪除
							</button>
						</div>
					</div>
				</article>
			{/each}
		</div>

		<!-- 分頁 -->
		{#if postsData?.pageInfo && postsData.pageInfo.totalPages > 1}
			<div class="mt-8 flex justify-center">
				<div class="flex items-center gap-2">
					<button
						onclick={() => loadPosts(currentPage - 1)}
						disabled={!postsData.pageInfo.hasPreviousPage || isLoading}
						class="btn btn-secondary disabled:opacity-50 disabled:cursor-not-allowed"
					>
						上一頁
					</button>

					<span class="px-4 text-gray-600">
						第 {postsData.pageInfo.currentPage} / {postsData.pageInfo.totalPages} 頁
					</span>

					<button
						onclick={() => loadPosts(currentPage + 1)}
						disabled={!postsData.pageInfo.hasNextPage || isLoading}
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
			{#if statusFilter === 'DRAFT'}
				<p class="text-gray-600 mb-4">您目前沒有草稿</p>
			{:else if statusFilter === 'PUBLISHED'}
				<p class="text-gray-600 mb-4">您目前沒有已發布的文章</p>
			{:else}
				<p class="text-gray-600 mb-4">您還沒有撰寫任何文章</p>
			{/if}
			<a href="/posts/new" class="btn btn-primary">撰寫第一篇文章</a>
		</div>
	{/if}
</div>

<style>
	.line-clamp-2 {
		overflow: hidden;
		display: -webkit-box;
		-webkit-line-clamp: 2;
		-webkit-box-orient: vertical;
	}
</style>
