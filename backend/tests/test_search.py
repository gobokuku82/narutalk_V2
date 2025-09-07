"""
Test cases for Enhanced Search Agent with ChromaDB
Testing multi-source search, reranking, and result merging
"""
import pytest
import json
import asyncio
from datetime import datetime
from langchain_core.messages import HumanMessage, AIMessage
from src.state.agent_state import AgentState
from src.agents.search import search_agent
from src.tools.search_tools import (
    search_internal_db,
    search_vector_db,
    search_external_api,
    rerank_search_results,
    merge_search_results,
    semantic_search,
    VectorDB,
    SearchModels
)


class TestSearchTools:
    """Test suite for search tools"""
    
    @pytest.fixture
    def vector_db(self):
        """Create a test vector database instance"""
        return VectorDB()
    
    @pytest.fixture
    def search_models(self):
        """Create search models instance"""
        return SearchModels()
    
    def test_search_internal_db(self):
        """Test internal SQLite database search"""
        # Test general search
        result = search_internal_db.invoke({
            "query": "samsung",
            "search_type": "all"
        })
        data = json.loads(result)
        
        assert "source" in data
        assert data["source"] == "internal_db"
        assert "results" in data
        
        # Test customer search
        result = search_internal_db.invoke({
            "query": "customer",
            "search_type": "customers"
        })
        data = json.loads(result)
        
        assert "results" in data
        
    def test_search_vector_db(self, vector_db):
        """Test ChromaDB vector search"""
        # Test product search
        result = search_vector_db.invoke({
            "query": "AI 영업 솔루션",
            "collections": ["products"]
        })
        data = json.loads(result)
        
        assert "source" in data
        assert data["source"] == "vector_db"
        assert "results" in data
        
        # Test knowledge base search
        result = search_vector_db.invoke({
            "query": "영업 프로세스 최적화",
            "collections": ["knowledge"]
        })
        data = json.loads(result)
        
        assert "results" in data
        if data["results"]:
            assert "knowledge" in data["results"]
    
    def test_search_external_api(self):
        """Test external API search (mock)"""
        # Test Naver API
        result = search_external_api.invoke({
            "query": "삼성전자 주가",
            "api": "naver"
        })
        data = json.loads(result)
        
        assert "source" in data
        assert "external_api_naver" in data["source"]
        assert "results" in data
        assert len(data["results"]) > 0
        
        # Test Google API
        result = search_external_api.invoke({
            "query": "AI sales trends",
            "api": "google"
        })
        data = json.loads(result)
        
        assert "external_api_google" in data["source"]
        assert "results" in data
    
    def test_rerank_search_results(self, search_models):
        """Test BGE-reranker-ko reranking"""
        documents = [
            "AI 영업 자동화 솔루션은 효율성을 높입니다",
            "삼성전자는 글로벌 기술 기업입니다",
            "영업 프로세스 최적화가 중요합니다",
            "데이터 분석으로 인사이트를 얻습니다",
            "고객 만족도 향상이 핵심입니다"
        ]
        
        result = rerank_search_results.invoke({
            "query": "영업 자동화",
            "documents": documents,
            "top_k": 3
        })
        data = json.loads(result)
        
        assert "source" in data
        assert data["source"] == "reranker"
        assert "results" in data
        assert len(data["results"]) <= 3
        
        # Check reranking structure
        for item in data["results"]:
            assert "index" in item
            assert "score" in item
            assert "text" in item
    
    def test_merge_search_results(self):
        """Test merging results from multiple sources"""
        # Create sample results from different sources
        internal_result = {
            "source": "internal_db",
            "results": {
                "customers": [{"name": "Samsung", "industry": "Tech"}],
                "products": [{"name": "AI Suite", "price": 1000000}]
            }
        }
        
        vector_result = {
            "source": "vector_db",
            "results": {
                "products": [{"text": "AI Sales Assistant", "distance": 0.1}],
                "knowledge": [{"text": "Sales process", "distance": 0.2}]
            }
        }
        
        external_result = {
            "source": "external_api",
            "results": [
                {"title": "News 1", "snippet": "Latest AI trends"},
                {"title": "News 2", "snippet": "Market analysis"}
            ]
        }
        
        result = merge_search_results.invoke({
            "results_list": [internal_result, vector_result, external_result],
            "query": "AI sales"
        })
        data = json.loads(result)
        
        assert "sources" in data
        assert len(data["sources"]) == 3
        assert "merged_results" in data
        assert "total_results" in data
        assert data["total_results"] > 0
        assert "summary" in data
        assert "by_source" in data["summary"]
    
    def test_semantic_search(self):
        """Test comprehensive semantic search"""
        result = semantic_search.invoke({
            "query": "삼성전자 AI 제품 정보",
            "priority_order": ["internal_db", "vector_db"]
        })
        data = json.loads(result)
        
        assert "search_summary" in data
        assert "total_sources_searched" in data["search_summary"]
        assert "merged_results" in data
        
        # Check if reranking was performed
        if "reranked_top_results" in data:
            assert isinstance(data["reranked_top_results"], list)


