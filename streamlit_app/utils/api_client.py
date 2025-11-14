"""
Klient API do komunikacji z backend serwisami
"""
import sys
from pathlib import Path

import httpx

# Dodaj katalog główny projektu do ścieżki
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from shared.config import get_settings

settings = get_settings()


class APIClient:
    """Klient do komunikacji z API serwisami"""
    
    def __init__(self, access_token: str | None = None):
        self.access_token = access_token
        self.base_urls = {
            "user": settings.user_service_url,
            "knowledge_base": settings.knowledge_base_service_url,
            "knowledge_management": settings.knowledge_management_service_url,
            "admin": settings.admin_panel_service_url
        }
    
    def _get_headers(self):
        """Pobierz nagłówki z tokenem autoryzacji"""
        headers = {"Content-Type": "application/json"}
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        return headers
    
    # User Service
    def login(self, username: str, password: str) -> dict:
        """Logowanie użytkownika"""
        with httpx.Client() as client:
            data = {
                "username": username,
                "password": password
            }
            response = client.post(
                f"{self.base_urls['user']}/api/v1/auth/token",
                data=data,
                timeout=10.0
            )
            if response.status_code == 200:
                return response.json()
            return None
    
    def get_current_user(self) -> dict | None:
        """Pobierz informacje o zalogowanym użytkowniku"""
        with httpx.Client() as client:
            response = client.get(
                f"{self.base_urls['user']}/api/v1/auth/me",
                headers=self._get_headers(),
                timeout=10.0
            )
            if response.status_code == 200:
                return response.json()
            return None
    
    # Knowledge Base Service
    def search(self, query: str, top_k: int = 5, user_id: int | None = None) -> dict:
        """Wyszukiwanie w bazie wiedzy"""
        with httpx.Client() as client:
            data = {"query": query}
            params = {"top_k": top_k, "search_type": "hybrid"}
            if user_id:
                params["user_id"] = user_id
            
            response = client.post(
                f"{self.base_urls['knowledge_base']}/api/v1/search/query",
                json=data,
                params=params,
                headers=self._get_headers(),
                timeout=30.0
            )
            if response.status_code == 200:
                return response.json()
            raise Exception(f"Błąd wyszukiwania: {response.status_code} - {response.text}")
    
    # Knowledge Management Service
    def upload_document(self, file_content: bytes, filename: str, content_type: str) -> dict:
        """Upload dokumentu"""
        with httpx.Client() as client:
            files = {
                "file": (filename, file_content, content_type)
            }
            response = client.post(
                f"{self.base_urls['knowledge_management']}/api/v1/documents/upload",
                files=files,
                headers={"Authorization": f"Bearer {self.access_token}"} if self.access_token else {},
                timeout=60.0
            )
            if response.status_code == 201:
                return response.json()
            raise Exception(f"Błąd uploadu: {response.status_code} - {response.text}")
    
    def list_documents(self, skip: int = 0, limit: int = 100) -> list:
        """Lista dokumentów"""
        with httpx.Client() as client:
            response = client.get(
                f"{self.base_urls['knowledge_management']}/api/v1/documents/",
                params={"skip": skip, "limit": limit},
                headers=self._get_headers(),
                timeout=10.0
            )
            if response.status_code == 200:
                return response.json()
            return []
    
    def get_document(self, document_id: int) -> dict | None:
        """Pobierz dokument po ID"""
        with httpx.Client() as client:
            response = client.get(
                f"{self.base_urls['knowledge_management']}/api/v1/documents/{document_id}",
                headers=self._get_headers(),
                timeout=10.0
            )
            if response.status_code == 200:
                return response.json()
            return None
    
    def search_in_document(self, document_id: int, query: str, top_k: int = 5) -> dict:
        """Wyszukiwanie w konkretnym dokumencie"""
        # TODO: Implement proper document filtering
        return self.search(query, top_k=top_k, user_id=None)
    
    # Admin Panel Service
    def list_users(self, skip: int = 0, limit: int = 100) -> list:
        """Lista użytkowników (admin)"""
        with httpx.Client() as client:
            response = client.get(
                f"{self.base_urls['admin']}/api/v1/users/",
                params={"skip": skip, "limit": limit},
                headers=self._get_headers(),
                timeout=10.0
            )
            if response.status_code == 200:
                return response.json()
            return []
    
    def get_user(self, user_id: int) -> dict | None:
        """Pobierz użytkownika po ID (admin)"""
        with httpx.Client() as client:
            response = client.get(
                f"{self.base_urls['admin']}/api/v1/users/{user_id}",
                headers=self._get_headers(),
                timeout=10.0
            )
            if response.status_code == 200:
                return response.json()
            return None
    
    def update_user_password(self, user_id: int, new_password: str) -> dict:
        """Zmień hasło użytkownika (admin)"""
        with httpx.Client() as client:
            data = {"new_password": new_password}
            response = client.put(
                f"{self.base_urls['admin']}/api/v1/users/{user_id}/password",
                json=data,
                headers=self._get_headers(),
                timeout=10.0
            )
            if response.status_code == 200:
                return response.json()
            raise Exception(f"Błąd zmiany hasła: {response.status_code} - {response.text}")

