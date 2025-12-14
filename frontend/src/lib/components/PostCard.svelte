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
	}

	let { postId, title, slug, excerpt, createdAt, author, tags = [], totalComments, likesCount }: Props = $props();

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
			{title}
		</a>
	</h2>

	<!-- Post Excerpt -->
	<p class="text-gray-600 mb-4 line-clamp-3">
		{excerpt || '暫無摘要'}
	</p>

	<!-- Post Tags -->
	{#if tags && tags.length > 0}
		<div class="flex flex-wrap gap-2 mb-4">
			{#each tags as tag}
				<span class="text-xs px-2 py-1 bg-gray-100 text-gray-600 rounded-full">
					#{tag.name}
				</span>
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
			<span>{author.username}</span>
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
