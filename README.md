# GRCInsight

<div align="center">
  <img src="assets/images/logo.png" alt="GRCInsight Logo" width="400"/>
</div>

Automated governance, risk & compliance intelligence that monitors RSS feeds and generates GRC reports using AI analysis.

[![Latest GRC Report](https://img.shields.io/badge/View-Latest%20Report-blue)](https://ricomanifesto.github.io/GRCInsight/)

## Features

- Monitors security RSS feeds for GRC-related content
- Extracts and correlates regulatory mentions and frameworks
- Generates reports with executive summaries, regulatory updates, compliance requirements, and risk management developments
- Integrates with [SentryDigest](https://github.com/ricomanifesto/SentryDigest) for automated analysis triggers

## Architecture

**LangGraph**: Orchestrates workflow state and conditional logic  
**Model Context Protocol (MCP)**: Standardized RSS feed interface  
**LangChain**: AI model integration and text processing  
**OpenAI GPT**: Content analysis and report generation

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Add OpenAI API key:
   ```bash
   echo "OPENAI_API_KEY=your-api-key-here" > .env
   ```

3. Configure feeds and output paths in `config/config.json`

## Usage

```bash
python main.py
```

Fetches articles, filters for GRC content, analyzes governance/risk/compliance developments, and saves reports to `index.md`.