"""
graph/builder.py
LangGraph 图构建

流程：
input_node → glucose_reader → triage_node
  → [条件路由] → companion_agent / expert_agent → history_update → END
"""
import sqlite3
from pathlib import Path
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver
from chatbot.state.chat_state import ChatState
from chatbot.agents.triage import input_node, triage_node, route_by_intent
from chatbot.agents.glucose_reader import glucose_reader_node
from chatbot.agents.companion import companion_agent_node
from chatbot.agents.expert import expert_agent_node
from chatbot.utils.memory import add_to_history


def history_update_node(state: ChatState) -> dict:
    """图内最后一步：把本轮对话追加到 history，由 checkpointer 持久化。"""
    user_text = state.get("user_input", "")
    response  = state.get("response", "")
    history   = add_to_history(state.get("history") or [], "user",      user_text)
    history   = add_to_history(history,                    "assistant",  response)
    return {"history": history}


def build_graph(checkpointer=None):
    graph = StateGraph(ChatState)

    # ── 注册节点 ─────────────────────────────────────────
    graph.add_node("input_node",      input_node)
    graph.add_node("glucose_reader",  glucose_reader_node)
    graph.add_node("triage_node",     triage_node)
    graph.add_node("companion_agent", companion_agent_node)
    graph.add_node("expert_agent",    expert_agent_node)
    graph.add_node("history_update",  history_update_node)

    # ── 入口 ─────────────────────────────────────────────
    graph.set_entry_point("input_node")

    # ── 固定边 ───────────────────────────────────────────
    graph.add_edge("input_node",     "glucose_reader")
    graph.add_edge("glucose_reader", "triage_node")

    # ── 条件路由：triage → crisis short-circuit or agent ──
    def _route_after_triage(state: ChatState) -> str:
        if state.get("intent") == "crisis":
            return "history_update"
        return route_by_intent(state)

    graph.add_conditional_edges(
        "triage_node",
        _route_after_triage,
        {
            "history_update": "history_update",
            "companion_agent": "companion_agent",
            "expert_agent":    "expert_agent",
        }
    )

    # ── 所有Agent → history_update → END ─────────────────
    for node in ["companion_agent", "expert_agent"]:
        graph.add_edge(node, "history_update")
    graph.add_edge("history_update", END)

    return graph.compile(checkpointer=checkpointer)


_DB_PATH = Path(__file__).parent.parent.parent / "data" / "langgraph.db"
_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
_conn = sqlite3.connect(str(_DB_PATH), check_same_thread=False)
app   = build_graph(SqliteSaver(_conn))
