<script lang="ts">
	import { UpdatePostStore, GetPostStore } from '$houdini';
	import { auth } from '$lib/stores/auth.svelte';
	import { notifications } from '$lib/stores/notifications.svelte';
	import { useAuthGuard } from '$lib/utils/authGuard.svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import TagInput from '$lib/components/TagInput.svelte';

	const updatePostStore = new UpdatePostStore();
	const getPostStore = new GetPostStore();

	// 表單狀態
	let title = $state('');
	let content = $state('');
	let excerpt = $state('');
	let selectedTags = $state<string[]>([]);
	let status = $state<'DRAFT' | 'PUBLISHED'>('DRAFT');
	let originalStatus = $state<'DRAFT' | 'PUBLISHED'>('DRAFT');
	let isSubmitting = $state(false);
	let isLoading = $state(true);
	let errors = $state<Record<string, string>>({});
	let showUnpublishConfirm = $state(false);

	function handleTagsChange(tags: string[]) {
		selectedTags = tags;
	}

	// 原始文章資料
	let postId = $state('');
	let originalSlug = $state('');

	// 權限狀態
	let hasPermission = $state(false);
	let hasPermissionRedirected = $state(false);

	// 預覽
	let renderedContent = $derived(renderMarkdown(content));

	// 登入檢查
	useAuthGuard('請先登入才能編輯文章');

	// 載入文章資料
	$effect(() => {
		if (auth.isAuthenticated && !hasPermissionRedirected) {
			loadPost();
		}
	});

	async function loadPost() {
		isLoading = true;

		try {
			const slug = page.params.slug;
			const result = await getPostStore.fetch({ variables: { id: slug } });

			if (result.data?.post) {
				const post = result.data.post;

				// 權限檢查：確認是否為作者
				if (String(auth.user?.id) !== String(post.author.id)) {
					notifications.error('您沒有權限編輯此文章');
					hasPermissionRedirected = true;
					goto(`/posts/${slug}`);
					return;
				}

				hasPermission = true;
				postId = post.id;
				originalSlug = post.slug;
				title = post.title;
				content = post.content;
				excerpt = post.excerpt || '';
				status = post.status as 'DRAFT' | 'PUBLISHED';
				originalStatus = post.status as 'DRAFT' | 'PUBLISHED';
				// 載入現有標籤
				selectedTags = post.tags?.map((t: { name: string }) => t.name) || [];
			} else {
				notifications.error('文章不存在');
				goto('/posts');
			}
		} catch (err) {
			console.error('Failed to load post:', err);
			notifications.error('載入文章失敗');
		} finally {
			isLoading = false;
		}
	}

	function renderMarkdown(text: string) {
		if (!text) return '';

		return text
			.replace(/^### (.*$)/gim, '<h3 class="text-xl font-semibold mt-4 mb-2">$1</h3>')
			.replace(/^## (.*$)/gim, '<h2 class="text-2xl font-semibold mt-6 mb-3">$1</h2>')
			.replace(/^# (.*$)/gim, '<h1 class="text-3xl font-bold mt-8 mb-4">$1</h1>')
			.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
			.replace(/\*(.+?)\*/g, '<em>$1</em>')
			.replace(/`(.+?)`/g, '<code class="bg-gray-100 px-1 py-0.5 rounded">$1</code>')
			.replace(/\[(.+?)\]\((.+?)\)/g, '<a href="$2" class="link text-primary-600">$1</a>')
			.replace(/^- (.+)$/gim, '<li class="ml-4">$1</li>')
			.replace(/^[0-9]+\. (.+)$/gim, '<li class="ml-4">$1</li>')
			.replace(/\n\n/g, '</p><p class="mb-4">')
			.replace(/^/, '<p class="mb-4">')
			.replace(/$/, '</p>');
	}

	function validateForm() {
		errors = {};

		if (!title.trim()) {
			errors.title = '標題為必填';
		} else if (title.length < 5) {
			errors.title = '標題至少需要 5 個字元';
		}

		if (!content.trim()) {
			errors.content = '內容為必填';
		} else if (content.length < 20) {
			errors.content = '內容至少需要 20 個字元';
		}

		if (!excerpt.trim()) {
			excerpt = content.substring(0, 150) + (content.length > 150 ? '...' : '');
		}

		return Object.keys(errors).length === 0;
	}

	async function handleSubmit(publishStatus: 'DRAFT' | 'PUBLISHED') {
		if (!validateForm()) {
			return;
		}

		// 如果是已發布文章要改為草稿，顯示確認對話框
		if (originalStatus === 'PUBLISHED' && publishStatus === 'DRAFT') {
			showUnpublishConfirm = true;
			return;
		}

		await submitPost(publishStatus);
	}

	async function submitPost(publishStatus: 'DRAFT' | 'PUBLISHED') {
		isSubmitting = true;

		try {
			const result = await updatePostStore.mutate({
				id: postId,
				input: {
					title,
					content,
					excerpt,
					status: publishStatus,
					tags: selectedTags.length > 0 ? selectedTags : null
				}
			});

			if (result.data?.updatePost) {
				notifications.success('文章更新成功');
				const newSlug = result.data.updatePost.slug;
				await goto(`/posts/${newSlug}`);
			}
		} catch (err: any) {
			console.error('Failed to update post:', err);
			errors.general = err.message || '更新文章失敗，請稍後再試';
		} finally {
			isSubmitting = false;
		}
	}

	async function confirmUnpublish() {
		showUnpublishConfirm = false;
		await submitPost('DRAFT');
	}

	function handleCancel() {
		goto(`/posts/${originalSlug}`);
	}
</script>

<svelte:head>
	<title>編輯文章 - GraphQL Blog</title>
</svelte:head>

{#if isLoading}
	<div class="max-w-6xl mx-auto">
		<div class="animate-pulse">
			<div class="h-8 bg-gray-200 rounded w-1/4 mb-6"></div>
			<div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
				<div class="space-y-4">
					<div class="h-10 bg-gray-200 rounded"></div>
					<div class="h-20 bg-gray-200 rounded"></div>
					<div class="h-64 bg-gray-200 rounded"></div>
				</div>
				<div class="h-96 bg-gray-200 rounded"></div>
			</div>
		</div>
	</div>
{:else if hasPermission}
	<div class="max-w-6xl mx-auto">
		<div class="flex items-center justify-between mb-6">
			<div class="flex items-center gap-3">
				<h1 class="text-3xl font-bold">編輯文章</h1>
				{#if originalStatus === 'PUBLISHED'}
					<span class="px-3 py-1 text-sm font-medium bg-green-100 text-green-800 rounded-full">
						已發布
					</span>
				{:else}
					<span class="px-3 py-1 text-sm font-medium bg-yellow-100 text-yellow-800 rounded-full">
						草稿
					</span>
				{/if}
			</div>
			<div class="flex items-center gap-3">
				<button
					onclick={handleCancel}
					class="btn btn-outline"
					disabled={isSubmitting}
				>
					取消
				</button>
				<button
					onclick={() => handleSubmit('DRAFT')}
					disabled={isSubmitting}
					class="btn btn-secondary"
				>
					{originalStatus === 'PUBLISHED' ? '取消發布' : '儲存為草稿'}
				</button>
				<button
					onclick={() => handleSubmit('PUBLISHED')}
					disabled={isSubmitting}
					class="btn btn-primary"
				>
					{isSubmitting ? '更新中...' : (originalStatus === 'PUBLISHED' ? '更新文章' : '發布文章')}
				</button>
			</div>
		</div>

		{#if errors.general}
			<div class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
				{errors.general}
			</div>
		{/if}

		<div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
			<!-- Editor Column -->
			<div class="space-y-4">
				<div>
					<label for="title" class="block text-sm font-medium text-gray-700 mb-2">
						標題 <span class="text-red-500">*</span>
					</label>
					<input
						type="text"
						id="title"
						bind:value={title}
						placeholder="輸入文章標題..."
						class="w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 {errors.title ? 'border-red-500' : 'border-gray-300'}"
						disabled={isSubmitting}
					/>
					{#if errors.title}
						<p class="mt-1 text-sm text-red-600">{errors.title}</p>
					{/if}
				</div>

				<div>
					<label for="excerpt" class="block text-sm font-medium text-gray-700 mb-2">
						摘要
					</label>
					<textarea
						id="excerpt"
						bind:value={excerpt}
						placeholder="輸入文章摘要（選填，若留空將自動擷取內容前 150 字）"
						rows="2"
						class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
						disabled={isSubmitting}
					></textarea>
				</div>

				<TagInput
					selectedTags={selectedTags}
					onTagsChange={handleTagsChange}
					disabled={isSubmitting}
				/>

				<div>
					<label for="content" class="block text-sm font-medium text-gray-700 mb-2">
						內容 <span class="text-red-500">*</span>
					</label>
					<textarea
						id="content"
						bind:value={content}
						placeholder="使用 Markdown 語法撰寫文章內容..."
						rows="20"
						class="w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 font-mono text-sm {errors.content ? 'border-red-500' : 'border-gray-300'}"
						disabled={isSubmitting}
					></textarea>
					{#if errors.content}
						<p class="mt-1 text-sm text-red-600">{errors.content}</p>
					{/if}
				</div>

				<!-- Markdown Help -->
				<div class="card bg-gray-50">
					<h3 class="font-medium mb-2">Markdown 語法提示</h3>
					<div class="text-sm text-gray-600 space-y-1 font-mono">
						<p># 標題一</p>
						<p>## 標題二</p>
						<p>### 標題三</p>
						<p>**粗體** *斜體* `程式碼`</p>
						<p>[連結文字](https://example.com)</p>
						<p>- 無序列表</p>
						<p>1. 有序列表</p>
					</div>
				</div>
			</div>

			<!-- Preview Column -->
			<div class="card h-fit sticky top-20">
				<h2 class="text-xl font-semibold mb-4">預覽</h2>

				{#if title}
					<h1 class="text-3xl font-bold mb-4">{title}</h1>
				{:else}
					<p class="text-gray-400 mb-4">文章標題將顯示在這裡</p>
				{/if}

				{#if selectedTags.length > 0}
					<div class="flex flex-wrap gap-2 mb-4">
						{#each selectedTags as tag}
							<span class="px-3 py-1 bg-gray-100 text-gray-700 rounded-full text-sm">
								#{tag}
							</span>
						{/each}
					</div>
				{/if}

				<div class="prose max-w-none">
					{#if content}
						{@html renderedContent}
					{:else}
						<p class="text-gray-400">文章內容預覽將顯示在這裡</p>
					{/if}
				</div>
			</div>
		</div>
	</div>
{:else if !auth.isAuthenticated}
	<div class="max-w-md mx-auto mt-12">
		<div class="card text-center">
			<p class="text-gray-600 mb-4">請先登入才能編輯文章</p>
			<a href="/login" class="btn btn-primary">前往登入</a>
		</div>
	</div>
{/if}

<!-- 取消發布確認對話框 -->
{#if showUnpublishConfirm}
	<div class="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
		<div class="bg-white rounded-lg shadow-xl max-w-md w-full mx-4 p-6">
			<h3 class="text-xl font-semibold mb-2">確認取消發布？</h3>
			<p class="text-gray-600 mb-6">
				將已發布的文章改為草稿會使其從公開列表中移除，讀者將無法再看到這篇文章。
			</p>
			<div class="flex justify-end gap-3">
				<button
					onclick={() => showUnpublishConfirm = false}
					class="btn btn-secondary"
				>
					取消
				</button>
				<button
					onclick={confirmUnpublish}
					class="btn bg-amber-600 text-white hover:bg-amber-700"
				>
					確認取消發布
				</button>
			</div>
		</div>
	</div>
{/if}
