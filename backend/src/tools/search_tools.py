"""
Search Tools for LangGraph 0.6.6
ChromaDB with Kure-v1 embedding and BGE-reranker-ko
"""
from typing import Dict, Any, List, Optional, Tuple
import json
import numpy as np
from datetime import datetime
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer, CrossEncoder
from langchain_core.tools import tool
from loguru import logger
import pandas as pd
from pathlib import Path
import hashlib

# Import database for internal search
from .database import MockDatabase

# Initialize models
class SearchModels:
    """Singleton for model management"""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """Initialize embedding and reranking models"""
        try:
            # Kure-v1 임베딩 모델 (한국어 특화)
            logger.info("Loading Kure-v1 embedding model...")
            self.embedder = SentenceTransformer('snunlp/KR-SBERT-V40K-klueNLI-augSTS')
            # Note: 실제로는 'kure-v1' 모델을 사용하지만, 여기서는 대체 모델 사용
            
            # BGE-reranker-ko 모델 (한국어 재정렬)
            logger.info("Loading BGE-reranker-ko model...")
            self.reranker = CrossEncoder('BAAI/bge-reranker-base')
            # Note: 실제로는 'bge-reranker-ko' 모델을 사용
            
            logger.info("Models loaded successfully")
        except Exception as e:
            logger.warning(f"Failed to load models, using mock: {e}")
            self.embedder = None
            self.reranker = None
    
    def embed(self, texts: List[str]) -> np.ndarray:
        """Generate embeddings"""
        if self.embedder:
            return self.embedder.encode(texts)
        else:
            # Mock embeddings for testing
            return np.random.rand(len(texts), 768)
    
    def rerank(self, query: str, documents: List[str], top_k: int = 5) -> List[Tuple[int, float]]:
        """Rerank documents"""
        if self.reranker:
            scores = self.reranker.predict([(query, doc) for doc in documents])
            ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)
            return ranked[:top_k]
        else:
            # Mock reranking for testing
            scores = np.random.rand(len(documents))
            ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)
            return ranked[:top_k]


