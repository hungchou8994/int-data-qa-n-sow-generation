"""
Test script for SOW Google Sheets export
"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), '.env'))

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scope_of_work.model import (
    ProjectDetail,
    ProjectAssumption,
    AssumptionSection,
    ScopeOfWork,
    ScopeOfWorkTask
)
from sow_sheet.connect import SOWGoogleSheetsConnector

import logging
logging.basicConfig(level=logging.INFO)

def create_sample_project_detail():
    """Create sample ProjectDetail for testing"""
    return ProjectDetail(
        detail_id="test_detail_001",
        customer_name="ABC Technology",
        business_domain="IT and Software Services",
        overview="""This is a project to build the Demand Forecasting Platform for X. The functionality of this AI and Data Platform will have the following key features:
- Advanced analytics and reporting capabilities
- Real-time data processing
- Machine learning integration""",
        key_features=[
            "Data Integration from Dropbox: Daily pull and unify sales, inventory, and operational data from Dropbox",
            "Data Preparation & Processing: Clean and transform historical data for use in forecasting models",
            "Demand Forecasting: Predict future demand by day or by period (e.g., 3-days / weekly) based on historical demand trends",
            "Forecast Reporting & Visualization: Provide a centralized dashboard to visualize demand forecasts, historical trends, and performance comparisons",
            "Product Update: Automatically update model on a defined schedule (e.g., daily or weekly)"
        ],
        created_at=datetime.now(),
        language="English"
    )

def create_sample_project_assumption():
    """Create sample ProjectAssumption for testing"""
    sections = [
        AssumptionSection(
            section="Data Scope",
            points=[
                "The client's sales, inventory, and operational in CSV files are stored in 3 folders respectively under one shared folder in Dropbox",
                "The client will grant access to query data sources Dropbox folders for integration and processing.",
                "Data are from CSV files stored in GCP folders for integration and processing.",
                "Evaluation Dashboard: 2 pages, total 10 charts",
                "Prediction Dashboard: 2 pages, total 10 charts"
            ]
        ),
        AssumptionSection(
            section="Demand Forecasting",
            points=[
                "SKUs: Up to 1000",
                "Accuracy: Up to 80% (for predicted SKUs only). Requirements for predicted SKU:",
                "History data: at least 3 years",
                "History data for the required consistent transactions (continuous, no replacement, no out-of-stock for a long time)",
                "Evaluation Dashboard: 2 pages, total 10 charts",
                "Prediction Dashboard: 2 pages, total 10 charts"
            ]
        )
    ]
    
    return ProjectAssumption(
        assumption_id="test_assumption_001",
        customer_name="ABC Technology",
        business_domain="IT and Software Services",
        assumptions=sections,
        created_at=datetime.now(),
        language="English"
    )

def create_sample_scope_of_work():
    """Create sample ScopeOfWork for testing"""
    tasks = [
        # Assessment & Planning
        ScopeOfWorkTask(
            task_category="Assessment & Planning",
            task_title="Identify business requirements",
            content="""- Verify business models
- Verify Scope of Works deployed
- Identify Client's expectation
- Verify data sources, source types and scope of data sources
- Verify data source access methods, information stores on GCP
- Verify the quantity and capacity of data sources converted to GCP
- Verify comparison of raw data converted to GCP with source data
- Verify the schema and data types of final clean data""",
            man_days=2.0,
            source="generated"
        ),
        ScopeOfWorkTask(
            task_category="Assessment & Planning",
            task_title="Explore current data sources",
            content="""- Verify data sources, source types and scope of data sources
- Verify data source access methods, information stores on GCP
- Verify the quantity and capacity of data sources converted to GCP""",
            man_days=3.0,
            source="rag",
            similarity_score=0.85
        ),
        ScopeOfWorkTask(
            task_category="Assessment & Planning",
            task_title="Stakeholder alignment",
            content="""- Verify input and processing of AI/ML models in use
- Verify test cases and success criteria for the project""",
            man_days=2.0,
            source="generated"
        ),
        # GCP Project Preparation
        ScopeOfWorkTask(
            task_category="GCP Project Preparation",
            task_title="Billing & Project Setup",
            content="""- Configure billing account and set up project structure""",
            man_days=0.5,
            source="generated"
        ),
        ScopeOfWorkTask(
            task_category="GCP Project Preparation",
            task_title="Access assignment to the Project",
            content="""- Configure network, add team members, assign permissions and set up dev and MVP environments""",
            man_days=1.5,
            source="generated"
        ),
        # Design Architecture
        ScopeOfWorkTask(
            task_category="Design Architecture",
            task_title="Standardize pipeline based on survey details and design dataset",
            content="""Design pipeline according to agreed information""",
            man_days=2.0,
            source="rag",
            similarity_score=0.78
        ),
        ScopeOfWorkTask(
            task_category="Design Architecture",
            task_title="Design pipeline, data model and corresponding reports",
            content="""Design detailed data model and corresponding report after agreeing on detailed requirements""",
            man_days=5.0,
            source="generated"
        ),
        # Data Integration
        ScopeOfWorkTask(
            task_category="Data Integration from Dropbox (Cloud Run)",
            task_title="Check and complete input data: schema, data type, filter",
            content="""- Review the raw data files for consistency and completeness.
