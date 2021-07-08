from ..status import ReviewState, State

GITHUB_STATUS_STATE_TO_PULLAPPROVE_STATUS_STATE = {
    "success": State.SUCCESS,
    "pending": State.PENDING,
    "failure": State.FAILURE,
    "error": State.ERROR,
}

PULLAPPROVE_STATUS_STATE_TO_GITHUB_STATUS_STATE = {
    State.SUCCESS: "success",
    State.PENDING: "pending",
    State.FAILURE: "failure",
    State.ERROR: "error",
}

GITHUB_REVIEW_STATE_TO_PULLAPPROVE_REVIEW_STATE = {
    "APPROVED": ReviewState.APPROVED,
    "CHANGES_REQUESTED": ReviewState.REJECTED,
    "PENDING": ReviewState.PENDING,
    "DISMISSED": ReviewState.PENDING,
}
