import re
import string
from typing import List, Dict, Any, Optional, Set

def extract_entities(text: str) -> Dict[str, Any]:
    """
    Extract GRC-related entities from text
    
    Args:
        text: Input text
        
    Returns:
        Dictionary with extracted entities
    """
    result = {
        "regulations": extract_regulations(text),
        "frameworks": extract_frameworks(text),
        "compliance_requirements": extract_compliance_requirements(text),
        "industries": extract_industries(text),
        "regulatory_bodies": extract_regulatory_bodies(text)
    }
    
    return result

def extract_regulations(text: str) -> List[str]:
    """Extract regulation references from text"""
    regulation_patterns = [
        # Common regulation patterns
        re.compile(r'SOX\s+(?:Section\s+)?(\d+)', re.IGNORECASE),
        re.compile(r'Sarbanes[-\s]?Oxley\s+(?:Section\s+)?(\d+)', re.IGNORECASE),
        re.compile(r'GDPR\s+(?:Article\s+)?(\d+)', re.IGNORECASE),
        re.compile(r'CCPA\s+(?:Section\s+)?(\d+)', re.IGNORECASE),
        re.compile(r'HIPAA\s+(?:Section\s+)?(\d+)', re.IGNORECASE),
        re.compile(r'PCI\s+DSS\s+(?:v)?(\d+\.\d+)', re.IGNORECASE),
        re.compile(r'SOC\s+(\d+)\s+Type\s+([I|II])', re.IGNORECASE),
        # General regulation pattern
        re.compile(r'([A-Z]{2,})\s+(?:Section|Article|Rule)\s+(\d+(?:\.\d+)?)', re.IGNORECASE)
    ]
    
    regulations = []
    
    for pattern in regulation_patterns:
        for match in pattern.finditer(text):
            if len(match.groups()) == 1:
                regulations.append(f"{match.group(0)}")
            elif len(match.groups()) == 2:
                regulations.append(f"{match.group(1)} {match.group(2)}")
    
    # Remove duplicates while preserving order
    seen = set()
    unique_regulations = []
    for item in regulations:
        if item not in seen:
            seen.add(item)
            unique_regulations.append(item)
    
    return unique_regulations

def extract_frameworks(text: str) -> List[str]:
    """Extract compliance framework references from text"""
    framework_patterns = [
        r'ISO\s+27001(?::\d{4})?',
        r'ISO\s+27002(?::\d{4})?',
        r'NIST\s+(?:CSF|Cybersecurity\s+Framework)',
        r'NIST\s+SP\s+800-\d+',
        r'COBIT\s+(?:\d+(?:\.\d+)?)?',
        r'COSO\s+(?:ERM|Internal\s+Control)?',
        r'ITIL\s+(?:v?\d+)?',
        r'SOC\s+\d+\s+Type\s+[I|II]',
        r'PCI\s+DSS\s+v?\d+\.\d+',
        r'FFIEC',
        r'BASEL\s+[I|II|III]',
        r'MiFID\s+[I|II]'
    ]
    
    frameworks = []
    
    for pattern in framework_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        frameworks.extend(matches)
    
    # Remove duplicates while preserving order
    seen = set()
    unique_frameworks = []
    for item in frameworks:
        if item not in seen:
            seen.add(item)
            unique_frameworks.append(item)
    
    return unique_frameworks

def extract_compliance_requirements(text: str) -> List[str]:
    """Extract compliance requirement keywords from text"""
    requirement_keywords = [
        "audit requirement", "compliance obligation", "regulatory requirement",
        "mandatory disclosure", "risk assessment", "internal controls",
        "data protection", "privacy policy", "incident response",
        "business continuity", "disaster recovery", "access controls",
        "segregation of duties", "documentation requirements",
        "retention policy", "monitoring controls", "reporting requirements"
    ]
    
    requirements = []
    
    for keyword in requirement_keywords:
        if re.search(keyword, text, re.IGNORECASE):
            requirements.append(keyword.title())
    
    return list(set(requirements))

