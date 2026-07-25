from enum import Enum, auto

class ParserState(Enum):
    IDLE = auto()
    READING_DEFAULT = auto()
    READING_OBJECT = auto()

class ParserStateMachine:
    """
    Parser State Machine.
    Governs state transitions during token stream processing.
    """

    def __init__(self):
        self.state = ParserState.IDLE

    def transition_to(self, new_state: ParserState):
        self.state = new_state

    @property
    def is_reading_default(self) -> bool:
        return self.state == ParserState.READING_DEFAULT

    @property
    def is_reading_object(self) -> bool:
        return self.state == ParserState.READING_OBJECT
