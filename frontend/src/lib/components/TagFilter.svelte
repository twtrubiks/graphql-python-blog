<script lang="ts">
	interface Tag {
		id: string;
		name: string;
		slug: string;
	}

	interface Props {
		availableTags: Tag[];
		selectedTags: string[];
		requireAll: boolean;
		onTagToggle: (slug: string) => void;
		onRequireAllToggle: () => void;
		onClear: () => void;
	}

	let {
		availableTags,
		selectedTags,
		requireAll,
		onTagToggle,
		onRequireAllToggle,
		onClear
	}: Props = $props();

	let isExpanded = $state(false);

	// 顯示已選中標籤數量
	let selectedCount = $derived(selectedTags.length);
</script>

<div class="tag-filter card mb-4">
	<!-- 篩選器標題列 -->
	<div class="flex items-center justify-between">
		<button
			onclick={() => (isExpanded = !isExpanded)}
			class="flex items-center gap-2 text-sm font-medium text-gray-700 hover:text-primary-600"
			type="button"
		>
			<span>標籤篩選</span>
			{#if selectedCount > 0}
				<span class="px-2 py-0.5 bg-primary-100 text-primary-600 rounded-full text-xs">
					{selectedCount}
				</span>
			{/if}
			<svg
				class="w-4 h-4 transition-transform {isExpanded ? 'rotate-180' : ''}"
				fill="none"
				stroke="currentColor"
				viewBox="0 0 24 24"
			>
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
			</svg>
		</button>

		{#if selectedCount > 0}
			<button onclick={onClear} class="text-sm text-gray-500 hover:text-red-500" type="button">
				清除篩選
			</button>
		{/if}
	</div>

	<!-- 展開的標籤選擇區 -->
	{#if isExpanded}
		<div class="mt-4 space-y-4">
			<!-- AND/OR 切換 -->
			{#if selectedCount > 1}
				<div class="flex items-center gap-4 text-sm p-3 bg-gray-50 rounded-lg">
					<span class="text-gray-600">篩選模式：</span>
					<label class="flex items-center gap-2 cursor-pointer">
						<input
							type="radio"
							name="filterMode"
							checked={!requireAll}
							onchange={() => {
								if (requireAll) onRequireAllToggle();
							}}
							class="text-primary-600"
						/>
						<span class="font-medium">OR</span>
						<span class="text-gray-500">（任一標籤）</span>
					</label>
					<label class="flex items-center gap-2 cursor-pointer">
						<input
							type="radio"
							name="filterMode"
							checked={requireAll}
							onchange={() => {
								if (!requireAll) onRequireAllToggle();
							}}
							class="text-primary-600"
						/>
						<span class="font-medium">AND</span>
						<span class="text-gray-500">（所有標籤）</span>
					</label>
				</div>
			{/if}

			<!-- 標籤列表 -->
			{#if availableTags.length > 0}
				<div class="flex flex-wrap gap-2">
					{#each availableTags as tag}
						<button
							onclick={() => onTagToggle(tag.slug)}
							class="tag-item {selectedTags.includes(tag.slug) ? 'tag-item-selected' : ''}"
							type="button"
						>
							#{tag.name}
						</button>
					{/each}
				</div>
			{:else}
				<p class="text-sm text-gray-500">暫無可用標籤</p>
			{/if}
		</div>
	{/if}

	<!-- 已選標籤快速顯示（收合狀態） -->
	{#if !isExpanded && selectedCount > 0}
		<div class="flex flex-wrap items-center gap-2 mt-3">
			{#each availableTags.filter((t) => selectedTags.includes(t.slug)) as tag}
				<span
					class="text-xs px-2 py-1 bg-primary-100 text-primary-600 rounded-full flex items-center gap-1"
				>
					#{tag.name}
					<button
						onclick={() => onTagToggle(tag.slug)}
						class="hover:text-red-500 font-bold"
						type="button"
					>
						&times;
					</button>
				</span>
			{/each}
			{#if requireAll && selectedCount > 1}
				<span class="text-xs text-gray-500 italic">(AND 模式)</span>
			{:else if selectedCount > 1}
				<span class="text-xs text-gray-500 italic">(OR 模式)</span>
			{/if}
		</div>
	{/if}
</div>

<style>
	.tag-item {
		@apply text-xs px-3 py-1.5 bg-gray-100 text-gray-600 rounded-full hover:bg-gray-200 transition-colors cursor-pointer border-2 border-transparent;
	}

	.tag-item-selected {
		@apply bg-primary-100 text-primary-600 border-primary-500;
	}
</style>
