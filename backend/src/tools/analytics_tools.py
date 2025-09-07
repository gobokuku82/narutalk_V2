"""
Analytics Tools for LangGraph 0.6.6
Pandas-based data analysis and insights generation
"""
from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
from langchain_core.tools import tool
from loguru import logger
from .database import MockDatabase


# Initialize database connection
db = MockDatabase()


@tool
def query_performance_data(employee_id: Optional[str] = None, department: Optional[str] = None) -> str:
    """
    Query employee performance data from SQLite database
    
    Args:
        employee_id: Specific employee ID to query
        department: Filter by department
    
    Returns:
        JSON string with performance data and analysis
    """
    try:
        # Get employee performance data
        df = db.get_employee_performance(employee_id)
        
        # Filter by department if specified
        if department and not employee_id:
            df = df[df['department'] == department]
        
        if df.empty:
            return json.dumps({"error": "No data found", "count": 0}, ensure_ascii=False)
        
        # Calculate statistics
        stats = {
            "total_employees": len(df),
            "avg_monthly_sales": float(df['monthly_sales'].mean()),
            "total_monthly_sales": float(df['monthly_sales'].sum()),
            "avg_performance_score": float(df['performance_score'].mean()),
            "top_performer": {
                "name": df.iloc[0]['name'],
                "score": float(df.iloc[0]['performance_score']),
                "monthly_sales": float(df.iloc[0]['monthly_sales'])
            } if not df.empty else None,
            "department_breakdown": df.groupby('department').agg({
                'monthly_sales': 'sum',
                'performance_score': 'mean',
                'deals_closed': 'sum'
            }).to_dict() if len(df) > 1 else None
        }
        
        # Add individual employee data if querying specific employee
        if employee_id and not df.empty:
            emp_data = df.iloc[0].to_dict()
            stats["employee_details"] = {
                k: float(v) if isinstance(v, (np.integer, np.floating)) else v
                for k, v in emp_data.items()
            }
        
        logger.info(f"Performance data queried: {len(df)} records")
        return json.dumps(stats, ensure_ascii=False, default=str)
        
    except Exception as e:
        logger.error(f"Error querying performance data: {e}")
        return json.dumps({"error": str(e)}, ensure_ascii=False)