# Initialize ChromaDB
class VectorDB:
    """ChromaDB manager with Kure-v1 embedding"""
    
    def __init__(self):
        """Initialize ChromaDB client and collections"""
        # Setup ChromaDB
        db_path = Path(__file__).parent.parent.parent / "data" / "chroma"
        db_path.mkdir(parents=True, exist_ok=True)
        
        self.client = chromadb.PersistentClient(
            path=str(db_path),
            settings=Settings(anonymized_telemetry=False)
        )
        
        self.models = SearchModels()
        
        # Create collections
        self.collections = {
            "products": self._get_or_create_collection("products"),
            "customers": self._get_or_create_collection("customers"),
            "documents": self._get_or_create_collection("documents"),
            "knowledge": self._get_or_create_collection("knowledge_base")
        }
        
        # Initialize with mock data
        self._seed_mock_data()
    
    def _get_or_create_collection(self, name: str):
        """Get or create a collection"""
        try:
            return self.client.get_collection(name)
        except:
            return self.client.create_collection(
                name=name,
                metadata={"hnsw:space": "cosine"}
            )
    
    def _seed_mock_data(self):
        """Seed collections with mock data"""
        # Check if already seeded
        if self.collections["products"].count() > 0:
            return
        
        logger.info("Seeding ChromaDB with mock data...")
        
        # Product documents
        product_docs = [
            {
                "id": "prod_vec_001",
                "text": "AI Sales Assistant Pro는 최첨단 인공지능 기술을 활용한 영업 자동화 솔루션입니다. 고객 분석, 리드 스코어링, 자동 제안서 작성 기능을 제공합니다.",
                "metadata": {"category": "Software", "price": 5000000, "rating": 4.8}
            },
            {
                "id": "prod_vec_002",
                "text": "Data Analytics Suite는 빅데이터 분석 플랫폼으로 실시간 대시보드, 예측 분석, 맞춤형 리포트 기능을 제공합니다. 한국어 자연어 처리 최적화.",
                "metadata": {"category": "Analytics", "price": 3000000, "rating": 4.6}
            },
            {
                "id": "prod_vec_003",
                "text": "CRM Platform은 고객 관계 관리를 위한 통합 솔루션입니다. 고객 이력 추적, 영업 파이프라인 관리, 마케팅 자동화 기능 포함.",
                "metadata": {"category": "CRM", "price": 2500000, "rating": 4.5}
            }
        ]
        
        # Add to products collection
        texts = [doc["text"] for doc in product_docs]
        embeddings = self.models.embed(texts)
        
        self.collections["products"].add(
            ids=[doc["id"] for doc in product_docs],
            embeddings=embeddings.tolist() if isinstance(embeddings, np.ndarray) else embeddings,
            documents=texts,
            metadatas=[doc["metadata"] for doc in product_docs]
        )
        
        # Customer documents
        customer_docs = [
            {
                "id": "cust_vec_001",
                "text": "삼성전자는 글로벌 기술 리더로 반도체, 디스플레이, 가전제품을 생산합니다. 디지털 트랜스포메이션과 AI 솔루션에 관심이 높습니다.",
                "metadata": {"industry": "Technology", "size": "대기업", "priority": "high"}
            },
            {
                "id": "cust_vec_002",
                "text": "LG화학은 배터리, 석유화학, 첨단소재 분야의 선도 기업입니다. 지속가능한 솔루션과 탄소중립 기술을 적극 도입하고 있습니다.",
                "metadata": {"industry": "Chemical", "size": "대기업", "priority": "high"}
            },
            {
                "id": "cust_vec_003",
                "text": "네이버는 한국 최대 포털 사이트 운영사로 AI, 클라우드, 커머스 플랫폼을 제공합니다. 혁신적인 기술 도입에 적극적입니다.",
                "metadata": {"industry": "Internet", "size": "대기업", "priority": "high"}
            }
        ]
        
        texts = [doc["text"] for doc in customer_docs]
        embeddings = self.models.embed(texts)
        
        self.collections["customers"].add(
            ids=[doc["id"] for doc in customer_docs],
            embeddings=embeddings.tolist() if isinstance(embeddings, np.ndarray) else embeddings,
            documents=texts,
            metadatas=[doc["metadata"] for doc in customer_docs]
        )
        
        # Knowledge base documents
        knowledge_docs = [
            {
                "id": "kb_001",
                "text": "영업 프로세스 최적화: 리드 생성 → 검증 → 육성 → 제안 → 협상 → 계약. 각 단계별 자동화 도구를 활용하여 효율성을 30% 향상시킬 수 있습니다.",
                "metadata": {"type": "process", "topic": "sales"}
            },
            {
                "id": "kb_002",
                "text": "AI 기반 고객 분석: 머신러닝을 활용한 고객 행동 예측, 이탈 방지, 교차 판매 기회 발굴. 정확도 85% 이상의 예측 모델 제공.",
                "metadata": {"type": "technology", "topic": "ai"}
            },
            {
                "id": "kb_003",
                "text": "한국 시장 영업 전략: 관계 중심 영업, 장기적 신뢰 구축, 현지화된 솔루션 제공이 핵심. 대기업은 POC를 선호하며 중소기업은 가격 민감도가 높음.",
                "metadata": {"type": "strategy", "topic": "korea"}
            }
        ]
        
        texts = [doc["text"] for doc in knowledge_docs]
        embeddings = self.models.embed(texts)
        
        self.collections["knowledge"].add(
            ids=[doc["id"] for doc in knowledge_docs],
            embeddings=embeddings.tolist() if isinstance(embeddings, np.ndarray) else embeddings,
            documents=texts,
            metadatas=[doc["metadata"] for doc in knowledge_docs]
        )
        
        logger.info(f"Seeded ChromaDB with {len(product_docs) + len(customer_docs) + len(knowledge_docs)} documents")
    
    def search(self, collection_name: str, query: str, top_k: int = 5) -> List[Dict]:
        """Search in a specific collection"""
        if collection_name not in self.collections:
            return []
        
        # Generate query embedding
        query_embedding = self.models.embed([query])[0]
        
        # Search
        results = self.collections[collection_name].query(
            query_embeddings=[query_embedding.tolist()],
            n_results=top_k
        )
        
        # Format results
        formatted_results = []
        if results["ids"] and results["ids"][0]:
            for i in range(len(results["ids"][0])):
                formatted_results.append({
                    "id": results["ids"][0][i],
                    "text": results["documents"][0][i] if results["documents"] else "",
                    "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                    "distance": results["distances"][0][i] if results["distances"] else 0
                })
        
        return formatted_results


