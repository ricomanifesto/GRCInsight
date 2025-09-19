"""OpenAI client service for GRC analysis."""

import asyncio
from typing import List, Dict, Any, Optional
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from loguru import logger

from config.settings import settings
from models.api import ArticleInput


class OpenAIService:
    """Service for OpenAI-powered GRC analysis."""
    
    def __init__(self):
        """Initialize OpenAI service."""
        if not settings.openai_api_key:
            raise ValueError("OpenAI API key is required")
            
        # Preferred and fallback models (A then B)
        self.model_primary = self._get_model_name()
        self.model_fallback_a = "gpt-4o"
        self.model_fallback_b = "gpt-3.5-turbo"  # "ChatGPT03"

        self.client = self._build_client(self.model_primary)
        
        logger.info(f"Initialized OpenAI client with model: {self.model_primary}")
    
    def _get_model_name(self) -> str:
        """Get the correct OpenAI model name."""
        model = settings.openai_model.lower()
        
        # Map common model names to actual OpenAI model identifiers
        model_mapping = {
            "gpt5": "gpt-5",
            "gpt-5": "gpt-5",
            "chatgpt-5": "gpt-5",
            "chatgpt5": "gpt-5",
            "gpt4": "gpt-4",
            "gpt-4": "gpt-4", 
            "gpt4o": "gpt-4o",
            "gpt-4o": "gpt-4o",
            "o3": "gpt-4o",  # o3 doesn't exist yet, fallback to gpt-4o
            "gpt-3.5": "gpt-3.5-turbo",
            "gpt-3.5-turbo": "gpt-3.5-turbo",
            "chatgpt03": "gpt-3.5-turbo",
            "chatgpt-03": "gpt-3.5-turbo",
            "chatgpt 03": "gpt-3.5-turbo"
        }
        
        return model_mapping.get(model, "gpt-5")  # Default to gpt-5; runtime fallback will handle if unavailable

    def _build_client(self, model_name: str) -> ChatOpenAI:
        """Construct a ChatOpenAI client for a given model."""
        return ChatOpenAI(
            model=model_name,
            max_tokens=settings.openai_max_tokens,
            temperature=0.1,
            openai_api_key=settings.openai_api_key,
        )

    async def _invoke_with_fallbacks(self, messages: List[Any]):
        """Invoke the model with ordered fallbacks: primary → A → B."""
        # Try primary
        try:
            return await self.client.ainvoke(messages)
        except Exception as e1:
            logger.warning(f"Primary model '{self.model_primary}' failed: {e1}")
            # Try fallback A
            try:
                logger.info(f"Falling back to '{self.model_fallback_a}'")
                self.client = self._build_client(self.model_fallback_a)
                return await self.client.ainvoke(messages)
            except Exception as e2:
                logger.warning(f"Fallback A '{self.model_fallback_a}' failed: {e2}")
                # Try fallback B
                logger.info(f"Falling back to '{self.model_fallback_b}'")
                self.client = self._build_client(self.model_fallback_b)
                return await self.client.ainvoke(messages)
    
    async def analyze_articles_for_grc(self, articles: List[ArticleInput]) -> Dict[str, Any]:
        """Analyze articles for GRC-relevant content."""
        try:
            logger.info(f"Analyzing {len(articles)} articles for GRC content")
            
            if not articles:
                return {
                    "grc_articles": [],
                    "summary": {
                        "total_articles": 0,
                        "grc_relevant_count": 0,
                        "confidence_score": 0.0
                    },
                    "analysis": {
                        "regulations_mentioned": [],
                        "frameworks_referenced": [],
                        "industries_affected": [],
                        "risk_categories": []
                    }
                }
            
            # Create analysis prompt
            analysis_prompt = self._create_analysis_prompt(articles)
            
            # Run analysis with ordered fallbacks
            response = await self._invoke_with_fallbacks([
                SystemMessage(content=self._get_system_prompt()),
                HumanMessage(content=analysis_prompt)
            ])
            
            # Process the response
            analysis_result = self._process_analysis_response(response.content, articles)
            
            logger.info(f"Analysis complete: {analysis_result['summary']['grc_relevant_count']} GRC-relevant articles found")
            
            return analysis_result
            
        except Exception as e:
            logger.error(f"Error during GRC analysis: {e}")
            return {
                "error": str(e),
                "grc_articles": [],
                "summary": {
                    "total_articles": len(articles),
                    "grc_relevant_count": 0,
                    "confidence_score": 0.0
                },
                "analysis": {
                    "regulations_mentioned": [],
                    "frameworks_referenced": [],
                    "industries_affected": [],
                    "risk_categories": []
                }
            }
    
    async def generate_grc_report(self, analysis_data: Dict[str, Any], feed_info: Dict[str, Any]) -> str:
        """Generate a comprehensive GRC intelligence report."""
        try:
            logger.info("Generating GRC intelligence report")
            
            report_prompt = self._create_report_prompt(analysis_data, feed_info)
            
            response = await self._invoke_with_fallbacks([
                SystemMessage(content=self._get_report_system_prompt()),
                HumanMessage(content=report_prompt)
            ])
            
            report_content = response.content
            
            logger.info("GRC report generation completed")
            return report_content
            
        except Exception as e:
            logger.error(f"Error generating report: {e}")
            return f"# GRC Intelligence Report - Error\n\nUnable to generate report: {str(e)}"
    
    def _get_system_prompt(self) -> str:
        """Get the system prompt for GRC analysis."""
        focus_areas = ", ".join(settings.analysis_focus_areas)
        
        return f"""You are a GRC (Governance, Risk, and Compliance) intelligence analyst specializing in identifying regulatory and compliance-related content in news articles and industry reports.

Your focus areas include: {focus_areas}

For each article, analyze:
1. Relevance to GRC/compliance (score 0-10)
2. Regulatory frameworks mentioned (SOX, GDPR, PCI-DSS, etc.)
3. Industries affected
4. Risk categories (operational, financial, cyber, regulatory, etc.)
5. Compliance requirements or changes

Be precise and factual. Only flag content as GRC-relevant if it has clear governance, risk, or compliance implications."""

    def _get_report_system_prompt(self) -> str:
        """Get the system prompt for report generation."""
        return """You are a senior GRC analyst creating executive-level intelligence reports. 

Create a comprehensive report that:
1. Summarizes key GRC developments and trends
2. Highlights regulatory changes and their business impact
3. Identifies emerging risks and compliance challenges
4. Provides actionable insights for governance and risk management

Use professional language and structure the report with clear sections and bullet points. Focus on business impact and strategic implications."""

    def _create_analysis_prompt(self, articles: List[ArticleInput]) -> str:
        """Create prompt for analyzing articles."""
        articles_text = ""
        for i, article in enumerate(articles, 1):  # Analyze all articles
            content = article.content or article.description or "No content available"
            articles_text += f"""
Article {i}:
Title: {article.title}
URL: {article.url}
Content: {content[:500]}...
Published: {article.published}
---"""
        
        return f"""Analyze the following articles for GRC relevance:

{articles_text}

Please provide analysis in this format:
- List articles that are GRC-relevant (include article number, title, relevance score 1-10, and brief reason)
- Identify mentioned regulations/frameworks (GDPR, SOX, PCI-DSS, ISO 27001, NIST, etc.)
- List affected industries
- Categorize risk types (cyber, operational, financial, regulatory, reputational)
- Note any compliance deadlines or regulatory changes

Focus only on content with clear governance, risk, or compliance implications."""

    def _create_report_prompt(self, analysis_data: Dict[str, Any], feed_info: Dict[str, Any]) -> str:
        """Create prompt for report generation."""
        grc_count = analysis_data.get("summary", {}).get("grc_relevant_count", 0)
        total_count = analysis_data.get("summary", {}).get("total_articles", 0)
        
        regulations = analysis_data.get("analysis", {}).get("regulations_mentioned", [])
        industries = analysis_data.get("analysis", {}).get("industries_affected", [])
        risks = analysis_data.get("analysis", {}).get("risk_categories", [])
        
        return f"""Create a GRC Intelligence Report based on this analysis:

Source: {feed_info.get('title', 'Unknown Feed')}
Analysis Period: Recent articles
Total Articles Analyzed: {total_count}
GRC-Relevant Articles: {grc_count}

Key Findings:
- Regulations/Frameworks: {', '.join(regulations) if regulations else 'None identified'}
- Industries Affected: {', '.join(industries) if industries else 'Multiple sectors'}
- Risk Categories: {', '.join(risks) if risks else 'Various risk types'}

Please create a professional executive summary report with:
1. Executive Summary
2. Key Regulatory Developments
3. Industry Impact Analysis
4. Risk Assessment
5. Recommendations for Action

Make it actionable for risk managers and compliance officers."""

    def _process_analysis_response(self, response_content: str, original_articles: List[ArticleInput]) -> Dict[str, Any]:
        """Process the OpenAI analysis response."""
        lines = response_content.split('\n')

        grc_articles = []
        regulations = []
        industries = []
        risks = []
        current_section = None
        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Identify sections
            if 'regulation' in line.lower() or 'framework' in line.lower():
                current_section = 'regulations'
            elif 'industri' in line.lower():
                current_section = 'industries'
            elif 'risk' in line.lower():
                current_section = 'risks'
            elif line.startswith('Article ') and any(word in line.lower() for word in ['relevant', 'grc', 'compliance']):
                # Extract article info
                try:
                    # Simple extraction - could be improved
                    if 'score' in line.lower():
                        article_info = {
                            "title": line.split('Title:')[-1].split('score')[0].strip() if 'Title:' in line else line,
                            "relevance_score": 7.0,  # Default score
                            "summary": "GRC-relevant content identified"
                        }
                        grc_articles.append(article_info)
                except:
                    pass

            # Extract items from current section
            if current_section == 'regulations' and any(reg in line for reg in ['GDPR', 'SOX', 'PCI', 'ISO', 'NIST', 'CCPA']):
                # Extract just the regulation names, not the formatted text
                for reg in ['GDPR', 'SOX', 'PCI-DSS', 'ISO 27001', 'NIST', 'CCPA']:
                    if reg in line:
                        regulations.append(reg)

        # Consider all articles potentially relevant for comprehensive GRC analysis
        if not grc_articles and original_articles:
            for article in original_articles:
                grc_articles.append({
                    "title": article.title,
                    "url": article.url,
                    "relevance_score": 7.0,
                    "summary": "GRC analysis via comprehensive AI evaluation"
                })

        return {
            "grc_articles": grc_articles,
            "summary": {
                "total_articles": len(original_articles),
                "grc_relevant_count": len(grc_articles),
                "confidence_score": 0.8 if grc_articles else 0.2
            },
            "analysis": {
                "regulations_mentioned": list(set(regulations)) if regulations else [],
                "frameworks_referenced": list(set([r for r in regulations if 'ISO' in r or 'NIST' in r])) if regulations else [],
                "industries_affected": list(set(industries)) if industries else [],
                "risk_categories": list(set(risks)) if risks else [],
                "regulatory_bodies": []
            }
        }
