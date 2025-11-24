# tests/test_llm_provider.py
import pytest
import asyncio

class FakeSession:
    def __init__(self):
        self.calls = []

    class _Resp:
        def __init__(self, status=200, data=b"{}"):
            self.status = status
            self._data = data
            self.headers = {}

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def json(self):
            return {}

        @property
        def content(self):
            class C:
                async def read(self):
                    return b""
            return C()

    def post(self, url=None, headers=None, json=None, data=None):
        self.calls.append({'url': url, 'headers': headers, 'json': json, 'data': data})
        return FakeSession._Resp()


@pytest.fixture
def monkey_config(monkeypatch):
    # Патчим server.helper.load_config так, чтобы вернуть заданный конфиг
    from server import helper as hlp
    def set_cfg(cfg):
        monkeypatch.setattr(hlp, "load_config", lambda: cfg)
    return set_cfg


def mk_interface():
    from server.oai_interface import Interface
    sess = FakeSession()
    itf = Interface(sess)
    return itf, sess


def test_openai_provider(monkey_config):
    cfg = {
        'llm': {
            'provider': 'openai',
            'api_base': 'https://api.openai.com/v1',
            'api_key': 'TESTKEY',
            'model_chat': 'gpt-4o-mini'
        }
    }
    monkey_config(cfg)
    itf, _ = mk_interface()
    assert itf.provider == 'openai'
    assert itf.api_base.endswith('/v1')
    assert itf.header['Authorization'] == 'Bearer TESTKEY'
    assert itf.model_chat == 'gpt-4o-mini'


def test_deepseek_provider(monkey_config):
    cfg = {
        'llm': {
            'provider': 'deepseek',
            'api_key': 'DEEPKEY',
            'model_chat': 'deepseek-chat'
        }
    }
    monkey_config(cfg)
    itf, _ = mk_interface()
    assert itf.provider == 'deepseek'
    assert itf.api_base.endswith('/v1')
    assert itf.header['Authorization'] == 'Bearer DEEPKEY'
    assert itf.model_chat == 'deepseek-chat'


def test_qwen_provider(monkey_config):
    cfg = {
        'llm': {
            'provider': 'qwen',
            'api_key': 'DASHKEY',
            'model_chat': 'qwen2.5-7b-instruct'
        }
    }
    monkey_config(cfg)
    itf, _ = mk_interface()
    assert itf.provider == 'qwen'
    assert itf.api_base.endswith('/v1')
    assert itf.header['Authorization'] == 'Bearer DASHKEY'
    assert itf.model_chat == 'qwen2.5-7b-instruct'


def test_tts_not_supported_on_deepseek(monkey_config):
    # Проверяем, что TTS на deepseek не поддержан и кидает NotImplementedError
    cfg = {
        'llm': {
            'provider': 'deepseek',
            'api_key': 'DEEPKEY',
            'model_chat': 'deepseek-chat'
        }
    }
    monkey_config(cfg)
    itf, _ = mk_interface()

    async def run():
        with pytest.raises(NotImplementedError):
            await itf.get_tts(voice=None, input="hello", model=None)

    asyncio.run(run())


def test_stt_not_supported_conditionally(monkey_config, tmp_path):
    # Тест STT (transcribe) — только если метод вообще существует в твоей версии Interface.
    cfg = {
        'llm': {
            'provider': 'qwen',
            'api_key': 'DASHKEY',
            'model_chat': 'qwen2.5-7b-instruct'
        }
    }
    monkey_config(cfg)
    itf, _ = mk_interface()

    if not hasattr(itf, "transcribe") or not callable(getattr(itf, "transcribe")):
        pytest.skip("Interface.transcribe() отсутствует — пропускаем STT-тест")

    dummy = tmp_path / "audio.wav"
    dummy.write_bytes(b"\x00\x00")

    async def run():
        with pytest.raises(NotImplementedError):
            await itf.transcribe(str(dummy), model=None)

    asyncio.run(run())
