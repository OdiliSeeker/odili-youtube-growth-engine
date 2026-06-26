from fastapi import APIRouter
from app.models.schemas import PlaylistRequest, PlaylistResponse
from app.services.playlist_service import route_to_playlist

router = APIRouter()


@router.post("/playlist", response_model=PlaylistResponse, tags=["Playlist"])
async def get_playlist(request: PlaylistRequest) -> PlaylistResponse:
    """
    Map a piece of text to the most relevant Odili Truth Seeker playlist.
    Falls back to 'General Content' when no keyword match is found.
    """
    playlist = route_to_playlist(request.text)
    return PlaylistResponse(playlist=playlist)
