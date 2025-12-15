<script lang="ts">
	import { GetAllTagsStore } from '$houdini';

	interface Tag {
		id: string;
		name: string;
		slug: string;
	}

	interface Props {
		selectedTags: string[];
		onTagsChange: (tags: string[]) => void;
		disabled?: boolean;
	}

	let { selectedTags, onTagsChange, disabled = false }: Props = $props();

	const getAllTagsStore = new GetAllTagsStore();

	let inputValue = $state('');
	let showSuggestions = $state(false);
	let availableTags = $state<Tag[]>([]);
	let isLoading = $state(true);
	let inputElement: HTMLInputElement;

	// Fetch available tags on mount
	$effect(() => {
		loadTags();
	});

	async function loadTags() {
		isLoading = true;
		try {
			const result = await getAllTagsStore.fetch();
			if (result.data?.tags) {
				availableTags = result.data.tags;
			}
		} catch (error) {
			console.error('Failed to load tags:', error);
		} finally {
			isLoading = false;
		}
	}

	// Filter suggestions based on input
	let filteredSuggestions = $derived(
		availableTags
			.filter(
				(tag) =>
					tag.name.toLowerCase().includes(inputValue.toLowerCase()) &&
					!selectedTags.includes(tag.name)
			)
			.slice(0, 5)
	);

	function addTag(tagName: string) {
		const trimmed = tagName.trim();
		if (trimmed && !selectedTags.includes(trimmed)) {
			onTagsChange([...selectedTags, trimmed]);
		}
		inputValue = '';
		showSuggestions = false;
	}

	function removeTag(tagName: string) {
		onTagsChange(selectedTags.filter((t) => t !== tagName));
	}

	function handleKeyDown(event: KeyboardEvent) {
		if (event.key === 'Enter' || event.key === ',') {
			event.preventDefault();
			if (inputValue.trim()) {
				addTag(inputValue);
			}
		} else if (event.key === 'Backspace' && !inputValue && selectedTags.length > 0) {
			// Remove last tag when backspace is pressed with empty input
			removeTag(selectedTags[selectedTags.length - 1]);
		} else if (event.key === 'Escape') {
			showSuggestions = false;
		}
	}

	function handleInput() {
		showSuggestions = inputValue.length > 0;
	}

	function handleFocus() {
		if (inputValue.length > 0) {
			showSuggestions = true;
		}
	}

	function handleBlur() {
		// Delay hiding to allow click on suggestion
		setTimeout(() => {
			showSuggestions = false;
		}, 200);
	}

	function selectSuggestion(tag: Tag) {
		addTag(tag.name);
		inputElement?.focus();
	}
</script>

<div class="tag-input-container">
	<label for="tag-input" class="block text-sm font-medium text-gray-700 mb-2"> 標籤 </label>

	<!-- Selected tags and input -->
	<div
		class="flex flex-wrap gap-2 p-2 border rounded-md focus-within:ring-2 focus-within:ring-primary-500 {disabled
			? 'bg-gray-100 cursor-not-allowed'
			: 'border-gray-300 bg-white'}"
	>
		<!-- Selected tags as chips -->
		{#each selectedTags as tag}
			<span
				class="inline-flex items-center gap-1 px-2 py-1 bg-primary-100 text-primary-700 rounded-full text-sm"
			>
				#{tag}
				{#if !disabled}
					<button
						type="button"
						onclick={() => removeTag(tag)}
						class="hover:text-primary-900 focus:outline-none"
						aria-label="移除標籤 {tag}"
					>
						<svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M6 18L18 6M6 6l12 12"
							/>
						</svg>
					</button>
				{/if}
			</span>
		{/each}

		<!-- Input field -->
		<div class="relative flex-1 min-w-[120px]">
			<input
				bind:this={inputElement}
				type="text"
				id="tag-input"
				bind:value={inputValue}
				oninput={handleInput}
				onkeydown={handleKeyDown}
				onfocus={handleFocus}
				onblur={handleBlur}
				placeholder={selectedTags.length > 0 ? '新增更多標籤...' : '輸入標籤，按 Enter 新增'}
				class="w-full border-none outline-none bg-transparent text-sm py-1 {disabled
					? 'cursor-not-allowed'
					: ''}"
				{disabled}
				autocomplete="off"
			/>

			<!-- Suggestions dropdown -->
			{#if showSuggestions && filteredSuggestions.length > 0 && !disabled}
				<div
					class="absolute left-0 top-full mt-1 w-full bg-white border border-gray-200 rounded-md shadow-lg z-10 max-h-40 overflow-y-auto"
				>
					{#each filteredSuggestions as suggestion}
						<button
							type="button"
							class="w-full text-left px-3 py-2 text-sm hover:bg-gray-100 focus:bg-gray-100 focus:outline-none"
							onclick={() => selectSuggestion(suggestion)}
						>
							#{suggestion.name}
						</button>
					{/each}
				</div>
			{/if}
		</div>
	</div>

	<!-- Helper text -->
	<p class="mt-1 text-xs text-gray-500">輸入標籤名稱，按 Enter 或逗號新增。可從建議中選擇現有標籤。</p>
</div>
