"""
GET /api/team_info endpoint.
Returns student details.
"""
from fastapi import APIRouter
from app.api.schemas.responses import TeamInfoResponse, StudentInfo

router = APIRouter()


@router.get("/team_info", response_model=TeamInfoResponse)
async def get_team_info() -> TeamInfoResponse:
    """
    Returns student details.

    Purpose: Retrieve team member names and emails for the course project.

    Returns:
        TeamInfoResponse with group info and student list
    """
    return TeamInfoResponse(
        group_batch_order_number="batch_1_order_9",
        team_name="avi_yehoraz_maya",
        students=[
            StudentInfo(name="Avi Simkin", email="avi.simkin@campus.technion.ac.il"),
            StudentInfo(name="Yehoraz Ben-Yehuda", email="yehoraz.ben@campus.technion.ac.il"),
            StudentInfo(name="Maya Meirovich", email="mmeirovich@campus.technion.ac.il")
        ]
    )
