from app.constants import MAX_MESSAGE_LENGTH


def split_message(text: str, max_length: int = MAX_MESSAGE_LENGTH) -> list[str]:
    """Разбивает длинное сообщение на части"""
    if len(text) <= max_length:
        return [text]
    
    chunks = []
    for i in range(0, len(text), max_length):
        chunks.append(text[i:i + max_length])
    
    return chunks