# Initialize database and vector DB
db = MockDatabase()
vector_db = VectorDB()
models = SearchModels()


@tool
def search_internal_db(query: str, search_type: str = "all") -> str:
    """
    Search internal SQLite database (1st priority)
    
    Args:
        query: Search query
        search_type: Type of search (customers, products, sales, all)
    
    Returns:
        JSON string with search results
    """
    try:
        results = {}
        
        # Search customers
        if search_type in ["customers", "all"]:
            customers_df = db.get_customer_trends(months=3)
            if not customers_df.empty and query.lower() in customers_df.to_string().lower():
                # Filter relevant customers
                mask = customers_df.apply(
                    lambda row: query.lower() in str(row.to_dict()).lower(), 
                    axis=1
                )
                filtered = customers_df[mask].head(5)
                if not filtered.empty:
                    results["customers"] = filtered.to_dict("records")
        
        # Search products
        if search_type in ["products", "all"]:
            products_df = db.get_product_performance()
            if not products_df.empty and query.lower() in products_df.to_string().lower():
                mask = products_df.apply(
                    lambda row: query.lower() in str(row.to_dict()).lower(),
                    axis=1
                )
                filtered = products_df[mask].head(5)
                if not filtered.empty:
                    results["products"] = filtered.to_dict("records")
        
        # Search employees
        if search_type in ["employees", "all"]:
            employees_df = db.get_employee_performance()
            if not employees_df.empty and query.lower() in employees_df.to_string().lower():
                mask = employees_df.apply(
                    lambda row: query.lower() in str(row.to_dict()).lower(),
                    axis=1
                )
                filtered = employees_df[mask].head(5)
                if not filtered.empty:
                    results["employees"] = filtered.to_dict("records")
        
        logger.info(f"Internal DB search for '{query}' found {len(results)} categories")
        
        return json.dumps({
            "source": "internal_db",
            "query": query,
            "results": results,
            "count": sum(len(v) for v in results.values() if isinstance(v, list))
        }, ensure_ascii=False, default=str)
        
    except Exception as e:
        logger.error(f"Error in internal DB search: {e}")
        return json.dumps({"error": str(e), "source": "internal_db"}, ensure_ascii=False)


@tool
def search_vector_db(query: str, collections: List[str] = None) -> str:
    """
    Search ChromaDB vector database (2nd priority)
    
    Args:
        query: Search query
        collections: List of collections to search (default: all)
    
    Returns:
        JSON string with search results
    """
    try:
        if collections is None:
            collections = ["products", "customers", "knowledge"]
        
        all_results = {}
        
        for collection in collections:
            results = vector_db.search(collection, query, top_k=3)
            if results:
                all_results[collection] = results
        
        logger.info(f"Vector DB search for '{query}' found {sum(len(v) for v in all_results.values())} results")
        
        return json.dumps({
            "source": "vector_db",
            "query": query,
            "results": all_results,
            "count": sum(len(v) for v in all_results.values())
        }, ensure_ascii=False, default=str)
        
    except Exception as e:
        logger.error(f"Error in vector DB search: {e}")
        return json.dumps({"error": str(e), "source": "vector_db"}, ensure_ascii=False)