- Validate and standardize data schema - ensuring uniform column names, data types, and formats across files.
- Identify and document outliers, missing values, nulls, and duplicates to inform cleaning processes.
- Document the finalized data schema to serve as a reference for all subsequent pipeline steps.
- Create and configure datasets in BigQuery to store both raw and processed data.""",
            man_days=4.0,
            source="generated"
        ),
        ScopeOfWorkTask(
            task_category="Data Integration from Dropbox (Cloud Run)",
            task_title="Set up dataset for Migration",
            content="""- Define dataset structure and table partitioning strategy (e.g., by date or source file) for optimized query performance.
- Implement appropriate data governance settings such as dataset access controls policies.
- Ensure dataset naming and structure align with organizational data architecture standards.""",
            man_days=2.0,
            source="generated"
        ),
    ]
    
    total_days = sum(task.man_days for task in tasks)
    
    return ScopeOfWork(
        sow_id="test_sow_001",
        customer_name="ABC Technology",
        business_domain="IT and Software Services",
        project_type="Data Analytics",
        tasks=tasks,
        total_man_days=total_days,
        total_tasks=len(tasks),
        created_at=datetime.now(),
        language="English"
    )

def test_export():
    """Test the export functionality"""
    print("=" * 60)
    print("SOW Google Sheets Export Test")
    print("=" * 60)
    
    # Check credentials
    credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    if not credentials_path or not os.path.exists(credentials_path):
        print("❌ ERROR: GOOGLE_APPLICATION_CREDENTIALS not found!")
        print("Please set the environment variable to your service account key file.")
        return
    
    print(f"✅ Credentials found: {credentials_path}")
    
    # Create sample data
    print("\n📝 Creating sample data...")
    project_detail = create_sample_project_detail()
    project_assumption = create_sample_project_assumption()
    scope_of_work = create_sample_scope_of_work()
    
    print(f"   - Project Detail: {project_detail.customer_name}")
    print(f"   - Assumptions: {len(project_assumption.assumptions)} sections")
    print(f"   - SOW Tasks: {scope_of_work.total_tasks} tasks, {scope_of_work.total_man_days} man-days")
    
    # Get spreadsheet URL from user
    print("\n" + "=" * 60)
    print("📊 Google Sheet Information")
    print("=" * 60)
    spreadsheet_url = input("Enter Google Sheet URL: ").strip()
    
    if not spreadsheet_url:
        print("❌ No URL provided. Exiting.")
        return
    
    overview_ws_name = input("Overview worksheet name (default: Overview): ").strip() or "Overview"
    sow_ws_name = input("SOW worksheet name (default: Scope of Work): ").strip() or "Scope of Work"
    
    # Export to Google Sheets
    print("\n🚀 Starting export...")
    print(f"   - Overview worksheet: {overview_ws_name}")
    print(f"   - SOW worksheet: {sow_ws_name}")
    
    try:
        connector = SOWGoogleSheetsConnector()
        result = connector.export_sow_to_sheet(
            spreadsheet_url=spreadsheet_url,
            project_detail=project_detail,
            project_assumption=project_assumption,
            scope_of_work=scope_of_work,
            overview_worksheet_name=overview_ws_name,
            sow_worksheet_name=sow_ws_name
        )
        
        print("\n" + "=" * 60)
        if result.success:
            print("✅ SUCCESS!")
            print(f"   Message: {result.message}")
            print(f"   URL: {result.spreadsheet_url}")
            print("\n🎉 You can now open the sheet and check the exported data!")
        else:
            print("❌ FAILED!")
            print(f"   Error: {result.error_message}")
            print("\n💡 Tips:")
            print("   - Make sure you shared the sheet with the service account email")
            print("   - Check that the URL is correct")
            print("   - Verify your credentials are valid")
        print("=" * 60)
        
    except Exception as e:
        print("\n" + "=" * 60)
        print("❌ ERROR occurred during export!")
        print(f"   {str(e)}")
        print("=" * 60)
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_export()
