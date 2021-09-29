from ..status import State

GITLAB_STATUS_STATE_TO_PULLAPPROVE_STATUS_STATE = {
    "pending": State.PENDING,
    "running": State.PENDING,
    "success": State.SUCCESS,
    "failed": State.FAILURE,
    "canceled": State.FAILURE,
}

PULLAPPROVE_STATUS_STATE_TO_GITLAB_STATUS_STATE = {
    State.SUCCESS: "success",
    State.PENDING: "pending",
    State.FAILURE: "failed",
    State.ERROR: "canceled",
}
