// Svelte 5: Store 使用 .svelte.ts 副檔名
// 這樣可以在檔案中使用 runes
import { browser } from '$app/environment';
import { goto } from '$app/navigation';
import { jwtDecode } from 'jwt-decode';

interface User {
	id: string;
	email: string;
	username: string;
	fullName?: string;
	bio?: string;
	avatarUrl?: string;
	isActive?: boolean;
	isSuperuser?: boolean;
}

interface AuthState {
	user: User | null;
	token: string | null;
	isAuthenticated: boolean;
	isLoading: boolean;
}

interface JWTPayload {
	exp: number;
	sub: string;
	// 其他 payload 欄位
}

function createAuthStore() {
	// Svelte 5: 使用 $state rune 創建響應式狀態
	let user = $state<User | null>(null);
	let token = $state<string | null>(null);
	let isLoading = $state(false);

	// Svelte 5: 使用 $derived rune 計算衍生狀態
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
		}
	};
}

// Export a singleton instance
export const auth = createAuthStore();