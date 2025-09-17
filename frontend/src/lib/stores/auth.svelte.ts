// Svelte 5: Store 使用 .svelte.ts 副檔名
// 這樣可以在檔案中使用 runes
import { browser } from '$app/environment';
import { goto } from '$app/navigation';

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

function createAuthStore() {
	// Svelte 5: 使用 $state rune 創建響應式狀態
	let user = $state<User | null>(null);
	let token = $state<string | null>(null);
	let isLoading = $state(false);

	// Svelte 5: 使用 $derived rune 計算衍生狀態
	let isAuthenticated = $derived(!!user && !!token);

	// 從 localStorage 載入 token
	if (browser) {
		const storedToken = localStorage.getItem('token');
		const storedUser = localStorage.getItem('user');
		if (storedToken) {
			token = storedToken;
		}
		if (storedUser) {
			try {
				user = JSON.parse(storedUser);
			} catch (e) {
				console.error('Failed to parse stored user:', e);
			}
		}
	}

	return {
		// Getters
		get user() { return user; },
		get token() { return token; },
		get isAuthenticated() { return isAuthenticated; },
		get isLoading() { return isLoading; },

		// Methods
		async login(userData: User, authToken: string) {
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
		}
	};
}

// Export a singleton instance
export const auth = createAuthStore();