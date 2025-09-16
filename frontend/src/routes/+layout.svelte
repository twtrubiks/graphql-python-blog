<script lang="ts">
	import '../app.css';
	import { page } from '$app/state';
	import type { LayoutProps } from './$types';

	// Svelte 5 syntax - using $props
	let { children }: LayoutProps = $props();
</script>

<div class="min-h-screen flex flex-col">
	<!-- Navigation Header -->
	<header class="sticky top-0 z-50 w-full border-b bg-white/95 backdrop-blur supports-[backdrop-filter]:bg-white/60">
		<div class="container mx-auto flex h-16 items-center px-4">
			<nav class="flex items-center gap-6">
				<a href="/" class="flex items-center gap-2 font-semibold">
					<span class="text-xl">📝</span>
					<span>GraphQL Blog</span>
				</a>

				<div class="flex items-center gap-4 text-sm">
					<a
						href="/"
						class="transition-colors hover:text-primary-600 {page.url.pathname === '/' ? 'text-primary-600 font-medium' : 'text-gray-600'}"
					>
						首頁
					</a>
					<a
						href="/posts"
						class="transition-colors hover:text-primary-600 {page.url.pathname.startsWith('/posts') ? 'text-primary-600 font-medium' : 'text-gray-600'}"
					>
						文章
					</a>
					<a
						href="/about"
						class="transition-colors hover:text-primary-600 {page.url.pathname === '/about' ? 'text-primary-600 font-medium' : 'text-gray-600'}"
					>
						關於
					</a>
				</div>
			</nav>

			<div class="ml-auto flex items-center gap-4">
				<a href="/login" class="btn btn-ghost">
					登入
				</a>
				<a href="/register" class="btn btn-primary">
					註冊
				</a>
			</div>
		</div>
	</header>

	<!-- Main Content -->
	<main class="flex-1 container mx-auto px-4 py-8">
		{@render children()}
	</main>

	<!-- Footer -->
	<footer class="border-t bg-gray-50">
		<div class="container mx-auto px-4 py-6">
			<div class="flex flex-col items-center justify-between gap-4 md:flex-row">
				<p class="text-sm text-gray-600">
					© 2024 GraphQL Blog. All rights reserved.
				</p>
				<div class="flex gap-4 text-sm">
					<a href="/privacy" class="link">隱私政策</a>
					<a href="/terms" class="link">服務條款</a>
				</div>
			</div>
		</div>
	</footer>
</div>