@tool
def analyze_sales_trend(period_days: int = 30, customer_id: Optional[str] = None) -> str:
    """
    Analyze sales trends using Pandas
    
    Args:
        period_days: Number of days to analyze
        customer_id: Specific customer to analyze
    
    Returns:
        JSON string with trend analysis
    """
    try:
        # Get sales summary
        summary = db.get_sales_summary(period_days)
        
        # Get customer trends if specified
        if customer_id:
            customer_df = db.get_customer_trends(customer_id, months=12)
        else:
            customer_df = db.get_customer_trends(months=3)
        
        # Analyze trends
        trend_analysis = {
            "period_days": period_days,
            "sales_summary": summary,
            "customer_analysis": {}
        }
        
        if not customer_df.empty:
            # Group by customer for overall trends
            customer_grouped = customer_df.groupby('customer_name').agg({
                'monthly_revenue': ['mean', 'sum', 'std'],
                'growth_rate': 'mean',
                'satisfaction_score': 'mean',
                'order_count': 'sum'
            })
            
            # Calculate trend direction
            recent_df = customer_df[customer_df['trend_date'] >= (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")]
            older_df = customer_df[customer_df['trend_date'] < (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")]
            
            if not recent_df.empty and not older_df.empty:
                recent_avg = recent_df['monthly_revenue'].mean()
                older_avg = older_df['monthly_revenue'].mean()
                trend_direction = "increasing" if recent_avg > older_avg else "decreasing"
                trend_percentage = ((recent_avg - older_avg) / older_avg * 100) if older_avg > 0 else 0
            else:
                trend_direction = "stable"
                trend_percentage = 0
            
            # Top customers by revenue
            top_customers = customer_df.groupby('customer_name')['monthly_revenue'].sum().nlargest(5)
            
            trend_analysis["customer_analysis"] = {
                "total_customers": customer_df['customer_id'].nunique(),
                "avg_monthly_revenue": float(customer_df['monthly_revenue'].mean()),
                "total_revenue": float(customer_df['monthly_revenue'].sum()),
                "trend_direction": trend_direction,
                "trend_percentage": float(trend_percentage),
                "top_customers": top_customers.to_dict() if not top_customers.empty else {},
                "avg_satisfaction": float(customer_df['satisfaction_score'].mean()),
                "risk_distribution": customer_df['risk_level'].value_counts().to_dict()
            }
        
        # Get top performers for the period
        top_performers = db.get_top_performers(limit=3)
        if not top_performers.empty:
            trend_analysis["top_performers"] = [
                {
                    "name": row['name'],
                    "department": row['department'],
                    "recent_revenue": float(row['recent_revenue']) if row['recent_revenue'] else 0,
                    "performance_score": float(row['performance_score'])
                }
                for _, row in top_performers.iterrows()
            ]
        
        logger.info(f"Sales trend analysis completed for {period_days} days")
        return json.dumps(trend_analysis, ensure_ascii=False, default=str)
        
    except Exception as e:
        logger.error(f"Error analyzing sales trend: {e}")
        return json.dumps({"error": str(e)}, ensure_ascii=False)


@tool
def calculate_kpis() -> str:
    """
    Calculate key performance indicators (KPIs)
    
    Returns:
        JSON string with calculated KPIs
    """
    try:
        # Get various data
        employees_df = db.get_employee_performance()
        sales_30d = db.get_sales_summary(30)
        sales_90d = db.get_sales_summary(90)
        products_df = db.get_product_performance()
        market_df = db.get_market_analysis()
        
        # Calculate KPIs
        kpis = {
            "employee_kpis": {},
            "sales_kpis": {},
            "product_kpis": {},
            "market_kpis": {}
        }
        
        # Employee KPIs
        if not employees_df.empty:
            kpis["employee_kpis"] = {
                "total_employees": len(employees_df),
                "avg_performance_score": float(employees_df['performance_score'].mean()),
                "top_performer_score": float(employees_df['performance_score'].max()),
                "avg_conversion_rate": float(employees_df['conversion_rate'].mean()),
                "total_deals_closed": int(employees_df['deals_closed'].sum()),
                "avg_customer_satisfaction": float(employees_df['customer_satisfaction'].mean())
            }
        
        # Sales KPIs
        if sales_30d:
            kpis["sales_kpis"]["last_30_days"] = {
                "total_revenue": float(sales_30d.get('total_revenue', 0)),
                "total_transactions": int(sales_30d.get('total_transactions', 0)),
                "avg_transaction_value": float(sales_30d.get('avg_transaction_value', 0)),
                "completion_rate": float(sales_30d.get('completed_revenue', 0) / sales_30d.get('total_revenue', 1) * 100) if sales_30d.get('total_revenue', 0) > 0 else 0
            }
        
        if sales_90d:
            kpis["sales_kpis"]["last_90_days"] = {
                "total_revenue": float(sales_90d.get('total_revenue', 0)),
                "total_transactions": int(sales_90d.get('total_transactions', 0)),
                "active_customers": int(sales_90d.get('active_customers', 0))
            }
        
        # Calculate growth rate (30d vs previous 30d)
        if sales_30d and sales_90d:
            current_revenue = sales_30d.get('total_revenue', 0)
            total_90d_revenue = sales_90d.get('total_revenue', 0)
            previous_revenue = total_90d_revenue - current_revenue
            
            if previous_revenue > 0:
                growth_rate = ((current_revenue - previous_revenue) / previous_revenue) * 100
                kpis["sales_kpis"]["growth_rate"] = float(growth_rate)
        
        # Product KPIs
        if not products_df.empty:
            kpis["product_kpis"] = {
                "total_products": len(products_df),
                "total_units_sold": int(products_df['units_sold'].sum()),
                "total_product_revenue": float(products_df['revenue'].sum()),
                "avg_product_rating": float(products_df['avg_rating'].mean()),
                "avg_return_rate": float(products_df['return_rate'].mean()),
                "best_selling_product": {
                    "name": products_df.iloc[0]['product_name'],
                    "revenue": float(products_df.iloc[0]['revenue']),
                    "units_sold": int(products_df.iloc[0]['units_sold'])
                } if not products_df.empty else None
            }
        
        # Market KPIs
        if not market_df.empty:
            recent_market = market_df[market_df['analysis_date'] >= (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")]
            
            if not recent_market.empty:
                kpis["market_kpis"] = {
                    "avg_market_share": float(recent_market['our_market_share'].mean()),
                    "avg_growth_forecast": float(recent_market['growth_forecast'].mean()),
                    "avg_opportunity_score": float(recent_market['opportunity_score'].mean()),
                    "threat_levels": recent_market['threat_level'].value_counts().to_dict(),
                    "best_segment": {
                        "name": recent_market.nlargest(1, 'opportunity_score').iloc[0]['market_segment'],
                        "opportunity_score": float(recent_market.nlargest(1, 'opportunity_score').iloc[0]['opportunity_score'])
                    } if not recent_market.empty else None
                }
        
        # Overall health score (weighted average of key metrics)
        health_score = 0
        weight_sum = 0
        
        if kpis["employee_kpis"]:
            health_score += kpis["employee_kpis"]["avg_performance_score"] * 0.3
            weight_sum += 0.3
        
        if kpis["sales_kpis"].get("growth_rate"):
            normalized_growth = min(max(kpis["sales_kpis"]["growth_rate"] + 50, 0), 100)
            health_score += normalized_growth * 0.3
            weight_sum += 0.3
        
        if kpis["product_kpis"]:
            product_score = kpis["product_kpis"]["avg_product_rating"] * 20
            health_score += product_score * 0.2
            weight_sum += 0.2
        
        if kpis["market_kpis"]:
            health_score += kpis["market_kpis"]["avg_opportunity_score"] * 0.2
            weight_sum += 0.2
        
        if weight_sum > 0:
            kpis["overall_health_score"] = float(health_score / weight_sum)
        
        logger.info("KPIs calculated successfully")
        return json.dumps(kpis, ensure_ascii=False, default=str)
        
    except Exception as e:
        logger.error(f"Error calculating KPIs: {e}")
        return json.dumps({"error": str(e)}, ensure_ascii=False)


@tool
def predict_sales_trend(months_ahead: int = 3) -> str:
    """
    Simple trend prediction using moving averages
    
    Args:
        months_ahead: Number of months to predict ahead
    
    Returns:
        JSON string with predictions
    """
    try:
        # Get historical customer trends
        customer_df = db.get_customer_trends(months=12)
        
        if customer_df.empty:
            return json.dumps({"error": "Insufficient data for prediction"}, ensure_ascii=False)
        
        # Convert trend_date to datetime
        customer_df['trend_date'] = pd.to_datetime(customer_df['trend_date'])
        
        # Group by month and calculate monthly totals
        monthly_revenue = customer_df.groupby(pd.Grouper(key='trend_date', freq='M'))['monthly_revenue'].sum()
        
        if len(monthly_revenue) < 3:
            return json.dumps({"error": "Need at least 3 months of data for prediction"}, ensure_ascii=False)
        
        # Calculate moving average and trend
        ma_3 = monthly_revenue.rolling(window=3).mean()
        
        # Simple linear trend
        x = np.arange(len(monthly_revenue))
        y = monthly_revenue.values
        
        # Remove NaN values
        mask = ~np.isnan(y)
        x_clean = x[mask]
        y_clean = y[mask]
        
        if len(x_clean) < 2:
            return json.dumps({"error": "Insufficient clean data for trend calculation"}, ensure_ascii=False)
        
        # Fit linear trend
        z = np.polyfit(x_clean, y_clean, 1)
        trend_slope = z[0]
        trend_intercept = z[1]
        
        # Make predictions
        predictions = []
        last_x = len(monthly_revenue)
        
        for i in range(1, months_ahead + 1):
            predicted_value = trend_slope * (last_x + i) + trend_intercept
            
            # Add some randomness based on historical volatility
            std_dev = monthly_revenue.std()
            noise = np.random.normal(0, std_dev * 0.1)  # 10% of historical volatility
            predicted_value += noise
            
            # Ensure positive values
            predicted_value = max(predicted_value, 0)
            
            future_date = monthly_revenue.index[-1] + pd.DateOffset(months=i)
            
            predictions.append({
                "month": future_date.strftime("%Y-%m"),
                "predicted_revenue": float(predicted_value),
                "confidence_low": float(predicted_value * 0.8),
                "confidence_high": float(predicted_value * 1.2)
            })
        
        # Calculate trend indicators
        recent_avg = monthly_revenue[-3:].mean()
        older_avg = monthly_revenue[-6:-3].mean() if len(monthly_revenue) >= 6 else monthly_revenue[:-3].mean()
        
        trend_direction = "upward" if trend_slope > 0 else "downward" if trend_slope < 0 else "stable"
        momentum = ((recent_avg - older_avg) / older_avg * 100) if older_avg > 0 else 0
        
        result = {
            "predictions": predictions,
            "trend_analysis": {
                "direction": trend_direction,
                "slope": float(trend_slope),
                "momentum_percentage": float(momentum),
                "recent_average": float(recent_avg),
                "volatility": float(monthly_revenue.std())
            },
            "historical_context": {
                "months_analyzed": len(monthly_revenue),
                "highest_month": {
                    "date": monthly_revenue.idxmax().strftime("%Y-%m"),
                    "value": float(monthly_revenue.max())
                },
                "lowest_month": {
                    "date": monthly_revenue.idxmin().strftime("%Y-%m"),
                    "value": float(monthly_revenue.min())
                }
            }
        }
        
        logger.info(f"Sales trend prediction completed for {months_ahead} months")
        return json.dumps(result, ensure_ascii=False, default=str)
        
    except Exception as e:
        logger.error(f"Error predicting sales trend: {e}")
        return json.dumps({"error": str(e)}, ensure_ascii=False)