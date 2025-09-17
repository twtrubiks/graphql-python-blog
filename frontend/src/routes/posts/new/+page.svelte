<script lang="ts">
	import { CreatePostStore } from '$houdini';
	import { auth } from '$lib/stores/auth.svelte';
	import { goto } from '$app/navigation';

	const createPostStore = new CreatePostStore();

	let title = $state('');
	let content = $state('');
	let excerpt = $state('');
	let tags = $state('');
	let status = $state<'DRAFT' | 'PUBLISHED'>('DRAFT');
	let isSubmitting = $state(false);
	let errors = $state<Record<string, string>>({});

	let preview = $state(false);

	let renderedContent = $derived(renderMarkdown(content));

	$effect(() => {
		if (!auth.isAuthenticated) {
			goto('/login');
		}
	});

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

		status = publishStatus;
		isSubmitting = true;

		try {
			// Tags will be implemented in the future
			// const tagsArray = tags
			//	.split(',')
			//	.map(t => t.trim())
			//	.filter(t => t);

			// Houdini expects variables directly, not wrapped in a variables object
			const result = await createPostStore.mutate({
				input: {
					title,
					content,
					excerpt,
					status
					// tags: tagsArray // Tags not yet supported in backend
				}
			});

			if (result.data?.createPost) {
				// Clear draft from localStorage after successful post creation
				localStorage.removeItem('post_draft');
				await goto(`/posts/${result.data.createPost.slug || result.data.createPost.id}`);
			}
		} catch (err) {
			console.error('Failed to create post:', err);
			errors.general = '發表文章失敗，請稍後再試';
		} finally {
			isSubmitting = false;
		}
	}

	function handleAutoSave() {
		// 這裡可以實作自動儲存到 localStorage
		if (title || content) {
			const draft = { title, content, excerpt, tags };
			localStorage.setItem('post_draft', JSON.stringify(draft));
		}
	}

	let hasDraft = $state(false);
	let draftLoaded = $state(false);

	// 載入草稿
	$effect(() => {
		if (!draftLoaded) {
			const draft = localStorage.getItem('post_draft');
			if (draft) {
				try {
					const parsed = JSON.parse(draft);
					// Check if draft has actual content
					if (parsed.title || parsed.content) {
						hasDraft = true;
						title = parsed.title || '';
						content = parsed.content || '';
						excerpt = parsed.excerpt || '';
						tags = parsed.tags || '';
					}
				} catch (e) {
					console.error('Failed to load draft:', e);
				}
			}
			draftLoaded = true;
		}
	});

	function clearDraft() {
		localStorage.removeItem('post_draft');
		title = '';
		content = '';
		excerpt = '';
		tags = '';
		hasDraft = false;
	}

	// 自動儲存
	let autoSaveTimer: ReturnType<typeof setTimeout>;
	$effect(() => {
		clearTimeout(autoSaveTimer);
		autoSaveTimer = setTimeout(handleAutoSave, 2000);
		return () => clearTimeout(autoSaveTimer);
	});
</script>

<svelte:head>
	<title>撰寫新文章 - GraphQL Blog</title>
</svelte:head>

{#if auth.isAuthenticated}
	<div class="max-w-6xl mx-auto">
		<div class="flex items-center justify-between mb-6">
			<h1 class="text-3xl font-bold">撰寫新文章</h1>
			<div class="flex items-center gap-3">
				{#if hasDraft}
					<button
						onclick={clearDraft}
						class="btn btn-outline btn-sm"
						title="清除草稿並開始新文章"
					>
						清除草稿
					</button>
				{/if}
				<button
					onclick={() => preview = !preview}
					class="btn btn-secondary"
				>
					{preview ? '編輯' : '預覽'}
				</button>
				<button
					onclick={() => handleSubmit('DRAFT')}
					disabled={isSubmitting}
					class="btn btn-secondary"
				>
					儲存草稿
				</button>
				<button
					onclick={() => handleSubmit('PUBLISHED')}
					disabled={isSubmitting}
					class="btn btn-primary"
				>
					發表文章
				</button>
			</div>
		</div>

		{#if hasDraft && draftLoaded}
			<div class="bg-blue-50 border border-blue-200 text-blue-700 px-4 py-3 rounded mb-4 flex items-center justify-between">
				<span>已自動載入上次的草稿內容</span>
				<button onclick={clearDraft} class="text-blue-500 hover:text-blue-700 underline text-sm">
					清除並重新開始
				</button>
			</div>
		{/if}

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

				<div>
					<label for="tags" class="block text-sm font-medium text-gray-700 mb-2">
						標籤 <span class="text-xs text-gray-500">（功能開發中）</span>
					</label>
					<input
						type="text"
						id="tags"
						bind:value={tags}
						placeholder="輸入標籤，以逗號分隔（例如：JavaScript, React, 教學）"
						class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 opacity-50"
						disabled={true}
						title="標籤功能即將推出"
					/>
					<p class="mt-1 text-xs text-gray-500">標籤功能即將推出，敬請期待</p>
				</div>

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

				{#if tags}
					<div class="flex flex-wrap gap-2 mb-4">
						{#each tags.split(',').filter(t => t.trim()) as tag}
							<span class="px-3 py-1 bg-gray-100 text-gray-700 rounded-full text-sm">
								#{tag.trim()}
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
{:else}
	<div class="max-w-md mx-auto mt-12">
		<div class="card text-center">
			<p class="text-gray-600 mb-4">請先登入才能撰寫文章</p>
			<a href="/login" class="btn btn-primary">前往登入</a>
		</div>
	</div>
{/if}