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

	// 將 GraphQL 錯誤訊息轉換為中文
	function translateError(message: string): string {
		const errorMap: Record<string, string> = {
			'Invalid credentials': '電子郵件或密碼錯誤',
			'Invalid email or password': '電子郵件或密碼錯誤',
			'User not found': '找不到此使用者',
			'Invalid password': '密碼錯誤',
			'Account is disabled': '帳號已被停用',
			'User is not active': '帳號尚未啟用'
		};

		// 檢查是否有對應的翻譯
		for (const [key, value] of Object.entries(errorMap)) {
			if (message.toLowerCase().includes(key.toLowerCase())) {
				return value;
			}
		}

		// 如果沒有對應翻譯，返回原始訊息
		return message;
	}

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
			} else if (result.errors && result.errors.length > 0) {
				// 處理 GraphQL 錯誤，顯示具體錯誤訊息
				const errorMessage = result.errors[0]?.message || '登入失敗';
				error = translateError(errorMessage);
			}
		} catch (err) {
			// Houdini 在 GraphQL 錯誤時會拋出異常
			// 需要從 store 或其他來源取得實際錯誤訊息
			console.error('Login error:', err);

			// 嘗試從 loginStore 取得錯誤
			const storeErrors = (loginStore as any).errors;
			if (storeErrors && storeErrors.length > 0) {
				error = translateError(storeErrors[0]?.message || '登入失敗');
			} else if (err instanceof Error) {
				error = translateError(err.message);
			} else {
				// 當 Houdini 拋出 true 時，表示有 GraphQL 錯誤但無法取得詳細訊息
				// 使用通用的認證錯誤訊息
				error = '電子郵件或密碼錯誤';
			}
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
					autocomplete="email"
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
					autocomplete="current-password"
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