"""tests/test_agent_state.py"""
import pytest
from app.core.agent.state import AgentState, AgentStateMachine, StateTransitionError


class TestAgentStateMachine:
    def test_initial_state(self):
        sm = AgentStateMachine()
        assert sm.current == AgentState.PENDING

    def test_pending_to_running(self):
        sm = AgentStateMachine()
        sm.transition(AgentState.RUNNING)
        assert sm.current == AgentState.RUNNING

    def test_running_to_tool_call(self):
        sm = AgentStateMachine(AgentState.RUNNING)
        sm.transition(AgentState.TOOL_CALL)
        assert sm.current == AgentState.TOOL_CALL

    def test_tool_call_to_running(self):
        sm = AgentStateMachine(AgentState.TOOL_CALL)
        sm.transition(AgentState.RUNNING)
        assert sm.current == AgentState.RUNNING

    def test_running_to_finished(self):
        sm = AgentStateMachine(AgentState.RUNNING)
        sm.transition(AgentState.FINISHED)
        assert sm.current == AgentState.FINISHED

    def test_running_to_error(self):
        sm = AgentStateMachine(AgentState.RUNNING)
        sm.transition(AgentState.ERROR)
        assert sm.current == AgentState.ERROR

    def test_invalid_transition_raises(self):
        sm = AgentStateMachine(AgentState.PENDING)
        with pytest.raises(StateTransitionError, match="Cannot transition"):
            sm.transition(AgentState.THINKING)  # PENDING->THINKING is invalid

    def test_finished_is_terminal(self):
        sm = AgentStateMachine(AgentState.FINISHED)
        with pytest.raises(StateTransitionError):
            sm.transition(AgentState.RUNNING)

    def test_error_is_terminal(self):
        sm = AgentStateMachine(AgentState.ERROR)
        with pytest.raises(StateTransitionError):
            sm.transition(AgentState.PENDING)

    def test_full_react_cycle(self):
        sm = AgentStateMachine()
        assert sm.current == AgentState.PENDING
        sm.transition(AgentState.RUNNING)
        assert sm.current == AgentState.RUNNING
        sm.transition(AgentState.THINKING)
        assert sm.current == AgentState.THINKING
        sm.transition(AgentState.TOOL_CALL)
        assert sm.current == AgentState.TOOL_CALL
        sm.transition(AgentState.RUNNING)
        assert sm.current == AgentState.RUNNING
        sm.transition(AgentState.FINISHED)
        assert sm.current == AgentState.FINISHED

    def test_allowed_transitions_returns_list(self):
        sm = AgentStateMachine(AgentState.RUNNING)
        allowed = sm.allowed_transitions()
        assert AgentState.THINKING in allowed
        assert AgentState.TOOL_CALL in allowed
        assert AgentState.FINISHED in allowed

    def test_reset_goes_to_pending(self):
        sm = AgentStateMachine(AgentState.FINISHED)
        sm.reset()
        assert sm.current == AgentState.PENDING
