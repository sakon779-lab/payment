from typing import Optional

def reverse_string(input_str: str) -> Optional[str]:
    """
    Reverse the given string.

    Args:
        input_str (str): The string to be reversed.

    Returns:
        Optional[str]: The reversed string if input is valid, None otherwise.
    """
    if not input_str:
        return None
    return input_str[::-1]