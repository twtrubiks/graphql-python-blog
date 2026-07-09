/**
 * 新文章列表刷新共用 store
 *
 * PostPublished 訂閱由 +layout.svelte 的訂閱管理器統一建立（全站僅一條 WebSocket 訂閱），
 * 收到新文章事件時累加 pendingCount，供文章列表頁／首頁顯示「有新文章」提示條。
 * 列表成功重新載入後由頁面呼叫 clear() 歸零。
 */

class PostFeedStore {
	/** 自列表上次載入以來發布的新文章數 */
	pendingCount = $state(0);

	notifyNewPost() {
		this.pendingCount++;
	}

	clear() {
		this.pendingCount = 0;
	}
}

export const postFeed = new PostFeedStore();
