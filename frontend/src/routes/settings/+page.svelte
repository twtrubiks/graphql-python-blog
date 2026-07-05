<script lang="ts">
	import { UpdateMeStore } from '$houdini';
	import { auth } from '$lib/stores/auth.svelte';
	import { notifications } from '$lib/stores/notifications.svelte';
	import { useAuthGuard } from '$lib/utils/authGuard.svelte';

	const updateMeStore = new UpdateMeStore();

	// 表單狀態（從 auth store 初始化）
	let username = $state(auth.user?.username || '');
	let fullName = $state(auth.user?.fullName || '');
	let bio = $state(auth.user?.bio || '');
	let avatarUrl = $state(auth.user?.avatarUrl || '');
	let isSubmitting = $state(false);

	useAuthGuard();

	// 同步 auth store 變化
	$effect(() => {
		if (auth.user) {
			username = auth.user.username || '';
			fullName = auth.user.fullName || '';
			bio = auth.user.bio || '';
			avatarUrl = auth.user.avatarUrl || '';
		}
	});

	async function handleSubmit() {
		if (!username.trim()) {
			notifications.error('用戶名稱不可為空');
			return;
		}

		isSubmitting = true;
		try {
			const result = await updateMeStore.mutate({
				input: {
					username: username.trim() || null,
					fullName: fullName.trim() || null,
					bio: bio.trim() || null,
					avatarUrl: avatarUrl.trim() || null
				}
			});

			if (result.data?.updateMe) {
				// 更新 auth store
				auth.updateUser({
					username: result.data.updateMe.username,
					fullName: result.data.updateMe.fullName ?? undefined,
					bio: result.data.updateMe.bio ?? undefined,
					avatarUrl: result.data.updateMe.avatarUrl ?? undefined
				});
				notifications.success('個人資料已更新');
			} else if (result.errors) {
				const errorMessage = result.errors[0]?.message || '更新失敗';
				notifications.error(errorMessage);
			}
		} catch (error: any) {
			notifications.error(error.message || '更新失敗，請稍後再試');
		} finally {
			isSubmitting = false;
		}
	}

	// 頭像預覽錯誤處理
	let avatarError = $state(false);

	function handleAvatarError() {
		avatarError = true;
	}

	$effect(() => {
		// 讀取 avatarUrl 以建立響應式依賴，當它改變時重設錯誤狀態
		if (avatarUrl) {
			avatarError = false;
		}
	});
</script>

<svelte:head>
	<title>個人設定 - GraphQL Blog</title>
</svelte:head>

<div class="max-w-2xl mx-auto">
	<h1 class="text-3xl font-bold mb-8">個人設定</h1>

	<form onsubmit={(e) => { e.preventDefault(); handleSubmit(); }} class="card space-y-6">
		<!-- 頭像預覽 -->
		<div class="flex items-center gap-6">
			<div class="shrink-0">
				{#if avatarUrl && !avatarError}
					<img
						src={avatarUrl}
						alt="頭像預覽"
						class="w-20 h-20 rounded-full object-cover border-2 border-gray-200"
						onerror={handleAvatarError}
					/>
				{:else}
					<div class="w-20 h-20 rounded-full bg-primary-100 flex items-center justify-center border-2 border-gray-200">
						<span class="text-2xl font-bold text-primary-600">
							{username ? username.charAt(0).toUpperCase() : '?'}
						</span>
					</div>
				{/if}
			</div>
			<div class="flex-1">
				<p class="text-sm text-gray-600">
					您的頭像將顯示在文章和評論旁邊
				</p>
			</div>
		</div>

		<!-- 用戶名稱 -->
		<div>
			<label for="username" class="block text-sm font-medium text-gray-700 mb-1">
				用戶名稱 <span class="text-red-500">*</span>
			</label>
			<input
				type="text"
				id="username"
				bind:value={username}
				class="w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
				required
				placeholder="您的唯一識別名稱"
			/>
			<p class="mt-1 text-xs text-gray-500">用於登入和識別，必須唯一</p>
		</div>

		<!-- 顯示名稱 -->
		<div>
			<label for="fullName" class="block text-sm font-medium text-gray-700 mb-1">
				顯示名稱
			</label>
			<input
				type="text"
				id="fullName"
				bind:value={fullName}
				class="w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
				placeholder="您希望別人如何稱呼您"
			/>
		</div>

		<!-- 個人簡介 -->
		<div>
			<label for="bio" class="block text-sm font-medium text-gray-700 mb-1">
				個人簡介
			</label>
			<textarea
				id="bio"
				bind:value={bio}
				rows="4"
				maxlength="200"
				class="w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 resize-none"
				placeholder="介紹一下自己..."
			></textarea>
			<p class="mt-1 text-xs text-gray-500">{bio.length}/200 字</p>
		</div>

		<!-- 頭像 URL -->
		<div>
			<label for="avatarUrl" class="block text-sm font-medium text-gray-700 mb-1">
				頭像 URL
			</label>
			<input
				type="url"
				id="avatarUrl"
				bind:value={avatarUrl}
				class="w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
				placeholder="https://example.com/avatar.jpg"
			/>
			<p class="mt-1 text-xs text-gray-500">請輸入有效的圖片網址</p>
		</div>

		<!-- 提交按鈕 -->
		<div class="flex justify-end gap-4 pt-4 border-t">
			<a href="/" class="btn btn-secondary">
				取消
			</a>
			<button
				type="submit"
				class="btn btn-primary"
				disabled={isSubmitting}
			>
				{isSubmitting ? '儲存中...' : '儲存變更'}
			</button>
		</div>
	</form>

	<!-- 帳號資訊（唯讀） -->
	<div class="card mt-6">
		<h2 class="text-lg font-semibold mb-4">帳號資訊</h2>
		<div class="space-y-3 text-sm">
			<div class="flex justify-between">
				<span class="text-gray-600">電子郵件</span>
				<span class="font-medium">{auth.user?.email || '-'}</span>
			</div>
			<div class="flex justify-between">
				<span class="text-gray-600">帳號狀態</span>
				<span class="font-medium">
					{#if auth.user?.isActive}
						<span class="text-green-600">已啟用</span>
					{:else}
						<span class="text-red-600">未啟用</span>
					{/if}
				</span>
			</div>
		</div>
	</div>
</div>
