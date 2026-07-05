/**
 * 認證狀態管理 - Svelte 5 Runes 示範
 *
 * Svelte 5 引入了 Runes，這是一種新的響應式系統：
 * - $state: 創建響應式狀態
 * - $derived: 計算衍生值（類似 computed）
 * - $effect: 響應式副作用（類似 watch）
 *
 * 檔案命名規則：
 * - .svelte.ts: 可以使用 Runes 的 TypeScript 檔案
 * - .ts: 純 TypeScript，不能使用 Runes
 *
 * 這個 Store 管理：
 * 1. 用戶登入狀態
 * 2. JWT Token 儲存和驗證
 * 3. 自動登出（Token 過期）
 * 4. 持久化（localStorage）
 */

import { browser } from '$app/environment';
import { goto } from '$app/navigation';
import { jwtDecode } from 'jwt-decode';
import { GetMeStore } from '$houdini';

interface User {
	id: string;
	// schema 上 email 為 nullable（非本人查詢時不回傳）
	email: string | null;
	username: string;
	fullName?: string | null;
	bio?: string | null;
	avatarUrl?: string | null;
	isActive?: boolean;
	isSuperuser?: boolean;
	createdAt?: string;
	followersCount?: number;
	followingCount?: number;
}

interface AuthState {
	user: User | null;
	token: string | null;
	isAuthenticated: boolean;
	isLoading: boolean;
}

interface JWTPayload {
	exp: number;  // Token 過期時間（Unix timestamp）
	sub: string;  // Subject（通常是用戶 ID）
	// 其他自定義欄位可在此擴展
}

function createAuthStore() {
	/**
	 * Svelte 5 Runes 使用方式：
	 *
	 * $state: 創建響應式狀態
	 * - 自動追蹤變更
	 * - 觸發相關元件重新渲染
	 */
	let user = $state<User | null>(null);
	let token = $state<string | null>(null);
	let isLoading = $state(false);

	/**
	 * $derived: 計算衍生狀態
	 * - 依賴的狀態變化時自動重新計算
	 * - 類似 Vue 的 computed 或 React 的 useMemo
	 */
	let isAuthenticated = $derived(!!user && !!token);

	// 檢查 token 是否過期
	function isTokenExpired(tokenString: string): boolean {
		try {
			const decoded = jwtDecode<JWTPayload>(tokenString);
			const currentTime = Date.now() / 1000;
			const isExpired = decoded.exp < currentTime;

			if (isExpired) {
				console.log('[Auth] Token expired at:', new Date(decoded.exp * 1000));
			}

			return isExpired;
		} catch (error) {
			console.error('[Auth] Failed to decode token:', error);
			return true; // 無法解析的 token 視為過期
		}
	}

	// 從 localStorage 載入 token
	if (browser) {
		const storedToken = localStorage.getItem('token');
		const storedUser = localStorage.getItem('user');

		if (storedToken) {
			// 檢查 token 是否過期
			if (isTokenExpired(storedToken)) {
				console.log('[Auth] Stored token is expired, clearing auth state');
				localStorage.removeItem('token');
				localStorage.removeItem('user');
			} else {
				token = storedToken;
				if (storedUser) {
					try {
						user = JSON.parse(storedUser);
					} catch (e) {
						console.error('Failed to parse stored user:', e);
					}
				}
			}
		}
	}

	return {
		// Getters
		get user() { return user; },
		get token() { return token; },
		get isAuthenticated() { return isAuthenticated; },
		get isLoading() { return isLoading; },

		// 取得有效的 token（自動檢查過期）
		get validToken(): string | null {
			if (!token) return null;

			if (isTokenExpired(token)) {
				console.log('[Auth] Token is expired, logging out');
				// 自動登出
				this.logout();
				return null;
			}

			return token;
		},

		// Methods
		async login(userData: User, authToken: string) {
			// 登入前先檢查 token 是否有效
			if (isTokenExpired(authToken)) {
				console.error('[Auth] Cannot login with expired token');
				return;
			}

			user = userData;
			token = authToken;
			if (browser) {
				localStorage.setItem('token', authToken);
				localStorage.setItem('user', JSON.stringify(userData));
			}
		},

		async logout() {
			user = null;
			token = null;
			if (browser) {
				localStorage.removeItem('token');
				localStorage.removeItem('user');
				await goto('/');
			}
		},

		setLoading(loading: boolean) {
			isLoading = loading;
		},

		updateUser(updates: Partial<User>) {
			if (user) {
				user = { ...user, ...updates };
				// 同步更新到 localStorage
				if (browser) {
					localStorage.setItem('user', JSON.stringify(user));
				}
			}
		},

		// 檢查 token 是否即將過期（1天內）
		isTokenExpiringSoon(): boolean {
			if (!token) return false;

			try {
				const decoded = jwtDecode<JWTPayload>(token);
				const currentTime = Date.now() / 1000;
				const timeUntilExpiry = decoded.exp - currentTime;

				// 如果在 1 天內過期（24 小時 = 86400 秒）
				return timeUntilExpiry > 0 && timeUntilExpiry < 86400;
			} catch {
				return false;
			}
		},

		// 從伺服器刷新用戶資訊
		async refreshUser(): Promise<boolean> {
			if (!token) return false;

			// 先檢查 token 是否已過期
			if (isTokenExpired(token)) {
				console.log('[Auth] Token expired, logging out');
				this.logout();
				return false;
			}

			isLoading = true;
			try {
				const getMeStore = new GetMeStore();
				const result = await getMeStore.fetch();

				if (result.data?.me) {
					const serverUser = result.data.me;
					user = {
						id: serverUser.id,
						email: serverUser.email,
						username: serverUser.username,
						fullName: serverUser.fullName ?? undefined,
						bio: serverUser.bio ?? undefined,
						avatarUrl: serverUser.avatarUrl ?? undefined,
						isActive: serverUser.isActive ?? undefined,
						isSuperuser: serverUser.isSuperuser ?? undefined,
						// DateTime scalar 會 unmarshal 成 Date，轉回字串以符合 localStorage 序列化格式
					createdAt: serverUser.createdAt?.toISOString(),
						followersCount: serverUser.followersCount ?? undefined,
						followingCount: serverUser.followingCount ?? undefined
					};
					if (browser) {
						localStorage.setItem('user', JSON.stringify(user));
					}
					console.log('[Auth] User refreshed successfully');
					return true;
				} else {
					// me query 返回 null - token 無效或用戶被停用
					console.log('[Auth] Server returned null for me query, logging out');
					this.logout();
					return false;
				}
			} catch (error) {
				console.error('[Auth] Failed to refresh user:', error);
				// 網路錯誤時保留本地狀態（允許離線使用）
				return false;
			} finally {
				isLoading = false;
			}
		}
	};
}

// Export a singleton instance
export const auth = createAuthStore();