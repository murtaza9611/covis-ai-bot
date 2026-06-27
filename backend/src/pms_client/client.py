import requests
from src.settings import settings
from src.pms_client.schemas import TaskPayload, BoardColumn


def login() -> str:
    payload = {
        "email": settings.PMS_EMAIL,
        "password": settings.PMS_PASSWORD,
        "deviceToken": "string",
        "deviceTypeId": 0
    }
    response = requests.post(
        f"{settings.PMS_BASE_URL}/api/Login/AuthUser",
        # json={"email": settings.PMS_EMAIL, "password": settings.PMS_PASSWORD},
        json=payload,
        headers={"Content-Type": "application/json"},
    )
    response.raise_for_status()
    data = response.json()
    if data.get("status") != 1:
        raise RuntimeError(f"PMS login failed: {data.get('message')}")
    return data["data"]["token"]


def create_task(token: str, payload: TaskPayload) -> dict:
    response = requests.post(
        f"{settings.PMS_BASE_URL}/api/ProjectTask/CreateProjectTask",
        json=payload.model_dump(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
    )
    response.raise_for_status()
    data = response.json()
    if data.get("status") != 1:
        raise RuntimeError(f"Create task failed: {data.get('message')}")
    return data["data"]


def get_tasks(
    token: str,
    timezone: str,
    start_date: str | None = None,
    end_date: str | None = None,
    general_search: str | None = None,
) -> list[BoardColumn]:
    """Fetch board columns/cards. Pass ``general_search`` to filter by PMS text search (duplicate checks)."""
    response = requests.post(
        f"{settings.PMS_BASE_URL}/api/ProjectTask/GetProjectTasksDetailsByProjectId",
        json={
            "taskTypeId": None,
            "startDate": start_date,
            "endDate": end_date,
            "DateType": 1,
            "severityId": None,
            "currentAssigneeId": None,
            "projectMileStoneId": settings.PMS_MILESTONE_ID,
            "generalSearch": (general_search or "").strip(),
            "pageNo": 1,
            "pageSize": 5000,
            "projectId": str(settings.PMS_PROJECT_ID),
            "organizationId": settings.PMS_ORGANIZATION_ID,
            "userId": settings.PMS_USER_ID,
            "timeZone": timezone,
        },
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
    )
    response.raise_for_status()
    data = response.json()
    if data.get("status") != 1:
        raise RuntimeError(f"Get tasks failed: {data.get('message')}")
    return [
        BoardColumn(**{**board, "cards": board.get("cards") or []})
        for board in data["data"]
    ]
