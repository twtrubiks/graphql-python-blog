import { load_GetPosts } from '$houdini';
import type { PageLoad } from './$types';

export const load: PageLoad = async (event) => {
	// 載入文章列表
	const { data, errors } = await load_GetPosts({
		event,
		variables: {
			page: 1,
			limit: 3
		}
	});

	return {
		posts: data?.posts
	};
};