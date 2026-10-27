"""pytest plugin（僅變異測試使用）：降低 bcrypt cost 以加速測試，不改變任何行為語意。"""
import bcrypt

_orig_gensalt = bcrypt.gensalt


def _fast_gensalt(rounds: int = 4, prefix: bytes = b"2b") -> bytes:
    return _orig_gensalt(rounds=4, prefix=prefix)


bcrypt.gensalt = _fast_gensalt
