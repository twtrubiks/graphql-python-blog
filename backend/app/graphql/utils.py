# 分頁參數上限：防止 limit 無上限造成單次查詢撈取過多資料（DoS）
MAX_PAGE_SIZE = 50


def clamp_pagination(page: int, limit: int) -> tuple[int, int]:
    """
    將分頁參數鉗制在安全範圍內

    - page 最小為 1（避免負數 offset）
    - limit 介於 1 到 MAX_PAGE_SIZE（避免除以零與過大查詢）
    """
    return max(page, 1), min(max(limit, 1), MAX_PAGE_SIZE)
