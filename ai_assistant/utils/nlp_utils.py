
"""
NLP Utilities for AI Assistant
Provides shared utility functions for common NLP tasks like text extraction, chunking, and simple QA.
"""

import re
import json
from typing import Dict, Any, List, Optional, Tuple, Set
import numpy as np
from pathlib import Path

# Assuming FinancialCategory, RiskLevel, etc. are defined elsewhere or passed as strings

def extract_market_indicators(text: str) -> Dict[str, Any]:
    """Extract market indicators from text"""
    indicators = {
        "mentions_earnings": bool(re.search(r'\bearnings?\b', text, re.IGNORECASE)),
        "mentions_revenue": bool(re.search(r'\brevenue\b', text, re.IGNORECASE)),
        "mentions_guidance": bool(re.search(r'\bguidance\b', text, re.IGNORECASE)),
        "mentions_outlook": bool(re.search(r'\boutlook\b', text, re.IGNORECASE)),
        "mentions_growth": bool(re.search(r'\bgrowth\b', text, re.IGNORECASE)),
        "mentions_decline": bool(re.search(r'\bdecline\b', text, re.IGNORECASE)),
        "has_price_target": bool(re.search(r'price target|target price', text, re.IGNORECASE)),
        "has_rating_change": bool(re.search(r'upgrade|downgrade|rating', text, re.IGNORECASE)),
        "mentions_volatility": bool(re.search(r'\bvolatility\b', text, re.IGNORECASE)),
        "mentions_volume": bool(re.search(r'\bvolume\b', text, re.IGNORECASE))
    }
    
    # Extract numerical indicators
    percentages = re.findall(r'(\d+(?:\.\d+)?)%', text)
    if percentages:
        indicators["percentages"] = [float(p) for p in percentages]
    
    prices = re.findall(r'\$(\d+(?:\.\d{2})?)', text)
    if prices:
        indicators["prices"] = [float(p) for p in prices]
    
    return indicators


def extract_key_phrases(text: str) -> List[str]:
    """Extract key financial phrases from text"""
    # Simple keyword extraction based on financial terms
    financial_keywords = [
        "earnings beat", "earnings miss", "revenue growth", "margin expansion",
        "cost cutting", "market share", "competitive advantage", "regulatory approval",
        "merger", "acquisition", "dividend increase", "share buyback",
        "guidance raised", "guidance lowered", "analyst upgrade", "analyst downgrade"
    ]
    
    key_phrases = []
    text_lower = text.lower()
    
    for phrase in financial_keywords:
        if phrase in text_lower:
            key_phrases.append(phrase)
    
    return key_phrases[:10]  # Limit to top 10


def extract_financial_indicators(text: str, financial_terms: List[str]) -> Dict[str, Any]:
    """Extract financial indicators from text"""
    indicators = {
        "mentions_earnings": bool(re.search(r'\bearnings?\b', text, re.IGNORECASE)),
        "mentions_revenue": bool(re.search(r'\brevenue\b', text, re.IGNORECASE)),
        "mentions_profit": bool(re.search(r'\bprofit\b', text, re.IGNORECASE)),
        "mentions_loss": bool(re.search(r'\bloss\b', text, re.IGNORECASE)),
        "mentions_growth": bool(re.search(r'\bgrowth\b', text, re.IGNORECASE)),
        "mentions_decline": bool(re.search(r'\bdecline\b', text, re.IGNORECASE)),
        "has_percentages": bool(re.search(r'\d+\.?\d*%', text)),
        "has_dollar_amounts": bool(re.search(r'\$\d+', text)),
        "financial_term_count": len([term for term in financial_terms 
                                   if term.lower() in text.lower()])
    }
    return indicators


def extract_tickers(text: str) -> List[Dict[str, Any]]:
    """Extract stock ticker symbols from text"""
    # Pattern for stock tickers (1-5 uppercase letters)
    ticker_pattern = r'\b[A-Z]{1,5}\b'
    matches = re.finditer(ticker_pattern, text)
    
    tickers = []
    for match in matches:
        ticker_text = match.group()
        # Filter out common words that might match the pattern
        if ticker_text not in ['THE', 'AND', 'OR', 'FOR', 'WITH', 'FROM', 'TO', 'IN', 'ON', 'AT']:
            tickers.append({
                "text": ticker_text,
                "label": "TICKER",
                "confidence": 0.8,
                "start": match.start(),
                "end": match.end()
            })
    
    return tickers


