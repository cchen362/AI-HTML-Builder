"""
Artifact Manager

Manages HTML artifacts with version tracking and change detection for
the conversational AI HTML builder. Supports Claude Artifacts-style
artifact management with intelligent version control.
"""

from typing import Dict, List, Optional, NamedTuple
from datetime import datetime
from dataclasses import dataclass
import structlog
import hashlib
import difflib

logger = structlog.get_logger()

@dataclass
class HTMLArtifact:
    """Represents an HTML artifact with metadata and version information"""
    id: str
    session_id: str
    html_content: str
    title: str
    content_type: str  # 'landing-page', 'article', 'portfolio', etc.
    version: int
    created_at: datetime
    updated_at: datetime
    metadata: Dict[str, any]
    hash: str
    changes_from_previous: List[str] = None

class ArtifactManager:
    """
    Manages HTML artifacts with intelligent version tracking and change detection.
    Provides Claude Artifacts-style artifact management capabilities.
    """
    
    def __init__(self):
        # In-memory storage for artifacts (could be extended to persist in Redis)
        self.artifacts: Dict[str, List[HTMLArtifact]] = {}  # session_id -> [artifacts]
        self.current_artifacts: Dict[str, HTMLArtifact] = {}  # session_id -> current artifact
        
        logger.info("Artifact manager initialized")
    
    def create_artifact(
        self, 
        session_id: str, 
        html_content: str, 
        metadata: Dict[str, any]
    ) -> HTMLArtifact:
        """Create a new HTML artifact"""
        try:
            # Generate artifact ID and hash
            artifact_id = self._generate_artifact_id(session_id, html_content)
            content_hash = self._generate_content_hash(html_content)
            
            # Determine version number
            version = 1
            if session_id in self.artifacts:
                version = len(self.artifacts[session_id]) + 1
            
            # Extract title from metadata or HTML
            title = metadata.get('title', self._extract_title_from_html(html_content))
            content_type = metadata.get('type', 'custom')
            
            # Create artifact
            artifact = HTMLArtifact(
                id=artifact_id,
                session_id=session_id,
                html_content=html_content,
                title=title,
                content_type=content_type,
                version=version,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                metadata=metadata,
                hash=content_hash
            )
            
            # Store artifact
            if session_id not in self.artifacts:
                self.artifacts[session_id] = []
            
            self.artifacts[session_id].append(artifact)
            self.current_artifacts[session_id] = artifact
            
            logger.info(
                "Artifact created",
                session_id=session_id,
                artifact_id=artifact_id,
                version=version,
                title=title,
                content_type=content_type
            )
            
            return artifact
            
        except Exception as e:
            logger.error("Failed to create artifact", session_id=session_id, error=str(e))
            raise
    
    def update_artifact(
        self, 
        session_id: str, 
        html_content: str, 
        changes_summary: List[str],
        metadata: Dict[str, any]
    ) -> HTMLArtifact:
        """Update existing artifact with new content and track changes"""
        try:
            # Get current artifact
            current = self.current_artifacts.get(session_id)
            if not current:
                # No existing artifact, create new one
                return self.create_artifact(session_id, html_content, metadata)
            
            # Check if content actually changed
            new_hash = self._generate_content_hash(html_content)
            if new_hash == current.hash:
                logger.info("No content changes detected", session_id=session_id)
                return current
            
            # Detect specific changes
            detected_changes = self._detect_changes(current.html_content, html_content)
            all_changes = changes_summary + detected_changes
            
            # Create new artifact version
            new_artifact = HTMLArtifact(
                id=self._generate_artifact_id(session_id, html_content),
                session_id=session_id,
                html_content=html_content,
                title=metadata.get('title', current.title),
                content_type=metadata.get('type', current.content_type),
                version=current.version + 1,
                created_at=current.created_at,
                updated_at=datetime.utcnow(),
                metadata={**current.metadata, **metadata},
                hash=new_hash,
                changes_from_previous=all_changes
            )
            
            # Store updated artifact
            self.artifacts[session_id].append(new_artifact)
            self.current_artifacts[session_id] = new_artifact
            
            logger.info(
                "Artifact updated",
                session_id=session_id,
                version=new_artifact.version,
                changes_count=len(all_changes),
                changes=all_changes[:3]  # Log first 3 changes
            )
            
            return new_artifact
            
        except Exception as e:
            logger.error("Failed to update artifact", session_id=session_id, error=str(e))
            raise
    
    def get_current_artifact(self, session_id: str) -> Optional[HTMLArtifact]:
        """Get the current artifact for a session"""
        return self.current_artifacts.get(session_id)
    
    def get_artifact_history(self, session_id: str) -> List[HTMLArtifact]:
        """Get all artifacts for a session"""
        return self.artifacts.get(session_id, [])
    
    def get_artifact_by_version(self, session_id: str, version: int) -> Optional[HTMLArtifact]:
        """Get a specific version of an artifact"""
        artifacts = self.artifacts.get(session_id, [])
        for artifact in artifacts:
            if artifact.version == version:
                return artifact
        return None
    
    def rollback_to_version(self, session_id: str, version: int) -> Optional[HTMLArtifact]:
        """Rollback to a previous version of an artifact"""
        try:
            target_artifact = self.get_artifact_by_version(session_id, version)
            if not target_artifact:
                logger.warning("Artifact version not found for rollback", session_id=session_id, version=version)
                return None
            
            # Create new artifact based on the target version
            rollback_metadata = {
                **target_artifact.metadata,
                'is_rollback': True,
                'rollback_from_version': self.current_artifacts[session_id].version,
                'rollback_to_version': version
            }
            
            new_artifact = self.create_artifact(
                session_id,
                target_artifact.html_content,
                rollback_metadata
            )
            
            logger.info("Artifact rolled back", session_id=session_id, from_version=rollback_metadata['rollback_from_version'], to_version=version)
            
            return new_artifact
            
        except Exception as e:
            logger.error("Failed to rollback artifact", session_id=session_id, version=version, error=str(e))
            raise
    
    def _generate_artifact_id(self, session_id: str, html_content: str) -> str:
        """Generate unique artifact ID"""
        timestamp = datetime.utcnow().isoformat()
        content_hash = self._generate_content_hash(html_content)
        return f"{session_id}_{timestamp}_{content_hash[:8]}"
    
    def _generate_content_hash(self, html_content: str) -> str:
        """Generate hash for HTML content"""
        return hashlib.md5(html_content.encode('utf-8')).hexdigest()
    
    def _extract_title_from_html(self, html_content: str) -> str:
        """Extract title from HTML content"""
        import re
        title_match = re.search(r'<title>(.*?)</title>', html_content, re.IGNORECASE)
        return title_match.group(1) if title_match else "Generated Page"
    
    def _detect_changes(self, old_html: str, new_html: str) -> List[str]:
        """Detect specific changes between two HTML versions"""
        try:
            # Simplified change detection - could be enhanced with more sophisticated diff analysis
            changes = []
            
            # Check for major structural changes
            old_lines = old_html.split('\n')
            new_lines = new_html.split('\n')
            
            # Use difflib to detect changes
            diff = list(difflib.unified_diff(old_lines, new_lines, n=0))
            
            # Analyze diff for meaningful changes
            added_lines = [line[1:].strip() for line in diff if line.startswith('+') and not line.startswith('+++')]
            removed_lines = [line[1:].strip() for line in diff if line.startswith('-') and not line.startswith('---')]
            
            # Categorize changes
            if any('background' in line.lower() or 'color' in line.lower() for line in added_lines):
                changes.append("Updated color scheme and styling")
            
            if any('font' in line.lower() or 'text' in line.lower() for line in added_lines):
                changes.append("Modified typography and text styling")
            
            if any('nav' in line.lower() or 'header' in line.lower() for line in added_lines):
                changes.append("Enhanced navigation and header design")
            
            if any('section' in line.lower() or 'div' in line.lower() for line in added_lines):
                changes.append("Restructured content layout")
            
            if any('animation' in line.lower() or 'transition' in line.lower() for line in added_lines):
                changes.append("Added animations and interactions")
            
            if any('@media' in line.lower() for line in added_lines):
                changes.append("Improved responsive design")
            
            # If no specific changes detected, provide generic summary
            if not changes and (added_lines or removed_lines):
                changes.append(f"Updated design elements and content structure")
            
            return changes[:5]  # Limit to 5 most important changes
            
        except Exception as e:
            logger.warning("Failed to detect specific changes", error=str(e))
            return ["Content updated"]
    
    def get_session_stats(self, session_id: str) -> Dict[str, any]:
        """Get statistics for a session's artifacts"""
        artifacts = self.artifacts.get(session_id, [])
        current = self.current_artifacts.get(session_id)
        
        if not artifacts:
            return {
                "total_versions": 0,
                "current_version": 0,
                "session_duration": None,
                "content_types": [],
                "total_changes": 0
            }
        
        # Calculate stats
        total_changes = sum(len(artifact.changes_from_previous or []) for artifact in artifacts)
        content_types = list(set(artifact.content_type for artifact in artifacts))
        session_start = min(artifact.created_at for artifact in artifacts)
        session_duration = datetime.utcnow() - session_start
        
        return {
            "total_versions": len(artifacts),
            "current_version": current.version if current else 0,
            "session_duration": session_duration.total_seconds(),
            "content_types": content_types,
            "total_changes": total_changes,
            "current_title": current.title if current else None,
            "current_type": current.content_type if current else None
        }


# Global artifact manager instance
artifact_manager = ArtifactManager()