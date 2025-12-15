<script lang="ts">
	import { RegisterStore } from '$houdini';
	import { auth } from '$lib/stores/auth.svelte';
	import { translateError } from '$lib/utils/errorTranslation';
	import { goto } from '$app/navigation';

	let email = $state('');
	let username = $state('');
	let password = $state('');
	let confirmPassword = $state('');
	let errors = $state<Record<string, string>>({});
	let isLoading = $state(false);

	const registerStore = new RegisterStore();

	// 密碼強度檢查
	let passwordChecks = $derived({
		minLength: password.length >= 8,
		hasUppercase: /[A-Z]/.test(password),
		hasLowercase: /[a-z]/.test(password),
		hasNumber: /[0-9]/.test(password)
	});

	let isPasswordValid = $derived(
		passwordChecks.minLength &&
		passwordChecks.hasUppercase &&
		passwordChecks.hasLowercase &&
		passwordChecks.hasNumber
	);

	let passwordMismatch = $derived(
		password && confirmPassword && password !== confirmPassword
	);

	let isFormValid = $derived(
		email &&
		username &&
		password &&
		confirmPassword &&
		password === confirmPassword &&
		isPasswordValid
	);

	function validateField(field: string, value: string) {
		errors = { ...errors };
		delete errors[field];

		switch (field) {
			case 'email':
				if (!value) {
					errors.email = '電子郵件為必填';
				} else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)) {
					errors.email = '請輸入有效的電子郵件地址';
				}
				break;
			case 'username':
				if (!value) {
					errors.username = '使用者名稱為必填';
				} else if (value.length < 3) {
					errors.username = '使用者名稱至少需要 3 個字元';
				} else if (!/^[a-zA-Z0-9_]+$/.test(value)) {
					errors.username = '使用者名稱只能包含字母、數字和底線';
				}
				break;
			case 'password':
				if (!value) {
					errors.password = '密碼為必填';
				} else if (value.length < 8) {
					errors.password = '密碼至少需要 8 個字元';
				} else if (!/[A-Z]/.test(value)) {
					errors.password = '密碼必須包含至少一個大寫字母';
				} else if (!/[a-z]/.test(value)) {
					errors.password = '密碼必須包含至少一個小寫字母';
				} else if (!/[0-9]/.test(value)) {
					errors.password = '密碼必須包含至少一個數字';
				}
				break;
			case 'confirmPassword':
				if (!value) {
					errors.confirmPassword = '請確認密碼';
				} else if (value !== password) {
					errors.confirmPassword = '密碼不相符';
				}
				break;
		}
	}

	async function handleSubmit(e: Event) {
		e.preventDefault();

		// Get values from form elements directly
		const form = e.target as HTMLFormElement;
		const formData = new FormData(form);
		const emailValue = formData.get('email') as string;
		const usernameValue = formData.get('username') as string;
		const passwordValue = formData.get('password') as string;

		validateField('email', emailValue);
		validateField('username', usernameValue);
		validateField('password', passwordValue);
		validateField('confirmPassword', confirmPassword);

		if (Object.keys(errors).length > 0) {
			return;
		}

		isLoading = true;

		console.log('Submitting registration with:', {
			email: emailValue,
			username: usernameValue,
			password: '***'
		});

		try {
			// Houdini expects variables directly, not wrapped in a variables object
			const result = await registerStore.mutate({
				email: emailValue,
				username: usernameValue,
				password: passwordValue
			});

			console.log('Registration result:', result);

			// Check if registration was successful
			if (result.data?.register) {
				console.log('Registration successful, logging in...');
				const { user, token } = result.data.register;

				// Save auth info
				await auth.login(user, token);
				console.log('Auth saved, redirecting to home...');

				// Navigate to home page
				await goto('/');
			} else if (result.errors) {
				// Handle GraphQL errors
				console.error('GraphQL errors:', result.errors);
				const errorMessage = result.errors[0]?.message || '註冊失敗';

				if (errorMessage.includes('email') || errorMessage.includes('Email')) {
					errors.email = '此電子郵件已被註冊';
				} else if (errorMessage.includes('username') || errorMessage.includes('Username')) {
					errors.username = '此使用者名稱已被使用';
				} else {
					errors.general = errorMessage;
				}
				isLoading = false;
			}
		} catch (err) {
			console.error('Registration error:', err);
			isLoading = false;

			if (err instanceof Error) {
				const errorMessage = err.message;
				const translatedMessage = translateError(errorMessage);

				// 根據錯誤內容分類到對應欄位
				if (errorMessage.toLowerCase().includes('email')) {
					errors.email = translatedMessage;
				} else if (errorMessage.toLowerCase().includes('username')) {
					errors.username = translatedMessage;
				} else if (errorMessage.toLowerCase().includes('password')) {
					errors.password = translatedMessage;
				} else {
					errors.general = translatedMessage;
				}
			} else {
				errors.general = '註冊失敗，請稍後再試';
			}
		}
	}
