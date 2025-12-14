<script lang="ts">
	interface Props {
		userId: string;
		username: string;
		fullName?: string | null;
		bio?: string | null;
		avatarUrl?: string | null;
		followersCount: number;
		followingCount: number;
	}

	let { userId, username, fullName, bio, avatarUrl, followersCount, followingCount }: Props = $props();
</script>

<article class="card hover:shadow-lg transition-shadow">
	<div class="flex items-start gap-4">
		<!-- Avatar -->
		{#if avatarUrl}
			<img
				src={avatarUrl}
				alt={username}
				class="w-16 h-16 rounded-full flex-shrink-0"
			/>
		{:else}
			<div class="w-16 h-16 rounded-full bg-primary-100 flex items-center justify-center flex-shrink-0">
				<span class="text-2xl font-bold text-primary-600">
					{username.charAt(0).toUpperCase()}
				</span>
			</div>
		{/if}

		<div class="flex-1 min-w-0">
			<!-- Username & Full Name -->
			<h3 class="text-lg font-semibold text-gray-900">
				{username}
			</h3>
			{#if fullName}
				<p class="text-sm text-gray-600">{fullName}</p>
			{/if}

			<!-- Bio -->
			{#if bio}
				<p class="mt-2 text-gray-600 text-sm line-clamp-2">
					{bio}
				</p>
			{/if}

			<!-- Stats -->
			<div class="mt-3 flex items-center gap-4 text-sm text-gray-500">
				<span>
					<strong class="text-gray-900">{followersCount}</strong> 追蹤者
				</span>
				<span>
					<strong class="text-gray-900">{followingCount}</strong> 追蹤中
				</span>
			</div>
		</div>
	</div>
</article>

<style>
	.line-clamp-2 {
		overflow: hidden;
		display: -webkit-box;
		-webkit-line-clamp: 2;
		-webkit-box-orient: vertical;
	}
</style>
