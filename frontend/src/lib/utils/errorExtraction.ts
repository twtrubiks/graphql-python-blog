/**
 * 從 Houdini mutation 錯誤中提取錯誤訊息
 * Houdini 不一定拋出 Error 物件，可能是 GraphQL errors 陣列或帶 message 的物件
 */
export function extractHoudiniError(err: unknown): string {
	if (err instanceof Error) {
		return err.message;
	}
	if (Array.isArray(err)) {
		return err[0]?.message || '';
	}
	if (typeof err === 'object' && err !== null && 'message' in err) {
		return (err as { message: string }).message;
	}
	return '';
}
