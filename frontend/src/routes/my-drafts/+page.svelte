<script lang="ts">
	import { GetMyPostsStore, DeletePostStore, PublishPostStore } from '$houdini';
	import { auth } from '$lib/stores/auth.svelte';
	import { notifications } from '$lib/stores/notifications.svelte';
	import { useAuthGuard } from '$lib/utils/authGuard.svelte';

	const postsStore = new GetMyPostsStore();
	const deleteStore = new DeletePostStore();
	const publishStore = new PublishPostStore();

	let currentPage = $state(1);
	let limit = $state(10);
	let isLoading = $state(true);
	let postsData = $state<any>(null);
	let publishingPostId = $state<string | null>(null);

	useAuthGuard();

	// 登入後載入草稿
	$effect(() => {
		if (auth.isAuthenticated) {
			loadDrafts();
		}
	});

	async function loadDrafts(page: number = currentPage) {
		isLoading = true;
		try {
			const result = await postsStore.fetch({
				variables: {
					page,
					limit,
					status: 'DRAFT'
				},
				policy: 'CacheAndNetwork'
			});
			postsData = result.data?.myPosts;
			currentPage = page;
		} catch (error) {
			console.error('Failed to load drafts:', error);
			notifications.error('載入草稿失敗');
		} finally {
			isLoading = false;
		}
	}

	async function handleDelete(postId: string, postTitle: string) {
		if (!confirm(`確定要刪除草稿「${postTitle}」嗎？`)) return;

		try {
			const result = await deleteStore.mutate({ id: postId });
			if (result.data?.deletePost?.success) {
				notifications.success('草稿已刪除');
				loadDrafts();
			} else {
				notifications.error(result.data?.deletePost?.message || '刪除失敗');
			}
		} catch (error) {
			notifications.error('刪除草稿時發生錯誤');
		}
	}

	async function handlePublish(postId: string, postTitle: string) {
		publishingPostId = postId;
		try {
			const result = await publishStore.mutate({ id: postId });
			if (result.data?.publishPost) {
				notifications.success(`「${postTitle}」已發布`);
				// 直接更新本地狀態，不發網路請求
				if (postsData?.edges) {
					postsData = {
						...postsData,
						edges: postsData.edges.filter((edge: any) => edge.node.id !== postId),
						pageInfo: {
							...postsData.pageInfo,
							totalCount: Math.max(0, (postsData.pageInfo.totalCount || 1) - 1)
						}
					};
				}
			} else {
				notifications.error('發布失敗');
			}
		} catch (error) {
			notifications.error('發布文章時發生錯誤');
		} finally {
			publishingPostId = null;
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
	<title>我的草稿 - GraphQL Blog</title>
</svelte:head>

<div class="max-w-6xl mx-auto">
	<div class="mb-8 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
		<div>
			<h1 class="text-3xl font-bold">我的草稿</h1>
			<p class="text-gray-600 mt-1">
				共 {postsData?.pageInfo?.totalCount || 0} 篇草稿
			</p>
		</div>
		<a href="/posts/new" class="btn btn-primary">
			✏️ 撰寫新文章
		</a>
	</div>

	<!-- 草稿列表 -->
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
				<article class="card hover:shadow-md transition-shadow border-l-4 border-yellow-400">
					<div class="flex flex-col md:flex-row md:items-start md:justify-between gap-4">
						<div class="flex-1">
							<!-- 狀態標籤 -->
							<div class="flex items-center gap-2 mb-2">
								<span class="px-2 py-1 text-xs font-medium bg-yellow-100 text-yellow-800 rounded-full">
									草稿
								</span>
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
							<div class="text-sm text-gray-500">
								<time datetime={post.createdAt}>
									建立於 {formatDate(post.createdAt)}
								</time>
							</div>
						</div>

						<!-- 操作按鈕 -->
						<div class="flex items-center gap-2">
							<button
								onclick={() => handlePublish(post.id, post.title)}
								disabled={publishingPostId === post.id}
								class="bg-green-600 hover:bg-green-700 text-white px-3 py-1.5 rounded text-sm disabled:opacity-50 disabled:cursor-not-allowed"
							>
								{publishingPostId === post.id ? '發布中...' : '發布'}
							</button>
							<a
								href="/posts/{post.slug || post.id}/edit"
								class="btn btn-primary text-sm"
							>
								繼續編輯
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
						onclick={() => loadDrafts(currentPage - 1)}
						disabled={!postsData.pageInfo.hasPreviousPage || isLoading}
						class="btn btn-secondary disabled:opacity-50 disabled:cursor-not-allowed"
					>
						上一頁
					</button>

					<span class="px-4 text-gray-600">
						第 {postsData.pageInfo.currentPage} / {postsData.pageInfo.totalPages} 頁
					</span>

					<button
						onclick={() => loadDrafts(currentPage + 1)}
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
			<div class="text-6xl mb-4">📄</div>
			<p class="text-gray-600 mb-4">您目前沒有任何草稿</p>
			<a href="/posts/new" class="btn btn-primary">撰寫新文章</a>
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
