<script lang="ts">
	import { LoginStore } from '$houdini';
	import { auth } from '$lib/stores/auth.svelte';
	import { goto } from '$app/navigation';

	// Svelte 5: 使用 $state rune
	let email = $state('');
	let password = $state('');
	let error = $state('');
	let isLoading = $state(false);

	// 建立 Houdini mutation store
	const loginStore = new LoginStore();

	async function handleSubmit(e: Event) {
		e.preventDefault();
		error = '';
		isLoading = true;

		try {
			// Houdini expects variables directly, not wrapped in a variables object
			const result = await loginStore.mutate({
				email,
				password
			});

			if (result.data?.login) {
				// 儲存認證資訊
				await auth.login(result.data.login.user, result.data.login.token);
				// 導向首頁
				await goto('/');
			}
		} catch (err) {
			error = err instanceof Error ? err.message : '登入失敗，請稍後再試';
		} finally {
			isLoading = false;
		}
	}
</script>

<svelte:head>
	<title>登入 - GraphQL Blog</title>
</svelte:head>

<div class="max-w-md mx-auto mt-12">
	<div class="card">
		<h1 class="text-2xl font-bold mb-6">登入</h1>

		{#if error}
			<div class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
				{error}
			</div>
		{/if}

		<form onsubmit={handleSubmit}>
			<div class="mb-4">
				<label for="email" class="block text-sm font-medium text-gray-700 mb-2">
					電子郵件
				</label>
				<input
					type="email"
					id="email"
					bind:value={email}
					required
					class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
					disabled={isLoading}
				/>
			</div>

			<div class="mb-6">
				<label for="password" class="block text-sm font-medium text-gray-700 mb-2">
					密碼
				</label>
				<input
					type="password"
					id="password"
					bind:value={password}
					required
					class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
					disabled={isLoading}
				/>
			</div>

			<button
				type="submit"
				class="w-full btn btn-primary"
				disabled={isLoading}
			>
				{isLoading ? '登入中...' : '登入'}
			</button>
		</form>

		<div class="mt-4 text-center text-sm text-gray-600">
			還沒有帳號？
			<a href="/register" class="link text-primary-600">註冊</a>
		</div>
	</div>
</div>