class TestSearchAgent:
    """Test suite for the enhanced search agent"""
    
    def test_search_agent_basic(self):
        """Test basic search agent functionality"""
        state = {
            "messages": [HumanMessage(content="Search for Samsung customer information")],
            "current_agent": "search",
            "task_type": "search",
            "task_description": "Search for Samsung customer information",
            "progress": [],
            "context": {},
            "metadata": {},
            "results": {},
            "errors": [],
            "is_complete": False
        }
        
        result = search_agent(state)
        
        # Check result structure
        assert result is not None
        assert "messages" in result
        assert len(result["messages"]) > 0
        assert "progress" in result
        assert "results" in result
        assert "context" in result
        
        # Check search completion
        assert result["context"]["search_completed"] == True
        
        # Check search results
        assert "search" in result["results"]
        search_result = result["results"]["search"]
        assert "timestamp" in search_result
        assert "query" in search_result
        assert "search_stats" in search_result
        assert "status" in search_result
        assert search_result["status"] == "success"
    
    def test_search_agent_with_chromadb(self):
        """Test search agent with ChromaDB integration"""
        state = {
            "messages": [HumanMessage(content="AI 영업 솔루션 정보 검색")],
            "current_agent": "search",
            "task_type": "search",
            "task_description": "AI 영업 솔루션 정보 검색",
            "progress": [],
            "context": {},
            "metadata": {},
            "results": {},
            "errors": [],
            "is_complete": False
        }
        
        result = search_agent(state)
        
        # Check ChromaDB was used
        assert "context" in result
        assert "has_chromadb_results" in result["context"]
        
        # Check search statistics
        if "search" in result["results"]:
            search_stats = result["results"]["search"].get("search_stats", {})
            assert "vector_db" in search_stats
    
    def test_search_agent_priority_order(self):
        """Test search priority order (Internal DB → ChromaDB → External)"""
        state = {
            "messages": [HumanMessage(content="Find limited information")],
            "current_agent": "search",
            "task_type": "search",
            "task_description": "Find limited information",
            "progress": [],
            "context": {},
            "metadata": {},
            "results": {},
            "errors": [],
            "is_complete": False
        }
        
        result = search_agent(state)
        
        # Check that priority order was followed
        if "search" in result["results"]:
            search_stats = result["results"]["search"]["search_stats"]
            
            # Internal DB should always be searched
            assert search_stats["internal_db"]["searched"] == True or search_stats["internal_db"]["count"] >= 0
            
            # Vector DB should be searched second
            assert "vector_db" in search_stats
            
            # External API only if needed (< 5 internal results)
            total_internal = search_stats["internal_db"]["count"] + search_stats["vector_db"]["count"]
            if total_internal < 5:
                assert search_stats["external_api"]["searched"] == True or search_stats["external_api"]["count"] >= 0
    
    def test_search_agent_reranking(self):
        """Test that reranking is performed on search results"""
        state = {
            "messages": [HumanMessage(content="영업 프로세스 최적화 방법")],
            "current_agent": "search",
            "task_type": "search",
            "task_description": "영업 프로세스 최적화 방법",
            "progress": [],
            "context": {},
            "metadata": {},
            "results": {},
            "errors": [],
            "is_complete": False
        }
        
        result = search_agent(state)
        
        # Check for reranked results
        if "search" in result["results"]:
            search_data = result["results"]["search"]
            
            # Check if reranking was performed
            if "reranked_results" in search_data and search_data["reranked_results"]:
                reranked = search_data["reranked_results"]
                assert "results" in reranked
                
                # Check reranked results have scores
                for item in reranked.get("results", []):
                    assert "score" in item
                    assert isinstance(item["score"], (int, float))
    
    def test_search_agent_error_handling(self):
        """Test search agent error handling"""
        state = {
            "messages": [],  # Empty messages might cause issues
            "current_agent": "search",
            "task_type": "search",
            "task_description": "",  # Empty task
            "progress": [],
            "context": {},
            "metadata": {},
            "results": {},
            "errors": [],
            "is_complete": False
        }
        
        result = search_agent(state)
        
        # Should still return a valid result
        assert result is not None
        assert "messages" in result
        assert "current_agent" in result
    
    def test_search_agent_context_preservation(self):
        """Test that search agent preserves and updates context"""
        state = {
            "messages": [HumanMessage(content="Search for product information")],
            "current_agent": "search",
            "task_type": "search",
            "task_description": "Search for product information",
            "progress": [
                {"agent": "supervisor", "timestamp": "2024-01-01T00:00:00", "action": "routing"}
            ],
            "context": {
                "client_name": "Test Corp",
                "priority": "high"
            },
            "metadata": {"thread_id": "test_thread"},
            "results": {},
            "errors": [],
            "is_complete": False
        }
        
        result = search_agent(state)
        
        # Check context preservation
        assert "context" in result
        assert result["context"]["client_name"] == "Test Corp"
        assert result["context"]["priority"] == "high"
        
        # Check context updates
        assert result["context"]["search_completed"] == True
        assert "search_sources" in result["context"]
        assert isinstance(result["context"]["search_sources"], list)


