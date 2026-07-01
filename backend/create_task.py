import requests

BASE_URL = "https://pmsapidev.visioncollab.com"

LOGIN_PAYLOAD = {
    "email": "irfanmalik@xevensolutions.com",
    "password": "Qwerty@1",
}

TASK_PAYLOAD = {
    "taskId": 0,
    "title": "Automated Test Task",
    "description": "<p>Created by automation script</p>",
    "projectId": 841,
    "currentMileStoneId": "1173",
    "currentTaskBoardId": 2011,    #2011(TODO)#2012(In Progress)#2013(Ready to integrate)#2014(QA)#2015(Completed)
    "currentTaskBoardTypeId": 5,
    "currentReportedById": 627,
    "currentAssigneeId": 627,
    "taskTypeId": 35, #35(task)#36(bug)#37(story)
    "severityId": 1,   #1(critical)#2(important)#3(normal)#4(minor)#5(low)
    "currentEstimatedTime": 0,
    "dueDate": "2026-04-16",
    "taskDocuments": [],
    "userId": 627,
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


def create_task(token):
    response = requests.post(
        f"{BASE_URL}/api/ProjectTask/CreateProjectTask",
        json=TASK_PAYLOAD,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
    )
    response.raise_for_status()
    data = response.json()
    if data.get("status") == 1:
        task = data["data"]
        print(f"Task created!")
        print(f"  ID    : {task['taskId']}")
        print(f"  Title : {task['title']}")
        print(f"  Board : {task['currentTaskBoard']}")
        print(f"  Assignee: {task['assignee']}")
    else:
        print(f"Failed to create task: {data.get('message')}")


if __name__ == "__main__":
    token = login()
    create_task(token)
