/**
 * 通用訂閱管理器 - Svelte 5 Runes + Houdini GraphQL
 *
 * 解決的問題：
 * 1. 防止 $effect/onMount 競爭條件導致的重複初始化
 * 2. 統一訂閱生命週期管理（初始化、啟動、清理）
 * 3. 減少重複程式碼
 *
 * 使用方式：
 * const manager = createSubscriptionManager({
 *   name: 'MySubscription',
 *   createStore: () => new MySubscriptionStore(),
 *   getListenParams: () => ({ userId: auth.user?.id }),
 *   onData: (data) => handleData(data),
 *   requiresAuth: true
 * });
 */

/**
 * 訂閱配置介面
 */
export interface SubscriptionConfig<TData> {
	/** 訂閱名稱（用於日誌） */
	name: string;
	/** 建立 Houdini Store 的工廠函數（使用 any 以適配各種 Houdini store 類型） */
	// eslint-disable-next-line @typescript-eslint/no-explicit-any
	createStore: () => any;
	/** 獲取 listen 參數，返回 null 表示不滿足啟動條件 */
	getListenParams: () => Record<string, unknown> | null;
	/** 資料處理回調 */
	onData: (data: TData) => void;
	/** 錯誤處理回調 */
	onError?: (error: unknown) => void;
	/** 清理回調（登出或元件卸載時） */
	onCleanup?: () => void;
	/** 是否需要認證 */
	requiresAuth: boolean;
}

/**
 * Houdini Subscription Store 介面
 * 使用泛型以適配不同的 Houdini store 類型
 */
interface HoudiniSubscriptionStore {
	subscribe: (callback: (value: { data?: unknown; error?: unknown }) => void) => () => void;
	listen: (params?: unknown, args?: unknown) => Promise<void>;
	unlisten: () => Promise<void>;
}

/**
 * 建立訂閱管理器
 *
 * @param config 訂閱配置
 * @returns 訂閱管理器物件
 */
export function createSubscriptionManager<TData>(config: SubscriptionConfig<TData>) {
	// eslint-disable-next-line @typescript-eslint/no-explicit-any
	let store: any = null;
	let unsubscribe: (() => void) | null = null;
	let isActive = $state(false);
	let isInitialized = $state(false);

	/**
	 * 初始化訂閱
	 * - 防重複：如果已初始化則跳過
	 * - 檢查參數：requiresAuth 時需要有效的 listen 參數
	 */
	function init() {
		if (isInitialized) {
			console.log(`[${config.name}] Already initialized, skipping`);
			return;
		}

		const params = config.getListenParams();
		if (config.requiresAuth && !params) {
			console.log(`[${config.name}] Missing auth params, skipping init`);
			return;
		}

		console.log(`[${config.name}] Initializing subscription`);
		isInitialized = true;
		store = config.createStore();

		// 設置資料監聽
		unsubscribe = store.subscribe((value) => {
			if (!value || !isActive) return;

			if (value.data) {
				config.onData(value.data as TData);
			}

			if (value.error && config.onError) {
				config.onError(value.error);
			}
		});

		// 啟動 WebSocket 連線
		start();
	}

	/**
	 * 啟動 WebSocket 訂閱
	 */
	async function start() {
		if (!store || isActive) return;

		const params = config.getListenParams();
		if (!params) {
			console.log(`[${config.name}] No listen params, cannot start`);
			return;
		}

		console.log(`[${config.name}] Starting subscription`);
		isActive = true;

		try {
			await store.listen(params);
			console.log(`[${config.name}] Subscription connected`);
		} catch (error) {
			console.error(`[${config.name}] Failed to connect:`, error);
			isActive = false;
		}
	}

	/**
	 * 清理訂閱資源
	 * - 取消 store 訂閱
	 * - 關閉 WebSocket 連線
	 * - 重置狀態
	 */
	async function cleanup() {
		console.log(`[${config.name}] Cleaning up subscription`);

		if (unsubscribe) {
			unsubscribe();
			unsubscribe = null;
		}

		if (store && isActive) {
			try {
				await store.unlisten();
			} catch (error) {
				console.error(`[${config.name}] Error during unlisten:`, error);
			}
		}

		isActive = false;
		isInitialized = false;
		store = null;

		config.onCleanup?.();
	}

	return {
		/** 是否已啟動 WebSocket 連線 */
		get isActive() {
			return isActive;
		},
		/** 是否已初始化 */
		get isInitialized() {
			return isInitialized;
		},
		/** 初始化訂閱 */
		init,
		/** 清理訂閱 */
		cleanup
	};
}
