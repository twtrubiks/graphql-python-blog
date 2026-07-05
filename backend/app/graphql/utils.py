from typing import Any, Type


def convert_model_to_graphql(model: Any, graphql_type: Type) -> Any:
    """
    Convert SQLAlchemy model to GraphQL type
    """
    if hasattr(graphql_type, 'from_orm'):
        return graphql_type.from_orm(model)
    
    # Manual conversion for types without from_orm
    kwargs = {}
    
    # Get all annotations from the GraphQL type to know what fields to copy
    if hasattr(graphql_type, '__annotations__'):
        for field_name, field_type in graphql_type.__annotations__.items():
            # Skip strawberry fields (they're computed)
            if hasattr(field_type, '__class__') and 'StrawberryAnnotation' in str(field_type.__class__):
                continue
            if hasattr(model, field_name):
                value = getattr(model, field_name)
                # Skip methods (like is_deleted property)
                if callable(value):
                    continue
                # Convert id to string for GraphQL ID type
                if field_name == 'id':
                    kwargs[field_name] = str(value)
                # Handle relationships
                elif field_name in ['author', 'post']:
                    # These will be resolved separately
                    continue
                else:
                    kwargs[field_name] = value
    
    return graphql_type(**kwargs)

# 分頁參數上限：防止 limit 無上限造成單次查詢撈取過多資料（DoS）
MAX_PAGE_SIZE = 50


def clamp_pagination(page: int, limit: int) -> tuple[int, int]:
    """
    將分頁參數鉗制在安全範圍內

    - page 最小為 1（避免負數 offset）
    - limit 介於 1 到 MAX_PAGE_SIZE（避免除以零與過大查詢）
    """
    return max(page, 1), min(max(limit, 1), MAX_PAGE_SIZE)
