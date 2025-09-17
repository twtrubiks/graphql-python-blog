<script lang="ts">
	import '../app.css';
	import { page } from '$app/state';
	import { auth } from '$lib/stores/auth.svelte';
	import type { LayoutProps } from './$types';

	// Svelte 5 syntax - using $props
	let { children }: LayoutProps = $props();

	let showUserMenu = $state(false);

	async function handleLogout() {
		await auth.logout();
		showUserMenu = false;
	}
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
					<!-- 關於頁面 - 不在實作範圍內
					<a
						href="/about"
						class="transition-colors hover:text-primary-600 {page.url.pathname === '/about' ? 'text-primary-600 font-medium' : 'text-gray-600'}"
					>
						關於
					</a>
					-->
				</div>
			</nav>

			<div class="ml-auto flex items-center gap-4">
				{#if auth.isAuthenticated}
					<a href="/posts/new" class="btn btn-ghost">
						撰寫文章
					</a>
					<div class="relative">
						<button
							onclick={() => showUserMenu = !showUserMenu}
							class="flex items-center gap-2 px-3 py-2 rounded-md hover:bg-gray-100 transition-colors"
						>
							{#if auth.user?.avatarUrl}
								<img
									src={auth.user.avatarUrl}
									alt={auth.user.username}
									class="w-8 h-8 rounded-full"
								/>
							{:else}
								<div class="w-8 h-8 rounded-full bg-primary-100 flex items-center justify-center">
									<span class="text-sm font-medium text-primary-600">
										{auth.user?.username?.charAt(0).toUpperCase() || 'U'}
									</span>
								</div>
							{/if}
							<span class="text-sm font-medium">{auth.user?.username}</span>
							<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path>
							</svg>
						</button>

						{#if showUserMenu}
							<div class="absolute right-0 mt-2 w-48 bg-white rounded-md shadow-lg py-1 z-50 border">
								<!-- 個人資料頁面 - 不在實作範圍內
								<a
									href="/profile"
									class="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
									onclick={() => showUserMenu = false}
								>
									個人資料
								</a>
								-->
								<!-- 我的文章頁面 - 不在實作範圍內
								<a
									href="/posts/my"
									class="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
									onclick={() => showUserMenu = false}
								>
									我的文章
								</a>
								<hr class="my-1" />
								-->
								<button
									onclick={handleLogout}
									class="block w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
								>
									登出
								</button>
							</div>
						{/if}
					</div>
				{:else}
					<a href="/login" class="btn btn-ghost">
						登入
					</a>
					<a href="/register" class="btn btn-primary">
						註冊
					</a>
				{/if}
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