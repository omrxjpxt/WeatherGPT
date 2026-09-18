from abc import ABC, abstractmethod
from typing import List, Optional
from app.models.user import UserProfile, SavedRoute

class UserRepository(ABC):
    @abstractmethod
    async def get_profile(self, uid: str) -> Optional[UserProfile]:
        """Retrieve user profile."""
        pass

    @abstractmethod
    async def update_profile(self, uid: str, profile: UserProfile) -> None:
        """Create or update user profile."""
        pass

    @abstractmethod
    async def get_saved_routes(self, uid: str) -> List[SavedRoute]:
        """Retrieve user's saved routes."""
        pass

    @abstractmethod
    async def save_route(self, uid: str, route: SavedRoute) -> None:
        """Save a new route for a user."""
        pass

    @abstractmethod
    async def delete_saved_route(self, uid: str, saved_route_id: str) -> None:
        """Delete a saved route."""
        pass
