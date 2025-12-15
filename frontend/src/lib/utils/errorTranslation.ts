/**
 * 錯誤訊息翻譯工具
 * 將後端返回的英文錯誤訊息轉換為中文
 */

const errorMap: Record<string, string> = {
	// 登入相關
	'Invalid credentials': '電子郵件或密碼錯誤',
	'Invalid email or password': '電子郵件或密碼錯誤',
	'User not found': '找不到此使用者',
	'Invalid password': '密碼錯誤',
	'Account is disabled': '帳號已被停用',
	'User is not active': '帳號尚未啟用',
	// 註冊相關
	'Password must contain at least one uppercase letter': '密碼必須包含至少一個大寫字母',
	'Password must contain at least one lowercase letter': '密碼必須包含至少一個小寫字母',
	'Password must contain at least one digit': '密碼必須包含至少一個數字',
	'Password must be at least 8 characters': '密碼至少需要 8 個字元',
	'Email already registered': '此電子郵件已被註冊',
	'Username already taken': '此使用者名稱已被使用',
	'Invalid email format': '電子郵件格式不正確',
	'Username must be at least 3 characters': '使用者名稱至少需要 3 個字元'
};

/**
 * 將英文錯誤訊息轉換為中文
 * @param message - 英文錯誤訊息
 * @returns 對應的中文訊息，若無對應則返回原始訊息
 */
export function translateError(message: string): string {
	for (const [key, value] of Object.entries(errorMap)) {
		if (message.toLowerCase().includes(key.toLowerCase())) {
			return value;
		}
	}
	return message;
}
