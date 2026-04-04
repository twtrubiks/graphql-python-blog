<script lang="ts">
	import { page } from '$app/state';
	import FollowList from '$lib/components/FollowList.svelte';

	let username = $derived(page.params.username ?? '');
</script>

<svelte:head>
	<title>{username} 的追蹤中 - GraphQL Blog</title>
</svelte:head>

<FollowList {username} initialTab="following" />
