/**
 * 用戶在線狀態管理
 *
 * 使用 Svelte 5 Runes 管理全局用戶狀態
 */

export type UserStatusType = 'ONLINE' | 'OFFLINE';

interface UserStatusState {
	[userId: string]: UserStatusType;
}

function createUserStatusStore() {
	let statuses = $state<UserStatusState>({});

	return {
		get statuses() {
			return statuses;
		},

		// 更新單個用戶狀態
		updateStatus(userId: string, status: UserStatusType) {
			statuses = { ...statuses, [userId]: status };
		},

		// 獲取用戶狀態
		getStatus(userId: string): UserStatusType {
			return statuses[userId] || 'OFFLINE';
		},

		// 批量設置初始狀態
		setInitialStatuses(userStatuses: { userId: string; status: UserStatusType }[]) {
			const newStatuses: UserStatusState = {};
			userStatuses.forEach(({ userId, status }) => {
				newStatuses[userId] = status;
			});
			statuses = newStatuses;
		},

		// 清除所有狀態
		clear() {
			statuses = {};
		}
	};
}

export const userStatusStore = createUserStatusStore();
