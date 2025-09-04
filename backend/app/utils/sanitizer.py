import re
from typing import Optional
import html

class HTMLSanitizer:
    """Basic HTML sanitization utilities"""
    
    @staticmethod
    def sanitize_input(text: str) -> str:
        """Sanitize user input to prevent XSS"""
        if not text:
            return ""
        
        # HTML escape special characters
        sanitized = html.escape(text)
        
        # Remove potential script tags and other dangerous content
        sanitized = re.sub(r'<script[^>]*>.*?</script>', '', sanitized, flags=re.IGNORECASE | re.DOTALL)
        sanitized = re.sub(r'javascript:', '', sanitized, flags=re.IGNORECASE)
        sanitized = re.sub(r'on\w+\s*=', '', sanitized, flags=re.IGNORECASE)
        
        return sanitized.strip()
    
    @staticmethod
    def validate_html_output(html_content: str) -> bool:
        """Basic validation of HTML output"""
        if not html_content:
            return False
        
        # Check for DOCTYPE declaration
        if not html_content.strip().startswith('<!DOCTYPE html>'):
            return False
        
        # Check for basic HTML structure
        required_tags = ['<html', '<head', '<body']
        for tag in required_tags:
            if tag not in html_content.lower():
                return False
        
        return True
    
    @staticmethod
    def clean_filename(filename: str) -> str:
        """Clean filename for safe storage"""
        if not filename:
            return "unknown"
        
        # Remove path separators and dangerous characters
        cleaned = re.sub(r'[^\w\-_.]', '_', filename)
        
        # Limit length
        if len(cleaned) > 100:
            name, ext = cleaned.rsplit('.', 1) if '.' in cleaned else (cleaned, '')
            cleaned = name[:95] + ('.' + ext if ext else '')
        
        return cleaned