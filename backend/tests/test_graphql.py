import pytest

from app.core.config import settings

GRAPHQL_ENDPOINT = "/graphql"

@pytest.mark.asyncio
async def test_graphql_hello_query(client):
    """Test basic GraphQL hello query."""
    query = """
    query {
        hello(name: "Test")
    }
    """
    
    response = await client.post(
        GRAPHQL_ENDPOINT,
        json={"query": query}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert data["data"]["hello"] == "Hello Test!"

@pytest.mark.asyncio
async def test_graphql_hello_query_default_name(client):
    """沒有傳 name 時打招呼的對象是 World"""
    response = await client.post(GRAPHQL_ENDPOINT, json={"query": "{ hello }"})

    assert response.json()["data"]["hello"] == "Hello World!"

@pytest.mark.asyncio
async def test_graphql_introspection(client):
    """Test GraphQL introspection query."""
    query = """
    query {
        __schema {
            queryType {
                name
            }
        }
    }
    """
    
    response = await client.post(
        GRAPHQL_ENDPOINT,
        json={"query": query}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert data["data"]["__schema"]["queryType"]["name"] == "Query"

@pytest.mark.asyncio
async def test_graphql_error_handling(client):
    """Test GraphQL error handling."""
    query = """
    query {
        nonExistentField
    }
    """
    
    response = await client.post(
        GRAPHQL_ENDPOINT,
        json={"query": query}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "errors" in data
    assert len(data["errors"]) > 0

@pytest.mark.asyncio
async def test_graphql_variables(client):
    """Test GraphQL query with variables."""
    query = """
    query HelloQuery($name: String!) {
        hello(name: $name)
    }
    """
    
    variables = {"name": "GraphQL"}
    
    response = await client.post(
        GRAPHQL_ENDPOINT,
        json={"query": query, "variables": variables}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["data"]["hello"] == "Hello GraphQL!"

@pytest.mark.asyncio
async def test_version_query(client):
    response = await client.post(GRAPHQL_ENDPOINT, json={"query": "{ version }"})

    assert response.json() == {"data": {"version": settings.VERSION}}


@pytest.mark.asyncio
async def test_echo_mutation(client):
    response = await client.post(GRAPHQL_ENDPOINT, json={"query": 'mutation { echo(message: "hi") }'})

    assert response.json() == {"data": {"echo": "Echo: hi"}}
