from fastapi import status
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder


class BuildJSONResponses:
    @staticmethod
    def record_not_found():
        return JSONResponse(
            content={"data": [], "succeeded": True, "message": "Record Not Found"},
            status_code=status.HTTP_200_OK,
        )

    @staticmethod
    def success_response(
        data=None, message=None, status_code=status.HTTP_200_OK, succeeded=True
    ):
        return JSONResponse(
            content={
                "data": jsonable_encoder(data),
                "succeeded": succeeded,
                "message": message,
                "httpStatusCode": status_code,
            },
            status_code=status.HTTP_200_OK,
        )

    @staticmethod
    def success_response_with_pagination_metadata(
        data=None, message=None, paginated_response=None
    ):
        return JSONResponse(
            content={
                "data": jsonable_encoder(data),
                "succeeded": True,
                "message": message,
                "pagination_metadata": paginated_response,
            },
            status_code=status.HTTP_200_OK,
        )

    @staticmethod
    def invalid_input(message):
        return JSONResponse(
            content={"data": [], "succeeded": False, "message": message},
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    @staticmethod
    def raise_exception(message, status_code=status.HTTP_400_BAD_REQUEST):
        return JSONResponse(
            content={"succeeded": False, "message": str(message)},
            status_code=status_code,
        )

    @staticmethod
    def invalid_token(message):
        return JSONResponse(
            content={
                "data": [],
                "succeeded": False,
                "message": message,
                "httpStatusCode": 401,
            },
            status_code=status.HTTP_401_UNAUTHORIZED,
        )
    @staticmethod
    def raise_exception_with_message(message, status_code=status.HTTP_400_BAD_REQUEST):
        return JSONResponse(
            content=str(message),  # returns just a string
            status_code=status_code,
        )


class CustomDBResponseHandler:
    @staticmethod
    def record_not_found():
        return {"status": False, "reason": 404}

    @staticmethod
    def success_message(data=None, message=None):
        return {"status": True, "data": data, "message": message}

    @staticmethod
    def exception_with_message(message):
        return {"status": False, "reason": 500, "message": str(message)}


class DBResponseChecker:
    @staticmethod
    def check_db_response(
        db_response, only_message_needed=False, message_data_both_required=False
    ):
        if db_response["status"]:
            if only_message_needed:
                return db_response["message"], None
            elif message_data_both_required:
                return db_response, None
            else:
                return db_response["data"], None
        else:
            if db_response["reason"] == 404:
                return None, BuildJSONResponses.record_not_found()
            elif db_response["reason"] == 400:
                return None, BuildJSONResponses.invalid_input(db_response["message"])
            else:
                return None, BuildJSONResponses.raise_exception(db_response["message"])
