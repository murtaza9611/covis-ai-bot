import json
import requests

BASE_URL = "https://pmsapidev.visioncollab.com"
OUTPUT_FILE = "tasks_output.json"

LOGIN_PAYLOAD = {
    "email": "irfanmalik@xevensolutions.com",
    "password": "Qwerty@1",
}

GET_TASKS_PAYLOAD = {
    "taskTypeId": None,
    "startDate": None,
    "endDate": None,
    "DateType": 1,
    "severityId": None,
    "currentAssigneeId": None,
    "projectMileStoneId": "1173",
    "generalSearch": "",
    "pageNo": 1,
    "pageSize": 5000,
    "projectId": "841",
    "organizationId": 109,
    "userId": 627,                    # always 627
    "timeZone": "Asia/Karachi",
}


def login():
    response = requests.post(
        f"{BASE_URL}/api/Login/Login",
        json=LOGIN_PAYLOAD,
        headers={"Content-Type": "application/json"},
    )
    response.raise_for_status()
    data = response.json()
    if data.get("status") != 1:
        raise RuntimeError(f"Login failed: {data.get('message')}")
    token = data["data"]["token"]
    print(f"Logged in as userId={data['data']['userId']} ({data['data']['firstName']} {data['data']['lastName']})")
    return token


def get_tasks(token):
    response = requests.post(
        f"{BASE_URL}/api/ProjectTask/GetProjectTasksDetailsByProjectId",
        json=GET_TASKS_PAYLOAD,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
    )
    response.raise_for_status()
    data = response.json()

    if data.get("status") == 1:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        print(f"Full response saved to {OUTPUT_FILE}\n")
        print("Board Summary:")
        print("-" * 40)
        for board in data["data"]:
            print(f"  {board['title']} ({board['taskBoardStatusName']}) — {board['totalTask']} task(s)")
            for card in board.get("cards", []):
                print(f"    [{card['taskId']}] {card['title']} (assignee: {card['assignee']})")
        print("-" * 40)
    else:
        print(f"Failed to fetch tasks: {data.get('message')}")


if __name__ == "__main__":
    token = login()
    get_tasks(token)
