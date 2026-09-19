from fastapi import APIRouter, Depends, HTTPException, status
from typing import List

from app.models.user import UserProfile, SavedRoute, TripHistorySummary, ConversationSummary
from app.api.auth import get_authenticated_user
from app.api.dependencies import get_user_repository, get_trip_repository, get_conversation_repository
from app.repositories.interfaces.user_repository import UserRepository
from app.repositories.interfaces.trip_repository import TripRepository
from app.repositories.interfaces.conversation_repository import ConversationRepository
from app.models.trip import TripResponse

router = APIRouter()

@router.get("/me/profile", response_model=UserProfile)
async def get_profile(
    current_user: dict = Depends(get_authenticated_user),
    user_repo: UserRepository = Depends(get_user_repository)
):
    uid = current_user["uid"]
    profile = await user_repo.get_profile(uid)
    if not profile:
        # Return a default profile if none exists
        profile = UserProfile(
            uid=uid,
            email=current_user.get("email")
        )
    return profile

@router.put("/me/profile", response_model=UserProfile)
async def update_profile(
    profile: UserProfile,
    current_user: dict = Depends(get_authenticated_user),
    user_repo: UserRepository = Depends(get_user_repository)
):
    uid = current_user["uid"]
    # Authenticated Firebase UID is the sole identity authority
    profile.uid = uid
    await user_repo.update_profile(uid, profile)
    return profile

@router.get("/me/saved-routes", response_model=List[SavedRoute])
async def get_saved_routes(
    current_user: dict = Depends(get_authenticated_user),
    user_repo: UserRepository = Depends(get_user_repository)
):
    uid = current_user["uid"]
    return await user_repo.get_saved_routes(uid)

@router.post("/me/saved-routes", response_model=SavedRoute)
async def save_route(
    route: SavedRoute,
    current_user: dict = Depends(get_authenticated_user),
    user_repo: UserRepository = Depends(get_user_repository)
):
    uid = current_user["uid"]
    await user_repo.save_route(uid, route)
    return route

@router.delete("/me/saved-routes/{saved_route_id}")
async def delete_saved_route(
    saved_route_id: str,
    current_user: dict = Depends(get_authenticated_user),
    user_repo: UserRepository = Depends(get_user_repository)
):
    uid = current_user["uid"]
    await user_repo.delete_saved_route(uid, saved_route_id)
    return {"status": "deleted"}

@router.get("/me/trips", response_model=List[TripHistorySummary])
async def get_trips(
    current_user: dict = Depends(get_authenticated_user),
    trip_repo: TripRepository = Depends(get_trip_repository)
):
    uid = current_user["uid"]
    return await trip_repo.get_trip_history(uid)

@router.get("/me/trips/{analysis_id}", response_model=TripResponse, response_model_by_alias=True)
async def get_trip_detail(
    analysis_id: str,
    current_user: dict = Depends(get_authenticated_user),
    trip_repo: TripRepository = Depends(get_trip_repository)
):
    uid = current_user["uid"]
    trip = await trip_repo.get_trip_decision(uid, analysis_id)
    if not trip:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found")
    return trip

@router.get("/me/conversations", response_model=List[ConversationSummary])
async def get_conversations(
    current_user: dict = Depends(get_authenticated_user),
    conv_repo: ConversationRepository = Depends(get_conversation_repository)
):
    uid = current_user["uid"]
    return await conv_repo.get_conversations(uid)
