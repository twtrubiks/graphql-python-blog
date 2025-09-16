<script lang="ts">
	import type { Snippet } from 'svelte';

	// Svelte 5: 使用 $props rune
	interface ButtonProps {
		variant?: 'primary' | 'secondary' | 'ghost';
		size?: 'sm' | 'md' | 'lg';
		disabled?: boolean;
		onclick?: () => void;
		children: Snippet;
	}

	let {
		variant = 'primary',
		size = 'md',
		disabled = false,
		onclick,
		children
	}: ButtonProps = $props();

	// Svelte 5: 使用 $derived rune
	let sizeClasses = $derived({
		sm: 'px-3 py-1.5 text-sm',
		md: 'px-4 py-2 text-sm',
		lg: 'px-6 py-3 text-base'
	}[size]);

	let variantClasses = $derived({
		primary: 'btn-primary',
		secondary: 'btn-secondary',
		ghost: 'btn-ghost'
	}[variant]);

	let buttonClasses = $derived(`btn ${variantClasses} ${sizeClasses}`);
</script>

<button
	class={buttonClasses}
	{disabled}
	{onclick}
>
	{@render children()}
</button>