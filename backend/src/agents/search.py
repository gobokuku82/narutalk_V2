"""
Enhanced Search Agent for LangGraph 0.6.6
ChromaDB with Kure-v1 embedding and BGE-reranker-ko
"""
from typing import Dict, Any, List
from datetime import datetime
import json
from langchain_core.messages import AIMessage, SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import ToolNode
from loguru import logger

# Import our enhanced search tools
from ..tools.search_tools import (
    search_internal_db,
    search_vector_db,
    search_external_api,
    rerank_search_results,
    merge_search_results,
    semantic_search
)
from ..state.enhanced_state import EnhancedAgentState as AgentState


def search_agent(state: AgentState) -> dict:
    """
    Enhanced Search Agent with ChromaDB and priority-based search
    Following rules.md: Node functions MUST return dict
    Uses StateGraph pattern with tool integration
    """
    # Initialize LLM with tools binding
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    
    # Bind search tools to LLM
    tools = [
        search_internal_db,
        search_vector_db,
        search_external_api,
        rerank_search_results,
        merge_search_results,
        semantic_search
    ]
    llm_with_tools = llm.bind_tools(tools)
    
    # Get task description and context
    task_description = state.get("task_description", "")
    context = state.get("context", {})
    messages = state.get("messages", [])
    
    # Get results from previous agents (especially analytics)
    previous_results = state.get("results", {})
    analytics_results = previous_results.get("analytics", {})
    
    # Extract analytics insights if available
    analytics_insights = analytics_results.get("key_insights", {})
    has_analytics_data = bool(analytics_insights)
    
    # Progress tracking
    progress_update = {
        "agent": "search",
        "timestamp": datetime.now().isoformat(),
        "action": "multi_source_search_with_chromadb"
    }
    
    logger.info(f"Search agent processing: {task_description[:100]}...")
    
    try:
        # Determine search type from task description and analytics insights
        search_type = "all"
        
        # Use analytics insights to refine search focus
        if has_analytics_data:
            performance_metrics = analytics_insights.get("performance_metrics", {})
            trends = analytics_insights.get("trends", {})
            recommendations = analytics_insights.get("recommendations", [])
            
            # Adjust search based on analytics findings
            if performance_metrics.get("health_score", 100) < 70:
                # Low health score - focus on improvement areas
                logger.info("Low health score detected, adjusting search focus...")
                if "customer" not in task_description.lower():
                    search_type = "customers"  # Focus on customer data
            elif trends.get("direction") == "declining":
                # Declining trends - search for market opportunities
                logger.info("Declining trends detected, searching for opportunities...")
                search_type = "products"  # Focus on product offerings
        
        # Override with explicit task requirements
        if "customer" in task_description.lower() or "고객" in task_description.lower():
            search_type = "customers"
        elif "product" in task_description.lower() or "제품" in task_description.lower():
            search_type = "products"
        elif "employee" in task_description.lower() or "직원" in task_description.lower():
            search_type = "employees"
        
        # Priority-based search execution
        all_results = []
        all_documents = []
        search_stats = {
            "internal_db": {"searched": False, "count": 0},
            "vector_db": {"searched": False, "count": 0},
            "external_api": {"searched": False, "count": 0}
        }
        
        # 1st Priority: Internal SQLite Database
        logger.info("Searching internal database...")
        internal_result = search_internal_db.invoke({
            "query": task_description,
            "search_type": search_type
        })
        internal_data = json.loads(internal_result)
        all_results.append(internal_data)
        
        if "results" in internal_data and internal_data["results"]:
            search_stats["internal_db"]["searched"] = True
            search_stats["internal_db"]["count"] = internal_data.get("count", 0)
            
            # Extract text for reranking
            for category, items in internal_data["results"].items():
                if isinstance(items, list):
                    for item in items:
                        text = json.dumps(item, ensure_ascii=False)
                        all_documents.append(text)
        
        # 2nd Priority: ChromaDB Vector Search
        logger.info("Searching ChromaDB vector database...")
        collections_to_search = None
        if search_type == "customers":
            collections_to_search = ["customers"]
        elif search_type == "products":
            collections_to_search = ["products"]
        else:
            collections_to_search = ["products", "customers", "knowledge"]
        
        vector_result = search_vector_db.invoke({
            "query": task_description,
            "collections": collections_to_search
        })
        vector_data = json.loads(vector_result)
        all_results.append(vector_data)
        
        if "results" in vector_data and vector_data["results"]:
            search_stats["vector_db"]["searched"] = True
            search_stats["vector_db"]["count"] = vector_data.get("count", 0)
            
            # Extract text for reranking
            for collection, items in vector_data["results"].items():
                if isinstance(items, list):
                    for item in items:
                        if "text" in item:
                            all_documents.append(item["text"])
        
        # 3rd Priority: External API (only if needed)
        total_internal_results = search_stats["internal_db"]["count"] + search_stats["vector_db"]["count"]
        if total_internal_results < 5:
            logger.info("Insufficient internal results, searching external APIs...")
            external_result = search_external_api.invoke({
                "query": task_description,
                "api": "naver"  # Korean market focus
            })
            external_data = json.loads(external_result)
            all_results.append(external_data)
            
            if "results" in external_data:
                search_stats["external_api"]["searched"] = True
                search_stats["external_api"]["count"] = external_data.get("count", 0)
                
                # Extract text for reranking
                for item in external_data["results"]:
                    if "snippet" in item:
                        all_documents.append(item["snippet"])
        
        # Rerank all documents using BGE-reranker-ko
        reranked_results = None
        if all_documents:
            logger.info(f"Reranking {len(all_documents)} documents...")
            reranked_result = rerank_search_results.invoke({
                "query": task_description,
                "documents": all_documents,
                "top_k": min(10, len(all_documents))
            })
            reranked_results = json.loads(reranked_result)
        
        # Merge all search results
        logger.info("Merging search results...")
        merged_result = merge_search_results.invoke({
            "results_list": all_results,
            "query": task_description
        })
        merged_data = json.loads(merged_result)
        
        # Add reranked results to merged data
        if reranked_results and "results" in reranked_results:
            merged_data["reranked_top_results"] = reranked_results["results"]
        
        # Generate LLM insights from search results
        search_summary = json.dumps(merged_data, ensure_ascii=False, indent=2)
        
        # Include analytics context in search analysis
        analytics_context = ""
        if has_analytics_data:
            analytics_context = f"""
        
        Additionally, consider these analytics insights:
        - Performance Health Score: {analytics_insights.get('performance_metrics', {}).get('health_score', 'N/A')}
        - Trend Direction: {analytics_insights.get('trends', {}).get('direction', 'N/A')}
        - Key Recommendations: {', '.join(analytics_insights.get('recommendations', []))}
        """
            logger.info("Incorporating analytics insights into search analysis")
        
        insight_prompt = f"""
        Based on the following multi-source search results (SQLite, ChromaDB, External APIs):
        
        {search_summary[:4000]}  # Limit to avoid token overflow
        {analytics_context}
        
        Search Query: {task_description}
        
        Please provide:
        1. Key Findings (3-5 most relevant points)
        2. Data Sources Summary (which sources provided best results)
        3. Actionable Insights (2-3 recommendations)
        4. Information Gaps (if any)
        
        Focus on accuracy and relevance to the search query.
        If analytics data is available, correlate search findings with performance metrics.
        """
        
        # Get LLM insights
        llm_response = llm.invoke([
            SystemMessage(content="You are a search analyst specializing in multi-source information retrieval."),
            HumanMessage(content=insight_prompt)
        ])
        
        # Format final search report
        search_content = f"""
🔍 **Enhanced Search Results**
*Powered by ChromaDB with Kure-v1 Embedding & BGE-reranker-ko*

{llm_response.content}

---

📊 **Search Statistics**
• Internal DB: {search_stats['internal_db']['count']} results
• Vector DB (ChromaDB): {search_stats['vector_db']['count']} results
• External API: {search_stats['external_api']['count']} results
• Total Documents: {len(all_documents)}
• Reranked Top Results: {len(reranked_results.get('results', [])) if reranked_results else 0}
"""
        
        # Add top reranked results if available
        if reranked_results and "results" in reranked_results:
            search_content += "\n\n🎯 **Top Relevant Results (Reranked)**\n"
            for i, result in enumerate(reranked_results["results"][:3], 1):
                search_content += f"\n{i}. Score: {result['score']:.3f}\n   {result['text'][:150]}...\n"
        
        # Update progress
        progress_update["status"] = "completed"
        progress_update["summary"] = f"Searched {len(all_results)} sources, found {len(all_documents)} documents"
        progress_update["search_stats"] = search_stats
        
        # Extract key entities for other agents
        companies_found = []
        products_found = []
        market_insights = ""
        
        if merged_data and "results" in merged_data:
            for source, items in merged_data["results"].items():
                if isinstance(items, dict):
                    if "customers" in items:
                        companies_found.extend([c.get("name", "") for c in items["customers"] if "name" in c])
                    if "products" in items:
                        products_found.extend([p.get("name", "") for p in items["products"] if "name" in p])
        
        # Store detailed results in state with structured data
        results_update = state.get("results", {})
        results_update["search"] = {
            "timestamp": datetime.now().isoformat(),
            "query": task_description,
            "search_stats": search_stats,
            "merged_results": merged_data,
            "reranked_results": reranked_results,
            "llm_insights": llm_response.content,
            "raw_data": {  # Structured data for other agents
                "companies_found": list(set(companies_found[:10])),  # Deduplicated top 10
                "products_found": list(set(products_found[:10])),
                "market_insights": llm_response.content[:500],  # Summary for other agents
                "search_focus": search_type,
                "incorporated_analytics": has_analytics_data
            },
            "status": "success",
            "total_documents": len(all_documents)
        }
        
        # Update context with search completion
        updated_context = {
            **context,
            "search_completed": True,
            "search_sources": list(search_stats.keys()),
            "has_chromadb_results": search_stats["vector_db"]["searched"],
            "has_external_results": search_stats["external_api"]["searched"],
            "top_result_score": reranked_results["results"][0]["score"] if reranked_results and reranked_results.get("results") else None
        }
        
        return {
            "messages": [AIMessage(
                content=search_content,
                metadata={
                    "agent": "search",
                    "status": "completed",
                    "tools_used": [tool.name for tool in tools],
                    "sources_searched": sum(1 for v in search_stats.values() if v["searched"])
                }
            )],
            "current_agent": "search",
            "progress": [progress_update],
            "results": results_update,
            "context": updated_context,
            "execution_plan": state.get("execution_plan", []),
            "current_step": state.get("current_step", 0),
            "next_agent": None
        }
        
    except Exception as e:
        logger.error(f"Error in search agent: {str(e)}")
        
        # Error handling
        error_message = f"⚠️ Search Error: {str(e)}"
        progress_update["status"] = "error"
        progress_update["error"] = str(e)
        
        return {
            "messages": [AIMessage(
                content=error_message,
                metadata={"agent": "search", "status": "error"}
            )],
            "current_agent": "search",
            "progress": [progress_update],
            "errors": state.get("errors", []) + [str(e)],
            "context": context,
            "execution_plan": state.get("execution_plan", []),
            "current_step": state.get("current_step", 0),
            "next_agent": None
        }