@tool
def search_external_api(query: str, api: str = "naver") -> str:
    """
    Search external APIs - Naver/Google (3rd priority)
    Mock implementation for testing
    
    Args:
        query: Search query
        api: API to use (naver, google)
    
    Returns:
        JSON string with search results
    """
    try:
        # Mock external API results
        mock_results = {
            "naver": [
                {
                    "title": f"네이버 검색: {query}",
                    "snippet": f"{query}에 대한 네이버 검색 결과입니다. 최신 한국 시장 정보와 트렌드를 제공합니다.",
                    "url": f"https://search.naver.com/search.naver?query={query}",
                    "source": "Naver"
                },
                {
                    "title": f"네이버 뉴스: {query} 관련",
                    "snippet": f"최근 {query} 관련 업계 동향과 뉴스를 확인하세요.",
                    "url": f"https://news.naver.com/search?query={query}",
                    "source": "Naver News"
                }
            ],
            "google": [
                {
                    "title": f"Google Search: {query}",
                    "snippet": f"Comprehensive global information about {query} from various sources.",
                    "url": f"https://www.google.com/search?q={query}",
                    "source": "Google"
                },
                {
                    "title": f"Industry Report: {query}",
                    "snippet": f"Latest industry analysis and market trends for {query}.",
                    "url": f"https://trends.google.com/search?q={query}",
                    "source": "Google Trends"
                }
            ]
        }
        
        results = mock_results.get(api, mock_results["naver"])
        
        logger.info(f"External API ({api}) search for '{query}' returned {len(results)} results")
        
        return json.dumps({
            "source": f"external_api_{api}",
            "query": query,
            "results": results,
            "count": len(results)
        }, ensure_ascii=False, default=str)
        
    except Exception as e:
        logger.error(f"Error in external API search: {e}")
        return json.dumps({"error": str(e), "source": "external_api"}, ensure_ascii=False)


@tool
def rerank_search_results(query: str, documents: List[str], top_k: int = 5) -> str:
    """
    Rerank search results using BGE-reranker-ko
    
    Args:
        query: Original search query
        documents: List of document texts to rerank
        top_k: Number of top results to return
    
    Returns:
        JSON string with reranked results
    """
    try:
        if not documents:
            return json.dumps({"error": "No documents to rerank"}, ensure_ascii=False)
        
        # Rerank using BGE-reranker-ko
        ranked_indices = models.rerank(query, documents, top_k=min(top_k, len(documents)))
        
        # Format reranked results
        reranked = []
        for idx, score in ranked_indices:
            reranked.append({
                "index": idx,
                "score": float(score),
                "text": documents[idx][:200] + "..." if len(documents[idx]) > 200 else documents[idx]
            })
        
        logger.info(f"Reranked {len(documents)} documents, returned top {len(reranked)}")
        
        return json.dumps({
            "source": "reranker",
            "query": query,
            "original_count": len(documents),
            "reranked_count": len(reranked),
            "results": reranked
        }, ensure_ascii=False, default=str)
        
    except Exception as e:
        logger.error(f"Error in reranking: {e}")
        return json.dumps({"error": str(e), "source": "reranker"}, ensure_ascii=False)


