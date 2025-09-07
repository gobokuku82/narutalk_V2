"""
Analytics Agent for LangGraph 0.6.6
Handles data analysis with SQLite and Pandas
"""
from typing import Dict, Any
from datetime import datetime
import json
from langchain_core.messages import AIMessage, SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import ToolNode
from loguru import logger

# Import our analytics tools
from ..tools.analytics_tools import (
    query_performance_data,
    analyze_sales_trend,
    calculate_kpis,
    predict_sales_trend
)
from ..state.agent_state import AgentState


def analytics_agent(state: AgentState) -> dict:
    """
    Enhanced Analytics agent with SQLite data and Pandas analysis
    Following rules.md: Node functions MUST return dict
    Uses StateGraph pattern with tool integration
    """
    # Initialize LLM with tools binding
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    
    # Bind tools to LLM
    tools = [query_performance_data, analyze_sales_trend, calculate_kpis, predict_sales_trend]
    llm_with_tools = llm.bind_tools(tools)
    
    # Get task description and context
    task_description = state.get("task_description", "")
    context = state.get("context", {})
    messages = state.get("messages", [])
    
    # Progress tracking
    progress_update = {
        "agent": "analytics",
        "timestamp": datetime.now().isoformat(),
        "action": "analyzing_data_with_sqlite"
    }
    
    logger.info(f"Analytics agent processing: {task_description[:100]}...")
    
    # Determine analysis type and use appropriate tools
    analysis_results = {}
    
    try:
        # Query performance data from SQLite
        if "performance" in task_description.lower() or "실적" in task_description.lower():
            perf_data = query_performance_data.invoke({"employee_id": context.get("employee_id")})
            analysis_results["performance"] = json.loads(perf_data)
            logger.info("Performance data queried from SQLite")
        
        # Analyze sales trends
        if "trend" in task_description.lower() or "추세" in task_description.lower() or "sales" in task_description.lower():
            period_days = context.get("period_days", 30)
            trend_data = analyze_sales_trend.invoke({"period_days": period_days})
            analysis_results["trends"] = json.loads(trend_data)
            logger.info(f"Sales trend analyzed for {period_days} days")
        
        # Calculate KPIs
        if "kpi" in task_description.lower() or "지표" in task_description.lower() or not analysis_results:
            kpi_data = calculate_kpis.invoke({})
            analysis_results["kpis"] = json.loads(kpi_data)
            logger.info("KPIs calculated")
        
        # Predict future trends if requested
        if "predict" in task_description.lower() or "forecast" in task_description.lower() or "예측" in task_description.lower():
            prediction_data = predict_sales_trend.invoke({"months_ahead": 3})
            analysis_results["predictions"] = json.loads(prediction_data)
            logger.info("Sales trend prediction completed")
        
        # If no specific analysis was triggered, run comprehensive analysis
        if not analysis_results:
            perf_data = query_performance_data.invoke({})
            analysis_results["performance"] = json.loads(perf_data)
            
            trend_data = analyze_sales_trend.invoke({"period_days": 30})
            analysis_results["trends"] = json.loads(trend_data)
            
            kpi_data = calculate_kpis.invoke({})
            analysis_results["kpis"] = json.loads(kpi_data)
            
            logger.info("Comprehensive analysis completed")
        
        # Use LLM to generate insights from the data
        data_summary = json.dumps(analysis_results, ensure_ascii=False, indent=2)
        
        insight_prompt = f"""
        Based on the following data analysis results from our SQLite database:
        
        {data_summary[:3000]}  # Limit to avoid token overflow
        
        Task: {task_description}
        
        Please provide:
        1. Executive Summary (2-3 sentences)
        2. Key Findings (3-5 bullet points)
        3. Actionable Recommendations (3-5 items)
        4. Risk Factors or Concerns (if any)
        
        Focus on practical, data-driven insights.
        """
        
        # Get LLM insights
        llm_response = llm.invoke([
            SystemMessage(content="You are a senior data analyst providing insights from SQL database analysis."),
            HumanMessage(content=insight_prompt)
        ])
        
        # Format final analysis report
        analysis_content = f"""
📊 **Data Analysis Report** 
*Generated from SQLite Database*

{llm_response.content}

---

📈 **Detailed Metrics**
"""
        
        # Add specific metrics based on what was analyzed
        if "kpis" in analysis_results:
            kpis = analysis_results["kpis"]
            if "overall_health_score" in kpis:
                analysis_content += f"\n• **Overall Health Score**: {kpis['overall_health_score']:.1f}/100"
            if "employee_kpis" in kpis:
                emp_kpis = kpis["employee_kpis"]
                analysis_content += f"\n• **Team Performance**: {emp_kpis.get('avg_performance_score', 0):.1f}/100"
                analysis_content += f"\n• **Total Deals Closed**: {emp_kpis.get('total_deals_closed', 0):,}"
            if "sales_kpis" in kpis and "last_30_days" in kpis["sales_kpis"]:
                sales_30d = kpis["sales_kpis"]["last_30_days"]
                analysis_content += f"\n• **Monthly Revenue**: ₩{sales_30d.get('total_revenue', 0):,.0f}"
                analysis_content += f"\n• **Growth Rate**: {kpis['sales_kpis'].get('growth_rate', 0):.1f}%"
        
        if "trends" in analysis_results:
            trends = analysis_results["trends"]
            if "customer_analysis" in trends:
                cust = trends["customer_analysis"]
                analysis_content += f"\n• **Revenue Trend**: {cust.get('trend_direction', 'stable')} ({cust.get('trend_percentage', 0):.1f}%)"
                analysis_content += f"\n• **Customer Satisfaction**: {cust.get('avg_satisfaction', 0):.1f}/5.0"
        
        if "predictions" in analysis_results:
            preds = analysis_results["predictions"]
            if "predictions" in preds and preds["predictions"]:
                next_month = preds["predictions"][0]
                analysis_content += f"\n• **Next Month Forecast**: ₩{next_month['predicted_revenue']:,.0f}"
        
        # Update progress
        progress_update["status"] = "completed"
        progress_update["summary"] = f"Analyzed {len(analysis_results)} data categories"
        progress_update["data_sources"] = list(analysis_results.keys())
        
        # Store detailed results in state
        results_update = state.get("results", {})
        results_update["analytics"] = {
            "timestamp": datetime.now().isoformat(),
            "analysis": analysis_content,
            "raw_data": analysis_results,
            "status": "success",
            "data_points_analyzed": sum(
                len(v) if isinstance(v, dict) else 1 
                for v in analysis_results.values()
            )
        }
        
        # Update context with analytics insights
        updated_context = {
            **context,
            "analytics_completed": True,
            "has_performance_data": "performance" in analysis_results,
            "has_trend_data": "trends" in analysis_results,
            "has_predictions": "predictions" in analysis_results,
            "overall_health": analysis_results.get("kpis", {}).get("overall_health_score")
        }
        
        return {
            "messages": [AIMessage(
                content=analysis_content,
                metadata={
                    "agent": "analytics",
                    "status": "completed",
                    "tools_used": [tool.name for tool in tools],
                    "data_categories": list(analysis_results.keys())
                }
            )],
            "current_agent": "analytics",
            "progress": [progress_update],
            "results": results_update,
            "context": updated_context
        }
        
    except Exception as e:
        logger.error(f"Error in analytics agent: {str(e)}")
        
        # Error handling
        error_message = f"⚠️ Analytics Error: {str(e)}"
        progress_update["status"] = "error"
        progress_update["error"] = str(e)
        
        return {
            "messages": [AIMessage(
                content=error_message,
                metadata={"agent": "analytics", "status": "error"}
            )],
            "current_agent": "analytics",
            "progress": [progress_update],
            "errors": state.get("errors", []) + [str(e)],
            "context": context
        }