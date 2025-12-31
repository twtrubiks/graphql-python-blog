import { redirect } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ params }) => {
	// 重導向到 /users/{username}，因為用戶個人頁面在那裡
	redirect(301, `/users/${params.username}`);
};
