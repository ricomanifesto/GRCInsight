import logging
import os
import re
import json
from typing import List, Dict, Any
from datetime import datetime

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

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
    api_key = os.getenv("ANTHROPIC_API_KEY")
    model_name = config.get("analysis", {}).get("model", "claude-opus-4-6")
    temperature = config.get("analysis", {}).get("temperature", 1)

    if not api_key:
        logger.error("No Anthropic API key provided")
        return {
            "grc_report": "# Error: No Anthropic API Key\n\nPlease set the ANTHROPIC_API_KEY environment variable.",
            "date": datetime.now().strftime("%Y-%m-%d"),
            "error": "No API key"
        }

    model = ChatAnthropic(
        anthropic_api_key=api_key,
        model=model_name,
        temperature=temperature,
        max_tokens=16000,
        thinking={"type": "enabled", "budget_tokens": 10000},
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

    # Estimate prompt length for logging
    estimated_chars = len(prompt)
    logger.info(f"Estimated prompt length: {estimated_chars} characters (~{estimated_chars // 4} tokens)")

    # Call the AI model
    try:
        messages = [
            SystemMessage(content="You are a GRC expert specializing in governance, risk, and compliance analysis. Your task is to create a comprehensive report on current GRC developments based on recent articles. Be extremely thorough in identifying ALL GRC-related content mentioned in the articles, including regulatory updates, compliance requirements, governance changes, and risk management developments."),
            HumanMessage(content=prompt)
        ]

        response = await model.ainvoke(messages)

        # Extract text content, handling extended thinking response format
        content = response.content
        if isinstance(content, str):
            grc_report = content
        elif isinstance(content, list):
            texts = [block["text"] for block in content if isinstance(block, dict) and block.get("type") == "text"]
            grc_report = "\n".join(texts)
        else:
            grc_report = str(content)

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
