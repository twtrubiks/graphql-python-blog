<script lang="ts">
	interface Props {
		count: number;
		onRefresh: () => void;
	}

	let { count, onRefresh }: Props = $props();
</script>

{#if count > 0}
	<div class="mb-4">
		<button
			onclick={onRefresh}
			class="w-full py-2 px-4 rounded-md border border-primary-200 bg-primary-50 text-primary-700 text-sm font-medium hover:bg-primary-100 transition-colors"
		>
			✨ 有 {count} 篇新文章，點擊更新列表
		</button>
	</div>
{/if}
