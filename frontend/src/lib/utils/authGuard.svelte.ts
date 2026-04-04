import { goto } from '$app/navigation';
import { auth } from '$lib/stores/auth.svelte';
import { notifications } from '$lib/stores/notifications.svelte';

/** 保護需要登入的路由，未登入時顯示通知並導向登入頁。 */
export function useAuthGuard(message: string = '請先登入') {
	// 防止 $effect 重複觸發時產生多次通知
	let hasRedirected = $state(false);

	$effect(() => {
		if (!auth.isAuthenticated && !hasRedirected) {
			hasRedirected = true;
			notifications.warning(message);
			goto('/login');
		}
	});
}
