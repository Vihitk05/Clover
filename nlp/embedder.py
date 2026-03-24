# nlp/embedder.py
import numpy as np
from typing import List, Dict, Any
import logging
import hashlib

logger = logging.getLogger(__name__)

class ProfileEmbedder:
    """Handles embedding of user profiles using local Sentence Transformers"""
    
    def __init__(self, use_local_model: bool = True, persist_directory: str = "./chroma_db"):
        """
        Initialize ProfileEmbedder
        
        Args:
            use_local_model: If True, use local Sentence Transformers (free, no API)
            persist_directory: Directory to persist ChromaDB data
        """
        self.use_local_model = use_local_model
        self.model = None
        self.embedding_dim = 384  # all-MiniLM-L6-v2 dimension
        
        # Initialize local model
        if use_local_model:
            try:
                from sentence_transformers import SentenceTransformer
                self.model = SentenceTransformer('all-MiniLM-L6-v2')
                logger.info("Loaded local Sentence Transformer model")
            except ImportError:
                logger.warning("sentence-transformers not installed. Install with: pip install sentence-transformers")
                logger.info("Falling back to TF-IDF mode")
                self.use_local_model = False
                self._init_tfidf()
            except Exception as e:
                logger.error(f"Error loading model: {e}")
                self.use_local_model = False
                self._init_tfidf()
        else:
            self._init_tfidf()
        
        # Initialize ChromaDB
        try:
            import chromadb
            self.chroma_client = chromadb.PersistentClient(path=persist_directory)
            try:
                self.collection = self.chroma_client.get_collection("profile_embeddings")
            except:
                self.collection = self.chroma_client.create_collection(
                    name="profile_embeddings",
                    metadata={"hnsw:space": "cosine"}
                )
        except ImportError:
            logger.warning("ChromaDB not installed")
            self.collection = None
    
    def _init_tfidf(self):
        """Initialize TF-IDF vectorizer as fallback"""
        from sklearn.feature_extraction.text import TfidfVectorizer
        self.tfidf_vectorizer = TfidfVectorizer(max_features=384)
        self.tfidf_fitted = False
        self.embedding_dim = 384
    
    def _get_tfidf_embedding(self, text: str) -> List[float]:
        """Generate embedding using TF-IDF"""
        if not self.tfidf_fitted:
            # Fit on this text
            self.tfidf_vectorizer.fit([text])
            self.tfidf_fitted = True
        embedding = self.tfidf_vectorizer.transform([text]).toarray()[0]
        # Normalize
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm
        return embedding.tolist()
    
    def embed_profile(self, profile: Dict[str, Any]) -> List[float]:
        """
        Embed a user profile for similarity search
        """
        # Combine skills, job titles, and preferences for embedding
        text_parts = []
        
        if profile.get('skills'):
            text_parts.append("Skills: " + ", ".join(profile['skills']))
        
        if profile.get('job_titles'):
            text_parts.append("Previous Roles: " + ", ".join(profile['job_titles']))
        
        if profile.get('preferences_raw'):
            text_parts.append("Preferences: " + profile['preferences_raw'])
        
        if profile.get('target_role'):
            text_parts.append("Target Role: " + profile['target_role'])
        
        if profile.get('target_location'):
            text_parts.append("Target Location: " + profile['target_location'])
        
        text_to_embed = " | ".join(text_parts)
        
        logger.info(f"Embedding profile: {text_to_embed[:200]}...")
        
        # Generate embedding
        if self.use_local_model and self.model:
            try:
                embedding = self.model.encode(text_to_embed).tolist()
            except Exception as e:
                logger.error(f"Error with local model: {e}")
                embedding = self._get_tfidf_embedding(text_to_embed)
        else:
            embedding = self._get_tfidf_embedding(text_to_embed)
        
        # Store in ChromaDB if available
        if self.collection and profile.get('id'):
            try:
                self.collection.add(
                    embeddings=[embedding],
                    metadatas=[{
                        "user_profile_id": profile.get('id'),
                        "seniority_level": profile.get('seniority_level'),
                        "target_role": profile.get('target_role'),
                        "target_location": profile.get('target_location'),
                        "years_experience": profile.get('years_experience')
                    }],
                    ids=[profile.get('id')]
                )
            except Exception as e:
                logger.warning(f"Failed to store embedding: {e}")
        
        return embedding
    
    def get_profile_embedding(self, profile_id: str) -> List[float]:
        """Retrieve existing profile embedding from ChromaDB"""
        if not self.collection:
            return None
        
        try:
            result = self.collection.get(
                ids=[profile_id],
                include=["embeddings"]
            )
            
            if result['embeddings'] and len(result['embeddings']) > 0:
                return result['embeddings'][0]
        except Exception as e:
            logger.error(f"Error retrieving profile embedding: {e}")
        
        return None
    
    def delete_profile(self, profile_id: str) -> bool:
        """Delete profile embedding from ChromaDB"""
        if not self.collection:
            return False
        
        try:
            self.collection.delete(ids=[profile_id])
            return True
        except Exception as e:
            logger.error(f"Error deleting profile: {e}")
            return False