@tool
def merge_search_results(results_list: List[Dict], query: str) -> str:
    """
    Merge and summarize search results from multiple sources
    
    Args:
        results_list: List of search results from different sources
        query: Original search query
    
    Returns:
        JSON string with merged and summarized results
    """
    try:
        merged = {
            "query": query,
            "sources": [],
            "total_results": 0,
            "merged_results": [],
            "summary": {}
        }
        
        # Process each source
        for result in results_list:
            if isinstance(result, str):
                result = json.loads(result)
            
            source = result.get("source", "unknown")
            merged["sources"].append(source)
            
            # Extract and merge results
            if "results" in result:
                source_results = result["results"]
                
                # Handle different result formats
                if isinstance(source_results, dict):
                    for category, items in source_results.items():
                        if isinstance(items, list):
                            for item in items:
                                merged_item = {
                                    "source": source,
                                    "category": category,
                                    "data": item
                                }
                                merged["merged_results"].append(merged_item)
                elif isinstance(source_results, list):
                    for item in source_results:
                        merged_item = {
                            "source": source,
                            "data": item
                        }
                        merged["merged_results"].append(merged_item)
        
        # Calculate statistics
        merged["total_results"] = len(merged["merged_results"])
        
        # Group by source
        source_counts = {}
        for item in merged["merged_results"]:
            source = item["source"]
            source_counts[source] = source_counts.get(source, 0) + 1
        
        merged["summary"] = {
            "by_source": source_counts,
            "top_source": max(source_counts, key=source_counts.get) if source_counts else None,
            "search_quality": "high" if merged["total_results"] > 10 else "medium" if merged["total_results"] > 5 else "low"
        }
        
        logger.info(f"Merged {merged['total_results']} results from {len(merged['sources'])} sources")
        
        return json.dumps(merged, ensure_ascii=False, default=str)
        
    except Exception as e:
        logger.error(f"Error merging results: {e}")
        return json.dumps({"error": str(e)}, ensure_ascii=False)


@tool
def semantic_search(query: str, priority_order: List[str] = None) -> str:
    """
    Perform comprehensive semantic search following priority order
    
    Args:
        query: Search query
        priority_order: Custom priority order (default: internal_db, vector_db, external_api)
    
    Returns:
        JSON string with comprehensive search results
    """
    try:
        if priority_order is None:
            priority_order = ["internal_db", "vector_db", "external_api"]
        
        all_results = []
        all_documents = []
        
        # 1. Internal DB search (1st priority)
        if "internal_db" in priority_order:
            internal_results = search_internal_db.invoke({"query": query})
            all_results.append(json.loads(internal_results))
            
            # Extract text for reranking
            internal_data = json.loads(internal_results)
            if "results" in internal_data:
                for category, items in internal_data["results"].items():
                    if isinstance(items, list):
                        for item in items:
                            text = json.dumps(item, ensure_ascii=False)
                            all_documents.append(text)
        
        # 2. Vector DB search (2nd priority)
        if "vector_db" in priority_order:
            vector_results = search_vector_db.invoke({"query": query})
            all_results.append(json.loads(vector_results))
            
            # Extract text for reranking
            vector_data = json.loads(vector_results)
            if "results" in vector_data:
                for collection, items in vector_data["results"].items():
                    if isinstance(items, list):
                        for item in items:
                            if "text" in item:
                                all_documents.append(item["text"])
        
        # 3. External API search (3rd priority)
        if "external_api" in priority_order and len(all_documents) < 5:
            # Only use external API if we don't have enough internal results
            external_results = search_external_api.invoke({"query": query})
            all_results.append(json.loads(external_results))
            
            # Extract text for reranking
            external_data = json.loads(external_results)
            if "results" in external_data:
                for item in external_data["results"]:
                    if "snippet" in item:
                        all_documents.append(item["snippet"])
        
        # 4. Rerank all documents
        reranked = None
        if all_documents:
            reranked_results = rerank_search_results.invoke({
                "query": query,
                "documents": all_documents,
                "top_k": 10
            })
            reranked = json.loads(reranked_results)
        
        # 5. Merge all results
        merged = merge_search_results.invoke({
            "results_list": all_results,
            "query": query
        })
        merged_data = json.loads(merged)
        
        # Add reranked results
        if reranked:
            merged_data["reranked_top_results"] = reranked.get("results", [])
        
        # Final summary
        merged_data["search_summary"] = {
            "query": query,
            "total_sources_searched": len(all_results),
            "total_documents_found": len(all_documents),
            "search_quality": merged_data["summary"]["search_quality"],
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"Semantic search completed: {merged_data['search_summary']}")
        
        return json.dumps(merged_data, ensure_ascii=False, default=str)
        
    except Exception as e:
        logger.error(f"Error in semantic search: {e}")
        return json.dumps({"error": str(e)}, ensure_ascii=False)