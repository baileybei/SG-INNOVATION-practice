from state.chat_state import ChatState


def test_chat_state_has_vision_fields():
    """ChatState should accept image_paths and vision_result fields."""
    state = ChatState(
        user_input="test",
        input_mode="text",
        chat_mode="personal",
        user_id="u1",
        history=[],
        user_profile={},
        image_paths=["/tmp/food.jpg"],
        vision_result=[{"scene_type": "FOOD", "confidence": 0.9}],
    )
    assert state["image_paths"] == ["/tmp/food.jpg"]
    assert state["vision_result"][0]["scene_type"] == "FOOD"


def test_chat_state_vision_fields_default_empty():
    """Vision fields should default to None when not provided."""
    state = ChatState(
        user_input="hello",
        input_mode="text",
        chat_mode="personal",
        user_id="u1",
        history=[],
        user_profile={},
    )
    assert state.get("image_paths") is None
    assert state.get("vision_result") is None
