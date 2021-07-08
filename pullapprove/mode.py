class Mode:
    def __init__(self) -> None:
        self._mode = "live"

    def __str__(self):
        return self._mode

    def set_test(self) -> None:
        self._mode = "test"

    def is_live(self) -> bool:
        return self._mode == "live"

    def is_test(self) -> bool:
        return self._mode == "test"
