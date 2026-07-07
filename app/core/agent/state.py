from enum import Enum


class AgentState(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    THINKING = "THINKING"
    TOOL_CALL = "TOOL_CALL"
    FINISHED = "FINISHED"
    ERROR = "ERROR"


_TRANSITIONS: dict[AgentState, list[AgentState]] = {
    AgentState.PENDING: [AgentState.RUNNING],
    AgentState.RUNNING: [AgentState.THINKING, AgentState.TOOL_CALL, AgentState.FINISHED, AgentState.ERROR],
    AgentState.THINKING: [AgentState.TOOL_CALL, AgentState.FINISHED],
    AgentState.TOOL_CALL: [AgentState.RUNNING],
    AgentState.FINISHED: [],
    AgentState.ERROR: [],
}

_TERMINAL_STATES = {AgentState.FINISHED, AgentState.ERROR}


class StateTransitionError(Exception):
    pass


class AgentStateMachine:
    """Finite state machine for Agent execution lifecycle."""

    def __init__(self, initial: AgentState = AgentState.PENDING):
        self._state = initial

    @property
    def current(self) -> AgentState:
        return self._state

    def transition(self, target: AgentState) -> None:
        if self._state in _TERMINAL_STATES:
            raise StateTransitionError(
                f"Cannot transition from terminal state {self._state.value}"
            )
        allowed = _TRANSITIONS.get(self._state, [])
        if target not in allowed:
            raise StateTransitionError(
                f"Cannot transition from {self._state.value} to {target.value}. "
                f"Allowed: {[s.value for s in allowed]}"
            )
        self._state = target

    def allowed_transitions(self) -> list[AgentState]:
        return list(_TRANSITIONS.get(self._state, []))

    def is_terminal(self) -> bool:
        return self._state in _TERMINAL_STATES

    def reset(self) -> None:
        self._state = AgentState.PENDING
