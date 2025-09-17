<script lang="ts">
	import { fade, fly } from 'svelte/transition';
	import { onDestroy } from 'svelte';

	interface Props {
		message?: string;
		type?: 'info' | 'success' | 'warning' | 'error';
		duration?: number;
		onClose?: (() => void) | null;
		link?: { text: string; href: string } | null;
	}

	let {
		message = '',
		type = 'info',
		duration = 5000,
		onClose = null,
		link = null
	}: Props = $props();

	let visible = $state(true);
	let timer: ReturnType<typeof setTimeout> | null = null;

	$effect(() => {
		// 設定自動關閉計時器
		if (duration > 0) {
			timer = setTimeout(() => {
				close();
			}, duration);
		}
	});

	onDestroy(() => {
		if (timer) {
			clearTimeout(timer);
		}
	});

	function close() {
		visible = false;
		if (onClose) {
			setTimeout(onClose, 300); // 等待動畫完成後執行回調
		}
	}

	function getTypeStyles() {
		switch (type) {
			case 'success':
				return 'bg-green-50 border-green-200 text-green-800';
			case 'warning':
				return 'bg-yellow-50 border-yellow-200 text-yellow-800';
			case 'error':
				return 'bg-red-50 border-red-200 text-red-800';
			default:
				return 'bg-blue-50 border-blue-200 text-blue-800';
		}
	}

	function getIcon() {
		switch (type) {
			case 'success':
				return '✅';
			case 'warning':
				return '⚠️';
			case 'error':
				return '❌';
			default:
				return 'ℹ️';
		}
	}
</script>

{#if visible}
	<div
		class="fixed top-4 right-4 max-w-sm w-full z-50"
		transition:fly={{ y: -20, duration: 300 }}
	>
		<div
			class="rounded-lg border shadow-lg p-4 {getTypeStyles()}"
			role="alert"
		>
			<div class="flex items-start">
				<span class="text-xl mr-3" aria-hidden="true">
					{getIcon()}
				</span>
				<div class="flex-1">
					<p class="font-medium">{message}</p>
					{#if link}
						<a
							href={link.href}
							class="mt-1 text-sm underline hover:no-underline"
						>
							{link.text}
						</a>
					{/if}
				</div>
				<button
					type="button"
					onclick={close}
					class="ml-3 -mr-1 -mt-1 p-1.5 rounded-md hover:bg-black/5 transition-colors"
					aria-label="關閉通知"
				>
					<svg
						class="w-4 h-4"
						fill="none"
						stroke="currentColor"
						viewBox="0 0 24 24"
					>
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2"
							d="M6 18L18 6M6 6l12 12"
						/>
					</svg>
				</button>
			</div>
		</div>
	</div>
{/if}

<style>
	/* 可選：為多個通知堆疊預留樣式 */
	:global(.notification-stack) {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}
</style>