def extract_financial_terms(text: str, financial_terms_list: List[str]) -> List[Dict[str, Any]]:
    """Extract financial terms from text"""
    financial_terms = []
    text_lower = text.lower()
    
    for term in financial_terms_list:
        pattern = r'\b' + re.escape(term.lower()) + r'\b'
        matches = re.finditer(pattern, text_lower)
        
        for match in matches:
            financial_terms.append({
                "text": text[match.start():match.end()],
                "label": "FIN_TERM",
                "confidence": 0.7,
                "start": match.start(),
                "end": match.end()
            })
    
    return financial_terms


def extract_entity_relationships(entities: List[Dict[str, Any]], text: str) -> List[Dict[str, Any]]:
    """Extract relationships between entities"""
    relationships = []
    
    # Simple relationship extraction based on proximity
    for i, entity1 in enumerate(entities):
        for j, entity2 in enumerate(entities[i+1:], i+1):
            # Check if entities are close to each other
            distance = abs(entity1["start"] - entity2["start"])
            if distance < 100:  # Within 100 characters
                relationships.append({
                    "entity1": entity1["text"],
                    "entity2": entity2["text"],
                    "type": "proximity",
                    "distance": distance,
                    "confidence": max(0.1, 1.0 - distance / 100.0)
                })
    
    return relationships


def chunk_text(text: str, max_length: int) -> List[str]:
    """Split text into chunks of maximum length"""
    words = text.split()
    chunks = []
    current_chunk = []
    current_length = 0
    
    for word in words:
        word_length = len(word) + 1  # +1 for space
        if current_length + word_length > max_length and current_chunk:
            chunks.append(" ".join(current_chunk))
            current_chunk = [word]
            current_length = word_length
        else:
            current_chunk.append(word)
            current_length += word_length
    
    if current_chunk:
        chunks.append(" ".join(current_chunk))
    
    return chunks


def extractive_summarization(text: str, max_length: int, financial_terms: List[str]) -> str:
    """Simple extractive summarization as fallback"""
    sentences = text.split('. ')
    if len(sentences) <= 3:
        return text
    
    # Score sentences based on financial terms
    scored_sentences = []
    for sentence in sentences:
        score = 0
        for term in financial_terms:
            if term.lower() in sentence.lower():
                score += 1
        scored_sentences.append((sentence, score))
    
    # Sort by score and take top sentences
    scored_sentences.sort(key=lambda x: x[1], reverse=True)
    top_sentences = scored_sentences[:3]
    
    # Reconstruct summary
    summary = '. '.join([s[0] for s in top_sentences])
    
    # Truncate if too long
    if len(summary) > max_length:
        summary = summary[:max_length-3] + "..."
    
    return summary


def extract_key_points(text: str, summary: str) -> List[str]:
    """Extract key points from text and summary"""
    key_points = []
    
    # Look for bullet points or numbered lists
    bullet_pattern = r'[•\-\*]\s*(.+)'
    number_pattern = r'\d+\.\s*(.+)'
    
    for pattern in [bullet_pattern, number_pattern]:
        matches = re.findall(pattern, text)
        key_points.extend(matches[:5])  # Limit to 5 points
    
    # If no structured points found, extract from summary
    if not key_points:
        sentences = summary.split('. ')
        key_points = [s.strip() for s in sentences[:3] if len(s.strip()) > 10]
    
    return key_points[:5]  # Maximum 5 key points


def simple_qa(question: str, context: str) -> Tuple[str, float, int, int]:
    """Simple keyword-based question answering as fallback"""
    question_words = set(question.lower().split())
    context_lower = context.lower()
    
    # Find sentences containing question keywords
    sentences = context.split('. ')
    best_sentence = ""
    best_score = 0
    best_start = 0
    best_end = 0
    
    for sentence in sentences:
        sentence_words = set(sentence.lower().split())
        overlap = len(question_words.intersection(sentence_words))
        
        if overlap > best_score:
            best_score = overlap
            best_sentence = sentence.strip()
            best_start = context.find(sentence)
            best_end = best_start + len(sentence)
    
    if best_sentence:
        confidence = min(0.8, best_score / len(question_words))
        return best_sentence, confidence, best_start, best_end
    else:
        return "No answer found", 0.1, 0, 0
