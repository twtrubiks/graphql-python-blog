from app.core import security


class AuthService:
    """
    認證服務的呼叫介面

    實作只有一份，放在 app.core.security；這裡只是轉接，
    讓 register / login 簽發的 token 與測試、WebSocket 驗證用的是同一套程式碼。
    """
    verify_password = staticmethod(security.verify_password)
    get_password_hash = staticmethod(security.get_password_hash)
    create_access_token = staticmethod(security.create_access_token)
    verify_token = staticmethod(security.decode_access_token)
