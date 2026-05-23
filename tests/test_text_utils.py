from discord_helper.core.text_utils import sanitize_for_tts


def test_remove_code_block():
    text = """hola
```python
print('test')
```
adios"""

    result = sanitize_for_tts(text)

    assert "print" not in result



def test_remove_url():
    text = "visita https://example.com ahora"

    result = sanitize_for_tts(text)

    assert "http" not in result



def test_remove_numbered_list():
    text = "1. primer punto\n2. segundo punto"

    result = sanitize_for_tts(text)

    assert "1." not in result
    assert "2." not in result



def test_clean_text_unchanged():
    text = "Hola, ¿cómo estás?"

    result = sanitize_for_tts(text)

    assert result == text