def extract_industries(text: str) -> List[str]:
    """Extract industry references from text"""
    industry_patterns = [
        r'financial\s+services',
        r'banking',
        r'healthcare',
        r'pharmaceuticals',
        r'energy\s+sector',
        r'utilities',
        r'telecommunications',
        r'manufacturing',
        r'retail',
        r'technology',
        r'government',
        r'public\s+sector',
        r'education',
        r'insurance',
        r'real\s+estate'
    ]
    
    industries = []
    
    for pattern in industry_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        industries.extend([match.title() for match in matches])
    
    return list(set(industries))

def extract_regulatory_bodies(text: str) -> List[str]:
    """Extract regulatory body references from text"""
    regulatory_bodies = [
        "SEC", "PCAOB", "FINRA", "CFTC", "OCC", "FDIC", "Fed", "Federal Reserve",
        "FCA", "PRA", "ECB", "ESMA", "EBA", "EIOPA",
        "FDA", "CDC", "CMS", "HHS",
        "FTC", "DOJ", "CFPB",
        "NIST", "CISA", "DHS",
        "GDPR Authority", "ICO", "CNIL"
    ]
    
    found_bodies = []
    
    for body in regulatory_bodies:
        if re.search(r'\b' + re.escape(body) + r'\b', text, re.IGNORECASE):
            found_bodies.append(body)
    
    return found_bodies

def extract_risk_levels(text: str) -> List[Dict[str, Any]]:
    """Extract risk level assessments from text"""
    risk_patterns = [
        re.compile(r'(high|medium|low|critical)\s+risk', re.IGNORECASE),
        re.compile(r'risk\s+(?:level|rating):\s*(high|medium|low|critical)', re.IGNORECASE),
        re.compile(r'(significant|material|immaterial)\s+(?:risk|impact)', re.IGNORECASE)
    ]
    
    risks = []
    
    for pattern in risk_patterns:
        for match in pattern.finditer(text):
            risk_level = match.group(1).lower()
            risks.append({
                "level": risk_level.title(),
                "context": match.group(0)
            })
    
    return risks

def analyze_article_grc_content(article: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze an article to identify GRC-related content
    
    Args:
        article: Article dictionary
        
    Returns:
        Dictionary with GRC analysis
    """
    result = {
        "has_grc_content": False,
        "regulations": [],
        "frameworks": [],
        "compliance_requirements": [],
        "industries": [],
        "regulatory_bodies": [],
        "risk_levels": []
    }
    
    # Construct the text to analyze
    text = article.get("title", "") + "\n" + article.get("summary", "")
    if "content" in article and article["content"]:
        text += "\n" + article["content"]
    
    # Extract GRC entities
    entities = extract_entities(text)
    result.update(entities)
    
    # Extract risk levels
    result["risk_levels"] = extract_risk_levels(text)
    
    # GRC-related keywords for content detection
    grc_keywords = [
        "governance", "risk", "compliance", "audit", "regulatory", "framework",
        "policy", "control", "oversight", "accountability", "transparency",
        "ethics", "internal controls", "risk management", "compliance program",
        "regulatory compliance", "corporate governance", "board oversight",
        "risk assessment", "control environment", "monitoring", "reporting",
        "disclosure", "documentation", "procedures", "standards", "guidelines",
        "certification", "accreditation", "validation", "verification",
        "SOX", "GDPR", "HIPAA", "PCI", "ISO", "NIST", "COBIT", "COSO",
        "audit committee", "risk committee", "compliance officer",
        "chief risk officer", "chief compliance officer", "internal audit",
        "external audit", "regulatory examination", "supervisory review"
    ]
    
    # Check for GRC keywords
    title_lower = article.get("title", "").lower()
    content_lower = text.lower()
    
    for keyword in grc_keywords:
        if keyword.lower() in title_lower or keyword.lower() in content_lower:
            result["has_grc_content"] = True
            break
    
    # Additional checks for GRC content
    if result["regulations"] or result["frameworks"] or result["regulatory_bodies"]:
        result["has_grc_content"] = True
    
    if result["compliance_requirements"]:
        result["has_grc_content"] = True
    
    # Check for governance-related terms
    governance_terms = ["board", "director", "executive", "officer", "committee", "oversight"]
    if any(term in content_lower for term in governance_terms):
        result["has_grc_content"] = True
    
    return result
"""Legacy module (monolith)."""