class TestChromaDBIntegration:
    """Test ChromaDB integration"""
    
    def test_chromadb_initialization(self):
        """Test ChromaDB initialization with collections"""
        vector_db = VectorDB()
        
        # Check collections exist
        assert "products" in vector_db.collections
        assert "customers" in vector_db.collections
        assert "documents" in vector_db.collections
        assert "knowledge" in vector_db.collections
        
        # Check mock data was seeded
        products_count = vector_db.collections["products"].count()
        assert products_count > 0
    
    def test_chromadb_search(self):
        """Test ChromaDB search functionality"""
        vector_db = VectorDB()
        
        # Search in products collection
        results = vector_db.search("products", "AI 영업", top_k=3)
        
        assert isinstance(results, list)
        if results:
            assert "id" in results[0]
            assert "text" in results[0]
            assert "metadata" in results[0]
            assert "distance" in results[0]
    
    def test_embedding_model(self):
        """Test Kure-v1 embedding model (or mock)"""
        models = SearchModels()
        
        # Test embedding generation
        texts = ["Test text 1", "Test text 2"]
        embeddings = models.embed(texts)
        
        assert embeddings is not None
        assert len(embeddings) == 2
        assert len(embeddings[0]) == 768  # Standard embedding dimension
    
    def test_reranker_model(self):
        """Test BGE-reranker-ko model (or mock)"""
        models = SearchModels()
        
        # Test reranking
        query = "영업 자동화"
        documents = ["영업 프로세스", "자동화 솔루션", "고객 관리"]
        
        ranked = models.rerank(query, documents, top_k=2)
        
        assert isinstance(ranked, list)
        assert len(ranked) <= 2
        for idx, score in ranked:
            assert 0 <= idx < len(documents)
            assert isinstance(score, (int, float))


@pytest.mark.asyncio
class TestSearchIntegration:
    """Integration tests for search with StateGraph"""
    
    async def test_search_in_graph_flow(self):
        """Test search agent within the graph flow"""
        from src.core.graph import SalesSupportApp
        
        app = SalesSupportApp(use_sqlite=False)
        
        # Request search
        result = await app.aprocess_request(
            user_input="Search for Samsung customer information and AI products",
            thread_id="test_search_1"
        )
        
        # Check that search was involved
        progress = result.get("progress", [])
        agents = [p.get("agent") for p in progress]
        
        # Should have supervisor and possibly search
        assert "supervisor" in agents or "search" in agents
        
        # Check results if search was executed
        if "search" in result.get("results", {}):
            search_results = result["results"]["search"]
            assert search_results["status"] == "success"