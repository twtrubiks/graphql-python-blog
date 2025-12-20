<script lang="ts">
	interface Author {
		id: string;
		username: string;
		avatarUrl: string | null;
	}

	interface Tag {
		id: string;
		name: string;
		slug: string;
	}

	interface Props {
		postId: number;
		title: string;
		slug: string;
		excerpt: string;
		createdAt: string;
		author: Author;
		tags?: Tag[];
		totalComments: number;
		likesCount: number;
		searchQuery?: string;
	}

	let { postId, title, slug, excerpt, createdAt, author, tags = [], totalComments, likesCount, searchQuery = '' }: Props = $props();

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

	function formatDate(dateString: string) {
		const date = new Date(dateString);
		return new Intl.DateTimeFormat('zh-TW', {
			year: 'numeric',
			month: 'long',
			day: 'numeric'
		}).format(date);
	}
</script>

<article class="card hover:shadow-lg transition-shadow">
	<!-- Post Title -->
	<h2 class="text-xl font-semibold mb-2">
		<a
			href="/posts/{slug || postId}"
			class="hover:text-primary-600 transition-colors"
		>
			{@html highlightText(title, searchQuery)}
		</a>
	</h2>

	<!-- Post Excerpt -->
	<p class="text-gray-600 mb-4 line-clamp-3">
		{@html highlightText(excerpt || '暫無摘要', searchQuery)}
	</p>

	<!-- Post Tags -->
	{#if tags && tags.length > 0}
		<div class="flex flex-wrap gap-2 mb-4">
			{#each tags as tag}
				<a
					href="/posts/tag/{tag.slug}"
					class="text-xs px-2 py-1 bg-gray-100 text-gray-600 rounded-full hover:bg-primary-100 hover:text-primary-600 transition-colors"
					onclick={(e) => e.stopPropagation()}
				>
					#{tag.name}
				</a>
			{/each}
		</div>
	{/if}

	<!-- Post Meta -->
	<div class="flex items-center justify-between text-sm text-gray-500">
		<div class="flex items-center gap-2">
			{#if author.avatarUrl}
				<img
					src={author.avatarUrl}
					alt={author.username}
					class="w-6 h-6 rounded-full"
				/>
			{:else}
				<div class="w-6 h-6 rounded-full bg-primary-100 flex items-center justify-center">
					<span class="text-xs font-medium text-primary-600">
						{author.username.charAt(0).toUpperCase()}
					</span>
				</div>
			{/if}
			<a href="/users/{author.username}" class="hover:text-primary-600 transition-colors">
				{author.username}
			</a>
		</div>
		<time datetime={createdAt}>
			{formatDate(createdAt)}
		</time>
	</div>

	<!-- Post Stats -->
	<div class="mt-4 pt-4 border-t flex items-center gap-4 text-sm text-gray-500">
		<span class="flex items-center gap-1">
			<span>💬</span>
			<span>{totalComments}</span>
		</span>
		<span class="flex items-center gap-1">
			<span>❤️</span>
			<span>{likesCount}</span>
		</span>
		<a
			href="/posts/{slug || postId}"
			class="ml-auto link text-primary-600"
		>
			閱讀更多 →
		</a>
	</div>
</article>

<style>
	.line-clamp-3 {
		overflow: hidden;
		display: -webkit-box;
		-webkit-line-clamp: 3;
		-webkit-box-orient: vertical;
	}
</style>
