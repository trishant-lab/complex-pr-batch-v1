from asyncpg.exceptions import PostgresError


class DataModificationError(PostgresError):
    """
    error while modifying data in db
    """

    def __str__(self: "DataModificationError") -> str:
        """
        @return:
        """
        return super().__str__()


class DataFetchError(PostgresError):
    """
    error while fetching data from db
    """

    def __str__(self: "DataFetchError") -> str:
        """
        @return:
        """
        return super().__str__()


DB_ERROR_CODES: dict = {
    "DataModificationError": {
        "description": "Error while inserting/updating data",
        "followupAction": ["Possible resolution will be done. Support will contact you."],
        "errorMsg": [],
        "possibleResolutions": [],
    },
    "DataFetchError": {
        "description": "Error while fetching data",
        "followupAction": ["Possible resolution will be done. Support will contact you."],
        "errorMsg": [],
        "possibleResolutions": [],
    },
}