</script>

<svelte:head>
	<title>註冊 - GraphQL Blog</title>
</svelte:head>

<div class="max-w-md mx-auto mt-12">
	<div class="card">
		<h1 class="text-2xl font-bold mb-6">註冊新帳號</h1>

		{#if errors.general}
			<div class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
				{errors.general}
			</div>
		{/if}

		<form onsubmit={handleSubmit}>
			<div class="mb-4">
				<label for="email" class="block text-sm font-medium text-gray-700 mb-2">
					電子郵件 <span class="text-red-500">*</span>
				</label>
				<input
					type="email"
					id="email"
					name="email"
					bind:value={email}
					onblur={() => validateField('email', email)}
					required
					autocomplete="email"
					class="w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 {errors.email ? 'border-red-500' : 'border-gray-300'}"
					disabled={isLoading}
				/>
				{#if errors.email}
					<p class="mt-1 text-sm text-red-600">{errors.email}</p>
				{/if}
			</div>

			<div class="mb-4">
				<label for="username" class="block text-sm font-medium text-gray-700 mb-2">
					使用者名稱 <span class="text-red-500">*</span>
				</label>
				<input
					type="text"
					id="username"
					autocomplete="username"
					name="username"
					bind:value={username}
					onblur={() => validateField('username', username)}
					required
					class="w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 {errors.username ? 'border-red-500' : 'border-gray-300'}"
					disabled={isLoading}
				/>
				{#if errors.username}
					<p class="mt-1 text-sm text-red-600">{errors.username}</p>
				{/if}
				<p class="mt-1 text-xs text-gray-500">只能使用字母、數字和底線</p>
			</div>

			<div class="mb-4">
				<label for="password" class="block text-sm font-medium text-gray-700 mb-2">
					密碼 <span class="text-red-500">*</span>
				</label>
				<input
					type="password"
					id="password"
					autocomplete="new-password"
					name="password"
					bind:value={password}
					onblur={() => validateField('password', password)}
					required
					class="w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 {errors.password ? 'border-red-500' : 'border-gray-300'}"
					disabled={isLoading}
				/>
				{#if errors.password}
					<p class="mt-1 text-sm text-red-600">{errors.password}</p>
				{/if}
				<!-- 密碼要求清單 -->
				<div class="mt-2 text-xs space-y-1">
					<p class="text-gray-600 font-medium">密碼必須包含：</p>
					<p class={passwordChecks.minLength ? 'text-green-600' : 'text-gray-500'}>
						{passwordChecks.minLength ? '✓' : '○'} 至少 8 個字元
					</p>
					<p class={passwordChecks.hasUppercase ? 'text-green-600' : 'text-gray-500'}>
						{passwordChecks.hasUppercase ? '✓' : '○'} 至少一個大寫字母 (A-Z)
					</p>
					<p class={passwordChecks.hasLowercase ? 'text-green-600' : 'text-gray-500'}>
						{passwordChecks.hasLowercase ? '✓' : '○'} 至少一個小寫字母 (a-z)
					</p>
					<p class={passwordChecks.hasNumber ? 'text-green-600' : 'text-gray-500'}>
						{passwordChecks.hasNumber ? '✓' : '○'} 至少一個數字 (0-9)
					</p>
				</div>
			</div>

			<div class="mb-6">
				<label for="confirmPassword" class="block text-sm font-medium text-gray-700 mb-2">
					確認密碼 <span class="text-red-500">*</span>
				</label>
				<input
					type="password"
					id="confirmPassword"
					autocomplete="new-password"
					bind:value={confirmPassword}
					onblur={() => validateField('confirmPassword', confirmPassword)}
					required
					class="w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 {errors.confirmPassword || passwordMismatch ? 'border-red-500' : 'border-gray-300'}"
					disabled={isLoading}
				/>
				{#if errors.confirmPassword}
					<p class="mt-1 text-sm text-red-600">{errors.confirmPassword}</p>
				{:else if passwordMismatch}
					<p class="mt-1 text-sm text-red-600">密碼不相符</p>
				{/if}
			</div>

			<button
				type="submit"
				class="w-full btn btn-primary"
				disabled={isLoading || !isFormValid}
			>
				{isLoading ? '註冊中...' : '註冊'}
			</button>
		</form>

		<!-- 暫時註解：隱私政策和服務條款尚未實作
		<div class="mt-6 text-center">
			<p class="text-sm text-gray-600">
				點擊註冊即表示您同意我們的
				<a href="/terms" class="link text-primary-600">服務條款</a>
				和
				<a href="/privacy" class="link text-primary-600">隱私政策</a>
			</p>
		</div>
		-->

		<div class="mt-4 text-center text-sm text-gray-600">
			已經有帳號了？
			<a href="/login" class="link text-primary-600">登入</a>
		</div>
	</div>
</div>