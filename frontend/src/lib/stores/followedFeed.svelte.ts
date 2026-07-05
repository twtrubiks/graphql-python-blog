/**
 * 追蹤動態共用 store
 *
 * FollowedUserPosted 訂閱由 +layout.svelte 的訂閱管理器統一建立（全站僅一條 WebSocket 訂閱），
 * 收到的資料寫入此 store 供 /following 頁面消費，避免頁面自行建立第二條重複訂閱。
 */

export type FeedStatus = 'idle' | 'connecting' | 'connected' | 'error';

class FollowedFeedStore {
	/** 最新收到的追蹤用戶新文章（消費端處理後應清為 null） */
	latestPost = $state<any>(null);

	/** 訂閱連線狀態（由 layout 的訂閱管理器更新） */
	status = $state<FeedStatus>('idle');

	reset() {
		this.latestPost = null;
		this.status = 'idle';
	}
}

export const followedFeed = new FollowedFeedStore();
