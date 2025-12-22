<script lang="ts">
	import { page } from '$app/state';
	import FollowList from '$lib/components/FollowList.svelte';
</script>

<svelte:head>
	<title>{page.params.username} 的追蹤中 - GraphQL Blog</title>
</svelte:head>

<FollowList username={page.params.username} initialTab="following" />
