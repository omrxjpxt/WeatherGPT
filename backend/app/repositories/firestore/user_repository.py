from typing import List, Optional, Dict
from app.repositories.interfaces.user_repository import UserRepository
from app.models.user import UserProfile, SavedRoute
from app.core.logging import get_logger

logger = get_logger(__name__)

class FirestoreUserRepository(UserRepository):
    def __init__(self, client):
        self.client = client
        # In-memory fallback: dict of uid -> UserProfile
        self._memory_profiles: Dict[str, UserProfile] = {}
        # In-memory fallback: dict of uid -> dict of route_id -> SavedRoute
        self._memory_routes: Dict[str, Dict[str, SavedRoute]] = {}
        if not self.client:
            logger.warning("UserRepository initialized in MEMORY MODE.")

    async def get_profile(self, uid: str) -> Optional[UserProfile]:
        if self.client:
            doc = await self.client.collection("users").document(uid).get()
            if doc.exists:
                return UserProfile.model_validate(doc.to_dict())
            return None
        else:
            return self._memory_profiles.get(uid)

    async def update_profile(self, uid: str, profile: UserProfile) -> None:
        if self.client:
            await self.client.collection("users").document(uid).set(profile.model_dump(mode="json"))
        else:
            self._memory_profiles[uid] = profile

    async def get_saved_routes(self, uid: str) -> List[SavedRoute]:
        if self.client:
            docs = await self.client.collection("users").document(uid).collection("saved_routes").get()
            return [SavedRoute.model_validate(doc.to_dict()) for doc in docs]
        else:
            routes = self._memory_routes.get(uid, {})
            return list(routes.values())

    async def save_route(self, uid: str, route: SavedRoute) -> None:
        if self.client:
            await self.client.collection("users").document(uid).collection("saved_routes").document(route.id).set(route.model_dump(mode="json"))
        else:
            if uid not in self._memory_routes:
                self._memory_routes[uid] = {}
            self._memory_routes[uid][route.id] = route

    async def delete_saved_route(self, uid: str, saved_route_id: str) -> None:
        if self.client:
            await self.client.collection("users").document(uid).collection("saved_routes").document(saved_route_id).delete()
        else:
            if uid in self._memory_routes and saved_route_id in self._memory_routes[uid]:
                del self._memory_routes[uid][saved_route_id]
