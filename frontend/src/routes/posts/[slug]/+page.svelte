<script lang="ts">
	import { GetPostStore, AddCommentStore, LikePostStore, UnlikePostStore } from '$houdini';
	import { page } from '$app/state';
	import { auth } from '$lib/stores/auth.svelte';
	import { goto } from '$app/navigation';

	const postStore = new GetPostStore();
	const addCommentStore = new AddCommentStore();
	const likePostStore = new LikePostStore();
	const unlikePostStore = new UnlikePostStore();

	let post = $state<any>(null);
	let isLoading = $state(true);
	let error = $state('');

	let newComment = $state('');
	let isSubmittingComment = $state(false);
	let isLiking = $state(false);

	$effect(() => {
		loadPost();
	});

	async function loadPost() {
		isLoading = true;
		error = '';

		try {
			// In Svelte 5, page is a state object, not a store
			const postId = page.params.slug;
			const result = await postStore.fetch({
				variables: {
					id: postId
				}
			});

			if (result.data?.post) {
				post = result.data.post;
			} else {
				error = '文章不存在';
			}
		} catch (err) {
			error = '載入文章失敗';
			console.error('Failed to load post:', err);
		} finally {
			isLoading = false;
		}
	}

	async function handleAddComment() {
		if (!auth.isAuthenticated) {
			await goto('/login');
			return;
		}

		if (!newComment.trim()) {
			return;
		}

		isSubmittingComment = true;
		try {
			// Houdini expects variables directly, not wrapped in a variables object
			const result = await addCommentStore.mutate({
				postId: post.id,
				content: newComment
			});

			if (result.data?.addComment) {
				post.comments = [...post.comments, result.data.addComment];
				post.totalComments += 1;
				newComment = '';
			}
		} catch (err) {
			console.error('Failed to add comment:', err);
		} finally {
			isSubmittingComment = false;
		}
	}

	async function handleLike() {
		if (!auth.isAuthenticated) {
			await goto('/login');
			return;
		}

		isLiking = true;
		try {
			if (post.isLiked) {
				// Houdini expects variables directly, not wrapped in a variables object
				const result = await unlikePostStore.mutate({
					postId: post.id
				});
				if (result.data?.unlikePost?.success) {
					post.isLiked = false;
					post.likesCount -= 1;
				}
			} else {
				// Houdini expects variables directly, not wrapped in a variables object
				const result = await likePostStore.mutate({
					postId: post.id
				});
				if (result.data?.likePost) {
					post.isLiked = true;
					post.likesCount += 1;
				}
			}
		} catch (err) {
			console.error('Failed to toggle like:', err);
		} finally {
			isLiking = false;
		}
	}

	function formatDate(dateString: string) {
		const date = new Date(dateString);
		return new Intl.DateTimeFormat('zh-TW', {
			year: 'numeric',
			month: 'long',
			day: 'numeric',
			hour: '2-digit',
			minute: '2-digit'
		}).format(date);
	}

	function renderMarkdown(content: string) {
		// 簡單的 markdown 轉換，實際專案應使用 markdown 函式庫
		return content
			.replace(/^### (.*$)/gim, '<h3 class="text-xl font-semibold mt-4 mb-2">$1</h3>')
			.replace(/^## (.*$)/gim, '<h2 class="text-2xl font-semibold mt-6 mb-3">$1</h2>')
			.replace(/^# (.*$)/gim, '<h1 class="text-3xl font-bold mt-8 mb-4">$1</h1>')
			.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
			.replace(/\*(.+?)\*/g, '<em>$1</em>')
			.replace(/\[(.+?)\]\((.+?)\)/g, '<a href="$2" class="link text-primary-600">$1</a>')
			.replace(/\n\n/g, '</p><p class="mb-4">')
			.replace(/^/, '<p class="mb-4">')
			.replace(/$/, '</p>');
	}
</script>

<svelte:head>
	{#if post}
		<title>{post.title} - GraphQL Blog</title>
		<meta name="description" content={post.excerpt || post.title} />
	{:else}
		<title>載入中... - GraphQL Blog</title>
	{/if}
</svelte:head>

<div class="max-w-4xl mx-auto">
	{#if isLoading}
		<div class="animate-pulse">
			<div class="h-8 bg-gray-200 rounded w-3/4 mb-4"></div>
			<div class="h-4 bg-gray-200 rounded w-1/2 mb-8"></div>
			<div class="space-y-3">
				<div class="h-3 bg-gray-200 rounded"></div>
				<div class="h-3 bg-gray-200 rounded"></div>
				<div class="h-3 bg-gray-200 rounded w-5/6"></div>
			</div>
		</div>
	{:else if error}
		<div class="card bg-red-50 border-red-200">
			<p class="text-red-600">{error}</p>
			<a href="/posts" class="btn btn-secondary mt-4">返回文章列表</a>
		</div>
	{:else if post}
		<article>
			<!-- Article Header -->
			<header class="mb-8">
				<h1 class="text-4xl font-bold mb-4">{post.title}</h1>

				<div class="flex items-center gap-4 text-gray-600">
					<div class="flex items-center gap-2">
						{#if post.author.avatarUrl}
							<img
								src={post.author.avatarUrl}
								alt={post.author.username}
								class="w-10 h-10 rounded-full"
							/>
						{:else}
							<div class="w-10 h-10 rounded-full bg-primary-100 flex items-center justify-center">
								<span class="text-lg font-medium text-primary-600">
									{post.author.username.charAt(0).toUpperCase()}
								</span>
							</div>
						{/if}
						<div>
							<p class="font-medium text-gray-900">{post.author.fullName || post.author.username}</p>
							<p class="text-sm">@{post.author.username}</p>
						</div>
					</div>

					<time datetime={post.publishedAt || post.createdAt} class="text-sm">
						{formatDate(post.publishedAt || post.createdAt)}
					</time>
				</div>

				{#if post.tags?.length > 0}
					<div class="flex flex-wrap gap-2 mt-4">
						{#each post.tags as tag}
							<span class="px-3 py-1 bg-gray-100 text-gray-700 rounded-full text-sm">
								#{tag.name}
							</span>
						{/each}
					</div>
				{/if}
			</header>

			<!-- Article Content -->
			<div class="prose prose-lg max-w-none mb-8">
				{@html renderMarkdown(post.content)}
			</div>

			<!-- Article Actions -->
			<div class="flex items-center gap-4 py-4 border-y mb-8">
				<button
					onclick={handleLike}
					disabled={isLiking}
					class="flex items-center gap-2 px-4 py-2 rounded-md hover:bg-gray-100 transition-colors"
					class:text-red-600={post.isLiked}
				>
					<span class="text-xl">{post.isLiked ? '❤️' : '🤍'}</span>
					<span>{post.likesCount} 個讚</span>
				</button>

				<div class="flex items-center gap-2 text-gray-600">
					<span>💬</span>
					<span>{post.totalComments} 則留言</span>
				</div>
			</div>

			<!-- Author Info Card -->
			{#if post.author.bio}
				<div class="card bg-gray-50 mb-8">
					<h3 class="font-semibold mb-2">關於作者</h3>
					<div class="flex items-start gap-4">
						{#if post.author.avatarUrl}
							<img
								src={post.author.avatarUrl}
								alt={post.author.username}
								class="w-16 h-16 rounded-full"
							/>
						{:else}
							<div class="w-16 h-16 rounded-full bg-primary-100 flex items-center justify-center">
								<span class="text-2xl font-medium text-primary-600">
									{post.author.username.charAt(0).toUpperCase()}
								</span>
							</div>
						{/if}
						<div class="flex-1">
							<p class="font-medium">{post.author.fullName || post.author.username}</p>
							<p class="text-sm text-gray-600 mb-2">@{post.author.username}</p>
							<p class="text-gray-700">{post.author.bio}</p>
							<div class="flex gap-4 mt-3 text-sm text-gray-600">
								<span>{post.author.followersCount} 個粉絲</span>
								<span>{post.author.followingCount} 個追蹤</span>
							</div>
						</div>
					</div>
				</div>
			{/if}

			<!-- Comments Section -->
			<section>
				<h2 class="text-2xl font-semibold mb-6">留言區</h2>

				<!-- Add Comment Form -->
				{#if auth.isAuthenticated}
					<div class="card mb-6">
						<textarea
							bind:value={newComment}
							placeholder="分享你的想法..."
							class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
							rows="3"
							disabled={isSubmittingComment}
						></textarea>
						<div class="mt-3 flex justify-end">
							<button
								onclick={handleAddComment}
								disabled={isSubmittingComment || !newComment.trim()}
								class="btn btn-primary"
							>
								{isSubmittingComment ? '發表中...' : '發表留言'}
							</button>
						</div>
					</div>
				{:else}
					<div class="card bg-gray-50 mb-6">
						<p class="text-gray-600 mb-3">請登入後發表留言</p>
						<a href="/login" class="btn btn-primary">登入</a>
					</div>
				{/if}

				<!-- Comments List -->
				{#if post.comments?.length > 0}
					<div class="space-y-4">
						{#each post.comments as comment}
							{#if !comment.isDeleted}
								<div class="card">
									<div class="flex items-start gap-3">
										{#if comment.author.avatarUrl}
											<img
												src={comment.author.avatarUrl}
												alt={comment.author.username}
												class="w-8 h-8 rounded-full"
											/>
										{:else}
											<div class="w-8 h-8 rounded-full bg-gray-200 flex items-center justify-center">
												<span class="text-sm font-medium">
													{comment.author.username.charAt(0).toUpperCase()}
												</span>
											</div>
										{/if}
										<div class="flex-1">
											<div class="flex items-center gap-2 mb-1">
												<span class="font-medium">{comment.author.username}</span>
												<time class="text-xs text-gray-500">
													{formatDate(comment.createdAt)}
												</time>
												{#if comment.updatedAt !== comment.createdAt}
													<span class="text-xs text-gray-500">(已編輯)</span>
												{/if}
											</div>
											<p class="text-gray-700">{comment.content}</p>
										</div>
									</div>
								</div>
							{/if}
						{/each}
					</div>
				{:else}
					<p class="text-center text-gray-500 py-8">還沒有留言，來當第一個留言的人吧！</p>
				{/if}
			</section>
		</article>
	{/if}
</div>