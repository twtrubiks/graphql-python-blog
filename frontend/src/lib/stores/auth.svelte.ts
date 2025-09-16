// Svelte 5: Store 使用 .svelte.ts 副檔名
// 這樣可以在檔案中使用 runes

interface User {
	id: number;
	email: string;
	username: string;
	bio?: string;
	avatar?: string;
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
	if (typeof window !== 'undefined') {
		const storedToken = localStorage.getItem('auth_token');
		if (storedToken) {
			token = storedToken;
		}
	}

	return {
		// Getters
		get user() { return user; },
		get token() { return token; },
		get isAuthenticated() { return isAuthenticated; },
		get isLoading() { return isLoading; },

		// Methods
		login(userData: User, authToken: string) {
			user = userData;
			token = authToken;
			if (typeof window !== 'undefined') {
				localStorage.setItem('auth_token', authToken);
			}
		},

		logout() {
			user = null;
			token = null;
			if (typeof window !== 'undefined') {
				localStorage.removeItem('auth_token');
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