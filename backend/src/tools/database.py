"""
Mock SQLite Database for Sales Support AI
Provides mock data for analytics and other agents
"""
import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random
import json
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
from loguru import logger


class MockDatabase:
    """Mock database with SQLite backend"""
    
    def __init__(self, db_path: str = None):
        """Initialize mock database"""
        if db_path is None:
            db_dir = Path(__file__).parent.parent.parent / "data"
            db_dir.mkdir(exist_ok=True)
            db_path = str(db_dir / "mock_sales.db")
        
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        
        # Initialize tables
        self._create_tables()
        self._seed_data()
        
        logger.info(f"Mock database initialized at {db_path}")
    
    def _create_tables(self):
        """Create database tables"""
        cursor = self.conn.cursor()
        
        # Employee Performance Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS employee_performance (
                employee_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                department TEXT NOT NULL,
                position TEXT NOT NULL,
                monthly_sales REAL DEFAULT 0,
                quarterly_sales REAL DEFAULT 0,
                yearly_sales REAL DEFAULT 0,
                deals_closed INTEGER DEFAULT 0,
                conversion_rate REAL DEFAULT 0,
                customer_satisfaction REAL DEFAULT 0,
                performance_score REAL DEFAULT 0,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Customer Trends Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS customer_trends (
                trend_id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id TEXT NOT NULL,
                customer_name TEXT NOT NULL,
                industry TEXT NOT NULL,
                trend_date DATE NOT NULL,
                monthly_revenue REAL DEFAULT 0,
                order_count INTEGER DEFAULT 0,
                average_order_value REAL DEFAULT 0,
                growth_rate REAL DEFAULT 0,
                retention_rate REAL DEFAULT 0,
                satisfaction_score REAL DEFAULT 0,
                risk_level TEXT DEFAULT 'low'
            )
        """)
        
        # Sales Transactions Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sales_transactions (
                transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id TEXT NOT NULL,
                customer_id TEXT NOT NULL,
                product_id TEXT NOT NULL,
                transaction_date TIMESTAMP NOT NULL,
                amount REAL NOT NULL,
                quantity INTEGER NOT NULL,
                discount_rate REAL DEFAULT 0,
                profit_margin REAL DEFAULT 0,
                payment_status TEXT DEFAULT 'pending',
                FOREIGN KEY (employee_id) REFERENCES employee_performance(employee_id)
            )
        """)
        
        # Product Performance Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS product_performance (
                product_id TEXT PRIMARY KEY,
                product_name TEXT NOT NULL,
                category TEXT NOT NULL,
                units_sold INTEGER DEFAULT 0,
                revenue REAL DEFAULT 0,
                avg_rating REAL DEFAULT 0,
                return_rate REAL DEFAULT 0,
                stock_level INTEGER DEFAULT 0,
                reorder_point INTEGER DEFAULT 0,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Market Analysis Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS market_analysis (
                analysis_id INTEGER PRIMARY KEY AUTOINCREMENT,
                analysis_date DATE NOT NULL,
                market_segment TEXT NOT NULL,
                total_market_size REAL DEFAULT 0,
                our_market_share REAL DEFAULT 0,
                competitor_share REAL DEFAULT 0,
                growth_forecast REAL DEFAULT 0,
                opportunity_score REAL DEFAULT 0,
                threat_level TEXT DEFAULT 'low'
            )
        """)
        
        self.conn.commit()
        logger.info("Database tables created successfully")
    
    def _seed_data(self):
        """Seed database with sample data"""
        cursor = self.conn.cursor()
        
        # Check if data already exists
        cursor.execute("SELECT COUNT(*) FROM employee_performance")
        if cursor.fetchone()[0] > 0:
            return  # Data already seeded
        
        # Seed Employee Performance
        employees = [
            ("emp_001", "김철수", "영업1팀", "팀장", 150000000, 420000000, 1500000000, 45, 0.35, 4.5, 92),
            ("emp_002", "이영희", "영업1팀", "대리", 95000000, 280000000, 980000000, 32, 0.28, 4.3, 85),
            ("emp_003", "박민수", "영업2팀", "과장", 120000000, 350000000, 1200000000, 38, 0.32, 4.4, 88),
            ("emp_004", "정수진", "영업2팀", "사원", 75000000, 210000000, 750000000, 25, 0.25, 4.2, 78),
            ("emp_005", "최동훈", "영업3팀", "차장", 135000000, 390000000, 1350000000, 42, 0.33, 4.6, 90),
            ("emp_006", "김지연", "영업3팀", "대리", 88000000, 250000000, 880000000, 28, 0.27, 4.1, 82),
            ("emp_007", "이준호", "영업1팀", "사원", 65000000, 180000000, 650000000, 20, 0.22, 4.0, 75),
            ("emp_008", "박서연", "영업2팀", "대리", 92000000, 270000000, 920000000, 30, 0.29, 4.3, 84),
        ]
        
        cursor.executemany("""
            INSERT OR REPLACE INTO employee_performance 
            (employee_id, name, department, position, monthly_sales, quarterly_sales, 
             yearly_sales, deals_closed, conversion_rate, customer_satisfaction, performance_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, employees)
        
        # Seed Customer Trends (last 12 months)
        customers = [
            ("cust_001", "삼성전자", "Technology"),
            ("cust_002", "LG화학", "Chemical"),
            ("cust_003", "현대자동차", "Automotive"),
            ("cust_004", "SK하이닉스", "Technology"),
            ("cust_005", "포스코", "Manufacturing"),
            ("cust_006", "네이버", "Technology"),
            ("cust_007", "카카오", "Technology"),
            ("cust_008", "신세계", "Retail"),
        ]
        
        for customer_id, customer_name, industry in customers:
            for month_offset in range(12):
                trend_date = datetime.now() - timedelta(days=30 * month_offset)
                base_revenue = random.uniform(50000000, 300000000)
                growth_factor = 1 + (random.uniform(-0.1, 0.2) * (12 - month_offset) / 12)
                
                cursor.execute("""
                    INSERT INTO customer_trends 
                    (customer_id, customer_name, industry, trend_date, monthly_revenue,
                     order_count, average_order_value, growth_rate, retention_rate, 
                     satisfaction_score, risk_level)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    customer_id, customer_name, industry,
                    trend_date.strftime("%Y-%m-%d"),
                    base_revenue * growth_factor,
                    random.randint(5, 50),
                    base_revenue * growth_factor / random.randint(5, 50),
                    random.uniform(-5, 15),
                    random.uniform(80, 98),
                    random.uniform(3.5, 5.0),
                    random.choice(['low', 'low', 'medium', 'high'])
                ))
        
        # Seed Sales Transactions (last 90 days)
        products = ["prod_001", "prod_002", "prod_003", "prod_004", "prod_005"]
        
        for _ in range(500):
            transaction_date = datetime.now() - timedelta(days=random.randint(0, 90))
            
            cursor.execute("""
                INSERT INTO sales_transactions
                (employee_id, customer_id, product_id, transaction_date, amount,
                 quantity, discount_rate, profit_margin, payment_status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                random.choice([e[0] for e in employees]),
                random.choice([c[0] for c in customers]),
                random.choice(products),
                transaction_date.strftime("%Y-%m-%d %H:%M:%S"),
                random.uniform(100000, 10000000),
                random.randint(1, 100),
                random.uniform(0, 0.3),
                random.uniform(0.1, 0.4),
                random.choice(['completed', 'completed', 'pending', 'cancelled'])
            ))
        
        # Seed Product Performance
        product_data = [
            ("prod_001", "AI Sales Assistant", "Software", 1500, 750000000, 4.5, 0.02, 100, 20),
            ("prod_002", "Data Analytics Suite", "Software", 800, 400000000, 4.3, 0.03, 50, 10),
            ("prod_003", "CRM Platform", "Software", 2000, 600000000, 4.4, 0.025, 150, 30),
            ("prod_004", "Compliance Manager", "Software", 500, 250000000, 4.2, 0.04, 75, 15),
            ("prod_005", "Document Generator", "Software", 1200, 360000000, 4.1, 0.035, 90, 20),
        ]
        
        cursor.executemany("""
            INSERT OR REPLACE INTO product_performance
            (product_id, product_name, category, units_sold, revenue, avg_rating,
             return_rate, stock_level, reorder_point)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, product_data)
        
        # Seed Market Analysis
        segments = ["Enterprise", "SMB", "Startup", "Government", "Education"]
        
        for segment in segments:
            for month_offset in range(6):
                analysis_date = datetime.now() - timedelta(days=30 * month_offset)
                
                cursor.execute("""
                    INSERT INTO market_analysis
                    (analysis_date, market_segment, total_market_size, our_market_share,
                     competitor_share, growth_forecast, opportunity_score, threat_level)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    analysis_date.strftime("%Y-%m-%d"),
                    segment,
                    random.uniform(1000000000, 10000000000),
                    random.uniform(10, 35),
                    random.uniform(30, 60),
                    random.uniform(5, 25),
                    random.uniform(60, 95),
                    random.choice(['low', 'medium', 'high'])
                ))
        
        self.conn.commit()
        logger.info("Database seeded with sample data")
    
    def query(self, sql: str, params: tuple = None) -> pd.DataFrame:
        """Execute SQL query and return DataFrame"""
        try:
            if params:
                return pd.read_sql_query(sql, self.conn, params=params)
            else:
                return pd.read_sql_query(sql, self.conn)
        except Exception as e:
            logger.error(f"Query error: {e}")
            return pd.DataFrame()
    
    def get_employee_performance(self, employee_id: str = None) -> pd.DataFrame:
        """Get employee performance data"""
        if employee_id:
            sql = "SELECT * FROM employee_performance WHERE employee_id = ?"
            return self.query(sql, (employee_id,))
        else:
            sql = "SELECT * FROM employee_performance ORDER BY performance_score DESC"
            return self.query(sql)
    
    def get_customer_trends(self, customer_id: str = None, months: int = 12) -> pd.DataFrame:
        """Get customer trend data"""
        date_limit = (datetime.now() - timedelta(days=30 * months)).strftime("%Y-%m-%d")
        
        if customer_id:
            sql = """
                SELECT * FROM customer_trends 
                WHERE customer_id = ? AND trend_date >= ?
                ORDER BY trend_date DESC
            """
            return self.query(sql, (customer_id, date_limit))
        else:
            sql = """
                SELECT * FROM customer_trends 
                WHERE trend_date >= ?
                ORDER BY trend_date DESC, customer_name
            """
            return self.query(sql, (date_limit,))
    
    def get_sales_summary(self, period_days: int = 30) -> Dict[str, Any]:
        """Get sales summary for a period"""
        date_limit = (datetime.now() - timedelta(days=period_days)).strftime("%Y-%m-%d")
        
        sql = """
            SELECT 
                COUNT(*) as total_transactions,
                SUM(amount) as total_revenue,
                AVG(amount) as avg_transaction_value,
                SUM(CASE WHEN payment_status = 'completed' THEN amount ELSE 0 END) as completed_revenue,
                COUNT(DISTINCT employee_id) as active_employees,
                COUNT(DISTINCT customer_id) as active_customers
            FROM sales_transactions
            WHERE transaction_date >= ?
        """
        
        result = self.query(sql, (date_limit,))
        return result.iloc[0].to_dict() if not result.empty else {}
    
    def get_top_performers(self, limit: int = 5) -> pd.DataFrame:
        """Get top performing employees"""
        sql = """
            SELECT 
                e.employee_id,
                e.name,
                e.department,
                e.position,
                e.monthly_sales,
                e.performance_score,
                COUNT(s.transaction_id) as recent_deals,
                SUM(s.amount) as recent_revenue
            FROM employee_performance e
            LEFT JOIN sales_transactions s 
                ON e.employee_id = s.employee_id 
                AND s.transaction_date >= date('now', '-30 days')
            GROUP BY e.employee_id
            ORDER BY e.performance_score DESC
            LIMIT ?
        """
        return self.query(sql, (limit,))
    
    def get_product_performance(self) -> pd.DataFrame:
        """Get product performance data"""
        sql = """
            SELECT * FROM product_performance
            ORDER BY revenue DESC
        """
        return self.query(sql)
    
    def get_market_analysis(self, segment: str = None) -> pd.DataFrame:
        """Get market analysis data"""
        if segment:
            sql = """
                SELECT * FROM market_analysis
                WHERE market_segment = ?
                ORDER BY analysis_date DESC
            """
            return self.query(sql, (segment,))
        else:
            sql = """
                SELECT * FROM market_analysis
                ORDER BY analysis_date DESC, opportunity_score DESC
            """
            return self.query(sql)
    
    def close(self):
        """Close database connection"""
        self.conn.close()
        logger.info("Database connection closed")