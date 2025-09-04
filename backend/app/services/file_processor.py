import os
import tempfile
from typing import Optional
from pathlib import Path
import aiofiles
import structlog
from docx import Document
from fastapi import UploadFile, HTTPException
from ..core.config import settings

logger = structlog.get_logger()

class FileProcessor:
    MAX_SIZE = settings.max_upload_size  # 50MB
    ALLOWED_EXTENSIONS = ['.txt', '.md', '.docx']
    ALLOWED_MIME_TYPES = [
        'text/plain',
        'text/markdown',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    ]
    
    @staticmethod
    def validate_file(file: UploadFile) -> bool:
        """Validate file type and size"""
        try:
            # Check file size
            if hasattr(file, 'size') and file.size > FileProcessor.MAX_SIZE:
                raise HTTPException(status_code=413, detail="File too large")
            
            # Check file extension
            if file.filename:
                file_ext = Path(file.filename).suffix.lower()
                if file_ext not in FileProcessor.ALLOWED_EXTENSIONS:
                    raise HTTPException(
                        status_code=400, 
                        detail=f"File type not supported. Allowed: {', '.join(FileProcessor.ALLOWED_EXTENSIONS)}"
                    )
            
            # Check MIME type if available
            if file.content_type and file.content_type not in FileProcessor.ALLOWED_MIME_TYPES:
                logger.warning("MIME type not in allowed list", mime_type=file.content_type)
            
            return True
            
        except Exception as e:
            logger.error("File validation failed", filename=file.filename, error=str(e))
            raise
    
    @staticmethod
    async def process_file(file: UploadFile) -> str:
        """
        Extract text content from uploaded files
        
        Supports:
        - .txt files (plain text)
        - .md files (markdown)
        - .docx files (Word documents)
        """
        try:
            # Validate file first
            FileProcessor.validate_file(file)
            
            if not file.filename:
                raise HTTPException(status_code=400, detail="No filename provided")
            
            file_ext = Path(file.filename).suffix.lower()
            
            logger.info("Processing file", filename=file.filename, extension=file_ext, size=getattr(file, 'size', 'unknown'))
            
            # Read file content
            content = await file.read()
            
            # Reset file pointer for potential reuse
            await file.seek(0)
            
            if file_ext in ['.txt', '.md']:
                return await FileProcessor._process_text_file(content, file.filename)
            elif file_ext == '.docx':
                return await FileProcessor._process_docx_file(content, file.filename)
            else:
                raise HTTPException(status_code=400, detail=f"Unsupported file type: {file_ext}")
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error("File processing failed", filename=getattr(file, 'filename', 'unknown'), error=str(e))
            raise HTTPException(status_code=500, detail="Failed to process file")
    
    @staticmethod
    async def _process_text_file(content: bytes, filename: str) -> str:
        """Process plain text and markdown files"""
        try:
            # Try different encodings
            encodings = ['utf-8', 'utf-16', 'latin-1', 'cp1252']
            
            for encoding in encodings:
                try:
                    text_content = content.decode(encoding)
                    logger.info("Successfully decoded text file", filename=filename, encoding=encoding)
                    return text_content.strip()
                except UnicodeDecodeError:
                    continue
            
            # If all encodings fail, use utf-8 with error handling
            text_content = content.decode('utf-8', errors='replace')
            logger.warning("Used fallback encoding", filename=filename)
            return text_content.strip()
            
        except Exception as e:
            logger.error("Text file processing failed", filename=filename, error=str(e))
            raise
    
    @staticmethod
    async def _process_docx_file(content: bytes, filename: str) -> str:
        """Process Word documents (.docx)"""
        try:
            # Create temporary file
            with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as tmp_file:
                tmp_file.write(content)
                tmp_file_path = tmp_file.name
            
            try:
                # Load document with python-docx
                doc = Document(tmp_file_path)
                
                # Extract text from all paragraphs
                text_parts = []
                for paragraph in doc.paragraphs:
                    text = paragraph.text.strip()
                    if text:  # Only add non-empty paragraphs
                        text_parts.append(text)
                
                # Extract text from tables
                for table in doc.tables:
                    for row in table.rows:
                        row_text = []
                        for cell in row.cells:
                            cell_text = cell.text.strip()
                            if cell_text:
                                row_text.append(cell_text)
                        if row_text:
                            text_parts.append(" | ".join(row_text))
                
                extracted_text = "\n\n".join(text_parts)
                
                logger.info("Successfully processed DOCX", filename=filename, paragraphs=len(doc.paragraphs), tables=len(doc.tables))
                return extracted_text
                
            finally:
                # Clean up temporary file
                try:
                    os.unlink(tmp_file_path)
                except:
                    pass
                    
        except Exception as e:
            logger.error("DOCX processing failed", filename=filename, error=str(e))
            raise
    
    @staticmethod
    async def save_temp_file(content: str, session_id: str, filename: str) -> str:
        """Save processed content to temporary file"""
        try:
            # Create temp directory structure
            temp_dir = Path(tempfile.gettempdir()) / "ai-html-builder" / "uploads" / session_id
            temp_dir.mkdir(parents=True, exist_ok=True)
            
            # Create unique filename
            timestamp = int(datetime.utcnow().timestamp())
            safe_filename = f"{timestamp}_{filename}.txt"
            temp_file_path = temp_dir / safe_filename
            
            # Save content
            async with aiofiles.open(temp_file_path, 'w', encoding='utf-8') as f:
                await f.write(content)
            
            logger.info("Temp file saved", path=str(temp_file_path))
            return str(temp_file_path)
            
        except Exception as e:
            logger.error("Failed to save temp file", session_id=session_id, filename=filename, error=str(e))
            raise
    
    @staticmethod
    async def cleanup_session_files(session_id: str):
        """Clean up temporary files for a session"""
        try:
            session_dir = Path(tempfile.gettempdir()) / "ai-html-builder" / "uploads" / session_id
            if session_dir.exists():
                import shutil
                shutil.rmtree(session_dir)
                logger.info("Session files cleaned up", session_id=session_id)
        except Exception as e:
            logger.error("Failed to cleanup session files", session_id=session_id, error=str(e))
    
    @staticmethod
    def get_file_info(file: UploadFile) -> dict:
        """Get file information"""
        return {
            "name": file.filename or "unknown",
            "size": getattr(file, 'size', 0),
            "type": file.content_type or "unknown"
        }

# Add missing import
from datetime import datetime