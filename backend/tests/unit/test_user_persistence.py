import pytest
from app.repositories.firestore.user_repository import FirestoreUserRepository
from app.models.user import UserProfile, SavedRoute

@pytest.fixture
def memory_repo():
    return FirestoreUserRepository(client=None)

@pytest.mark.asyncio
async def test_user_profile_crud(memory_repo):
    uid = "test_user_1"
    
    # Get non-existent
    profile = await memory_repo.get_profile(uid)
    assert profile is None
    
    # Create
    new_profile = UserProfile(uid=uid, email="test@test.com")
    await memory_repo.update_profile(uid, new_profile)
    
    # Read
    fetched = await memory_repo.get_profile(uid)
    assert fetched is not None
    assert fetched.email == "test@test.com"
    
@pytest.mark.asyncio
async def test_saved_routes_crud(memory_repo):
    uid = "test_user_1"
    
    # Get empty
    routes = await memory_repo.get_saved_routes(uid)
    assert len(routes) == 0
    
    # Add route
    route = SavedRoute(id="route1", name="Home to Work", origin_id="home", destination_id="work")
    await memory_repo.save_route(uid, route)
    
    # Read
    routes = await memory_repo.get_saved_routes(uid)
    assert len(routes) == 1
    assert routes[0].name == "Home to Work"
    
    # Delete
    await memory_repo.delete_saved_route(uid, "route1")
    routes = await memory_repo.get_saved_routes(uid)
    assert len(routes) == 0

@pytest.mark.asyncio
async def test_user_data_isolation(memory_repo):
    uid1 = "user1"
    uid2 = "user2"
    
    route = SavedRoute(id="r1", name="U1 Route", origin_id="A", destination_id="B")
    await memory_repo.save_route(uid1, route)
    
    routes1 = await memory_repo.get_saved_routes(uid1)
    routes2 = await memory_repo.get_saved_routes(uid2)
    
    assert len(routes1) == 1
    assert len(routes2) == 0
