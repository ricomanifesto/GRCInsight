import logging
import os
import re
import json
from typing import List, Dict, Any
from datetime import datetime

import tiktoken
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize tokenizer for token counting
tokenizer = tiktoken.get_encoding("cl100k_base")

def load_template() -> str:
    """Load the GRC report template"""
    template_path = os.path.join(os.path.dirname(__file__), "..", "..", "docs", "templates", "grc_report.md")
    try:
        with open(template_path, "r") as f:
            return f.read()
    except Exception as e:
        logger.error(f"Error loading template: {e}")
        return """# GRC Intelligence Report

{{ grc_summary }}

## Regulatory Updates

{{ regulatory_updates }}

## Compliance Requirements

{{ compliance_requirements }}

## Risk Management

{{ risk_management }}

## Governance Changes

{{ governance_changes }}
"""

def filter_grc_articles(articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Filter articles to only include those with GRC-related content
    
    Args:
        articles: List of article dictionaries
        
    Returns:
        Filtered list of articles with GRC content
    """
    logger.info(f"Filtering {len(articles)} articles for GRC content")
    
    # Pass all articles to the AI for analysis
    # This gives the AI more context to work with
    return articles

async def analyze_grc_content(articles: List[Dict[str, Any]], config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze GRC-related articles
    
    Args:
        articles: List of article dictionaries with GRC content
        config: Configuration dictionary
        
    Returns:
        GRC analysis report
    """
    logger.info(f"Analyzing GRC content in {len(articles)} articles")
    
    # Get the template
    template = load_template()
    
    # Initialize the AI model
    api_key = os.getenv("OPENAI_API_KEY")
    model_name = config.get("analysis", {}).get("model", "gpt-4o")
    temperature = config.get("analysis", {}).get("temperature", 0.1)
    
    if not api_key:
        logger.error("No OpenAI API key provided")
        return {
            "grc_report": "# Error: No OpenAI API Key\n\nPlease set the OPENAI_API_KEY environment variable.",
            "date": datetime.now().strftime("%Y-%m-%d"),
            "error": "No API key"
        }
    
    # o1 and o3 models don't support temperature parameter
    if model_name.startswith("o1") or model_name.startswith("o3"):
        model = ChatOpenAI(
            api_key=api_key,
            model=model_name
        )
    else:
        model = ChatOpenAI(
            api_key=api_key,
            model=model_name,
            temperature=temperature
        )
    
    # Prepare all article summaries
    all_article_summaries = []
    all_regulations = set()
    all_frameworks = set()
    all_industries = set()
    all_regulatory_bodies = set()
    
    for article in articles:
        # Get article metadata
        title = article.get("title", "")
        source = article.get("source", "")
        link = article.get("link", "")
        
        # Get article content or summary
        content = article.get("content", article.get("summary", "No content available"))
        
        # Create summary
        summary = f"**{title}** (Source: {source})\n\nURL: {link}\n\n{content[:500]}...\n\n"
        all_article_summaries.append(summary)
        
        # Extract GRC entities
        if "regulations" in article:
            for regulation in article.get("regulations", []):
                all_regulations.add(regulation)
        if "frameworks" in article:
            for framework in article.get("frameworks", []):
                all_frameworks.add(framework)
        if "industries" in article:
            for industry in article.get("industries", []):
                all_industries.add(industry)
        if "regulatory_bodies" in article:
            for body in article.get("regulatory_bodies", []):
                all_regulatory_bodies.add(body)
    
    # Create a comprehensive prompt for GRC analysis
    prompt = f"""
You're a GRC (Governance, Risk, and Compliance) expert specializing in regulatory analysis and compliance intelligence. Analyze the following articles to generate a comprehensive report on current GRC developments.

Generate a report following this EXACT structure with professional markdown formatting:

# GRC Intelligence Report

[Write a comprehensive summary paragraph of the most critical GRC developments. Focus on regulatory changes, compliance updates, governance improvements, and risk management developments. Only mention specific regulation codes or framework versions if they are explicitly provided in the articles.]

## Regulatory Updates and Changes

[For each significant regulatory development, create a well-formatted subsection:

### Regulation/Rule Name
- **Description**: Detailed description of the regulatory change or update
- **Impact**: What organizations need to do to comply
- **Timeline**: Implementation deadlines or effective dates if mentioned
- **Affected Industries**: Which sectors are impacted
- **Regulatory Body**: Which agency or authority issued the update
]

## Compliance Requirements and Obligations

[Create a well-formatted bullet list of new or updated compliance requirements:
- **Requirement Name**: Specific details about what organizations must do
- **Framework/Standard**: Associated compliance framework or standard
- **Implementation Details**: How organizations should implement the requirement
]

## Risk Management Developments

[Use clear formatting for risk-related updates:
- **Risk Area**: Description of the risk category or concern
- **Assessment Methods**: How risks should be evaluated or measured
- **Mitigation Strategies**: Recommended approaches to manage the risks
]

## Governance and Oversight Changes

[Organize governance information clearly:
- **Governance Area**: Board oversight, executive responsibility, committee structure changes
- **Requirements**: New governance requirements or best practices
- **Accountability**: Who is responsible for implementation and oversight
]

## Industry-Specific Impacts

[Break down impacts by industry sector:
- **Industry Sector**: Specific impacts and requirements for different industries
- **Sector-Specific Requirements**: Unique compliance obligations for each industry
]

Formatting requirements:
- Use proper markdown with **bold** for emphasis
- Create clear bullet points with good spacing
- Use ### for subsections within main sections
- Write professional, well-structured content
- Only mention specific regulation codes, framework versions, or compliance deadlines when they are actually provided in the source articles
- Do NOT mention missing or unavailable regulatory information

Focus specifically on:
- New or updated regulations and compliance requirements
- Changes to governance frameworks and standards
- Risk management updates and best practices
- Industry-specific compliance developments
- Regulatory enforcement actions and guidance
- Board governance and oversight requirements
- Internal control and audit developments
- Data privacy and security compliance updates

Here are the articles:

{''.join(all_article_summaries)}

Generate a well-formatted GRC intelligence report following the structure above. Be comprehensive but only include specific regulatory details when they are explicitly mentioned in the articles.
"""
    
    # Estimate token count for logging
    estimated_tokens = len(tokenizer.encode(prompt))
    logger.info(f"Estimated token count for analysis prompt: {estimated_tokens}")
    
    # Call the AI model
    try:
        # o1 and o3 models work better with just the user message
        if model_name.startswith("o1") or model_name.startswith("o3"):
            messages = [
                HumanMessage(content=f"You are a GRC expert specializing in governance, risk, and compliance analysis. Your task is to create a comprehensive report on current GRC developments based on recent articles. Be extremely thorough in identifying ALL GRC-related content mentioned in the articles, including regulatory updates, compliance requirements, governance changes, and risk management developments.\n\n{prompt}")
            ]
        else:
            messages = [
                SystemMessage(content="You are a GRC expert specializing in governance, risk, and compliance analysis. Your task is to create a comprehensive report on current GRC developments based on recent articles. Be extremely thorough in identifying ALL GRC-related content mentioned in the articles, including regulatory updates, compliance requirements, governance changes, and risk management developments."),
                HumanMessage(content=prompt)
            ]
        
        response = await model.ainvoke(messages)
        
        # Extract the GRC report
        grc_report = response.content
        
        return {
            "grc_report": grc_report,
            "date": datetime.now().strftime("%Y-%m-%d"),
            "analyzed_article_count": len(articles),
            "regulations_identified": list(all_regulations),
            "frameworks_identified": list(all_frameworks),
            "industries_identified": list(all_industries),
            "regulatory_bodies_identified": list(all_regulatory_bodies)
        }
    except Exception as e:
        logger.error(f"Error during GRC analysis: {e}")
        return {
            "grc_report": f"# Error Generating GRC Intelligence Report\n\nAn error occurred during analysis: {str(e)}\n\n## Partial Data\n\nRegulations identified: {', '.join(all_regulations) if all_regulations else 'None'}\n\nFrameworks identified: {', '.join(all_frameworks) if all_frameworks else 'None'}\n\nIndustries identified: {', '.join(all_industries) if all_industries else 'None'}",
            "date": datetime.now().strftime("%Y-%m-%d"),
            "error": str(e)
        }

def analyze_article_grc_content(article: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze GRC content in an article
    
    Args:
        article: Article dictionary
        
    Returns:
        Dictionary with GRC details
    """
    # We'll skip the detailed article analysis and rely on the AI for comprehensive analysis
    return {
        "has_grc_content": True,  # Consider all articles potentially relevant for GRC analysis
        "regulations": [],
        "frameworks": [],
        "compliance_requirements": [],
        "industries": [],
        "regulatory_bodies": [],
        "risk_levels": []
    }