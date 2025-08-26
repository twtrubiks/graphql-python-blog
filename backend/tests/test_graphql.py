import pytest
import json

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