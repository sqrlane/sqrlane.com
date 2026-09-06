"""llm.py is the only door to an AI provider, and there are now four of them.

Adding Hugging Face means Groq is no longer the only provider with runtime model
discovery, so the discovery code stopped being Groq-shaped and became shared.
That refactor is exactly the kind that works on the provider you tested and
quietly breaks the other one, so this suite holds both ends of it:

  1. A Hugging Face call goes to the router, OpenAI-shaped, with the token on it.
  2. Discovery never picks an image or audio model. The router lists them in the
     same call as chat models, which Groq's list never did - so the filter that
     was adequate for one provider is not adequate for the other.
  3. A retired model still costs exactly one re-resolve and one retry, on both
     providers. That behaviour was bought the hard way: a hard-coded name 404'd
     on a live key and sent every decision to the rule fallback silently.
  4. Nothing outside llm.py and config.py names a provider host. One door.

There is no network here and no key. Every provider response is a stub, which is
enough to prove the request we build and the branching we do. What it cannot
prove is that the live router answers in this shape - that needs one run of
`python -m src.llm --models` with a real token, the same way PEGELONLINE needed
one look from a machine with outbound access.

    python -m unittest discover -s tests
"""

import importlib
import json
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import config, llm  # noqa: E402


class _Reply:
    """The parts of a requests.Response that llm.py actually touches."""

    def __init__(self, status_code=200, payload=None, text=None):
        self.status_code = status_code
        self._payload = {} if payload is None else payload
        self.text = json.dumps(self._payload) if text is None else text
        self.headers = {}

    def json(self):
        return self._payload


def _catalogue(*entries):
    """A /v1/models reply. Each entry is an id, or an (id, task) pair."""
    data = []
    for entry in entries:
        if isinstance(entry, tuple):
            data.append({"id": entry[0], "object": "model", "task": entry[1]})
        else:
            data.append({"id": entry, "object": "model"})
    return _Reply(payload={"object": "list", "data": data})


def _answer(text="OK"):
    return _Reply(payload={"choices": [{"message": {"content": text},
                                        "finish_reason": "stop"}]})


class ProviderSwapTests(unittest.TestCase):

    def setUp(self):
        # Every test picks its own provider and key, so nothing leaks between
        # them - including the per-process resolved-model cache.
        self._saved = {name: getattr(config, name) for name in
                       ("LLM_PROVIDER", "LLM_MODEL", "HF_API_TOKEN", "GROQ_API_KEY")}
        llm._resolved.clear()
        llm._resolution_note = ""
        config.LLM_MODEL = ""
        config.HF_API_TOKEN = "hf_test_token"
        config.GROQ_API_KEY = "gsk_test_key"

    def tearDown(self):
        for name, value in self._saved.items():
            setattr(config, name, value)
        llm._resolved.clear()
        llm._resolution_note = ""

    # -- 1. the request we build --------------------------------------------

    def test_a_hugging_face_call_is_openai_shaped_and_carries_the_token(self):
        config.LLM_PROVIDER = "hf"
        self.assertTrue(llm.is_configured())

        catalogue = _catalogue("meta-llama/Llama-3.3-70B-Instruct")
        with mock.patch.object(llm.requests, "get", return_value=catalogue), \
             mock.patch.object(llm.requests, "post", return_value=_answer()) as post:
            reply = llm.complete("say OK", system="be brief", max_tokens=40)

        self.assertEqual(reply, "OK")
        url = post.call_args.args[0]
        body = post.call_args.kwargs["json"]
        headers = post.call_args.kwargs["headers"]

        self.assertEqual(url, "https://router.huggingface.co/v1/chat/completions")
        self.assertEqual(headers["Authorization"], "Bearer hf_test_token")
        self.assertEqual(body["model"], "meta-llama/Llama-3.3-70B-Instruct")
        self.assertEqual([m["role"] for m in body["messages"]], ["system", "user"])
        self.assertEqual(body["max_tokens"], 40)

    def test_groq_still_goes_to_groq(self):
        """The shared implementation must not have moved Groq's endpoint."""
        config.LLM_PROVIDER = "groq"
        catalogue = _catalogue("llama-3.3-70b-versatile")
        with mock.patch.object(llm.requests, "get", return_value=catalogue), \
             mock.patch.object(llm.requests, "post", return_value=_answer()) as post:
            llm.complete("say OK")

        self.assertEqual(post.call_args.args[0],
                         "https://api.groq.com/openai/v1/chat/completions")
        self.assertEqual(post.call_args.kwargs["headers"]["Authorization"],
                         "Bearer gsk_test_key")

    # -- 2. discovery picks a model that can answer with words ---------------

    def test_discovery_skips_image_and_audio_models_on_the_router(self):
        """The router lists FLUX and Whisper beside the chat models. Groq's did not.

        The first two entries are caught by name. The third is the one that
        matters: a house-branded image model whose name hits no exclusion at all,
        and which is only recognisable from its stated task. Nothing here is on
        the preference list, so ranking decides - and on size alone the image
        model wins, because it is the bigger number. Only the task check keeps it
        out. Deleting that check makes this test fail, which was confirmed by
        deleting it.
        """
        config.LLM_PROVIDER = "hf"
        catalogue = _catalogue(
            ("black-forest-labs/FLUX.1-dev", "text-to-image"),
            ("openai/whisper-large-v3", "automatic-speech-recognition"),
            ("some-lab/Dreamweaver-70B", "text-to-image"),
            ("some-lab/Chatterbox-32B-Instruct", "conversational"),
        )
        with mock.patch.object(llm.requests, "get", return_value=catalogue):
            chosen = llm.resolve_model("hf")
        self.assertEqual(chosen, "some-lab/Chatterbox-32B-Instruct")

    def test_a_model_with_no_stated_task_is_kept(self):
        """Groq's listing states no task at all - absent must not mean rejected."""
        self.assertTrue(llm._serves_text({"id": "llama-3.3-70b-versatile"}))
        self.assertFalse(llm._serves_text({"id": "x", "task": "text-to-image"}))
        self.assertTrue(llm._serves_text({"id": "x", "pipeline_tag": "conversational"}))

    def test_the_preference_list_wins_over_a_bigger_unknown_model(self):
        config.LLM_PROVIDER = "hf"
        catalogue = _catalogue("some-lab/Enormous-405B-Instruct",
                               "meta-llama/Llama-3.3-70B-Instruct")
        with mock.patch.object(llm.requests, "get", return_value=catalogue):
            self.assertEqual(llm.resolve_model("hf"),
                             "meta-llama/Llama-3.3-70B-Instruct")

    def test_an_unknown_lineup_still_yields_a_sensible_model(self):
        """The whole point of discovery: a catalogue this code has never seen."""
        config.LLM_PROVIDER = "hf"
        catalogue = _catalogue("some-lab/Tiny-3B-Instruct",
                               "some-lab/Base-70B",
                               "some-lab/Big-70B-Instruct")
        with mock.patch.object(llm.requests, "get", return_value=catalogue):
            self.assertEqual(llm.resolve_model("hf"), "some-lab/Big-70B-Instruct")

    def test_a_token_with_nothing_usable_says_so_rather_than_guessing(self):
        config.LLM_PROVIDER = "hf"
        catalogue = _catalogue(("black-forest-labs/FLUX.1-dev", "text-to-image"))
        with mock.patch.object(llm.requests, "get", return_value=catalogue):
            with self.assertRaises(llm.ModelNotAvailable) as caught:
                llm.resolve_model("hf")
        self.assertIn("Hugging Face", str(caught.exception))
        self.assertIn("huggingface.co/settings/tokens", str(caught.exception))

    def test_an_unreachable_model_list_falls_back_to_a_preference(self):
        """A demo does not die because the listing endpoint is having a moment."""
        config.LLM_PROVIDER = "hf"
        with mock.patch.object(llm.requests, "get",
                               side_effect=llm.requests.RequestException("boom")):
            chosen = llm.resolve_model("hf")
        self.assertEqual(chosen, config.HF_MODEL_PREFERENCES[0])
        self.assertIn("could not reach the model list", llm.resolution_note())

    # -- 3. a retired model costs one re-resolve, not the whole run ----------

    def test_a_retired_model_is_re_resolved_once_and_retried(self):
        config.LLM_PROVIDER = "hf"
        catalogue = _catalogue("meta-llama/Llama-3.3-70B-Instruct",
                               "Qwen/Qwen2.5-72B-Instruct")
        gone = _Reply(status_code=404,
                      text='{"error":"Model meta-llama/Llama-3.3-70B-Instruct '
                           'is not supported"}')
        with mock.patch.object(llm.requests, "get", return_value=catalogue), \
             mock.patch.object(llm.requests, "post",
                               side_effect=[gone, _answer("recovered")]) as post:
            reply = llm.complete("say OK")

        self.assertEqual(reply, "recovered")
        self.assertEqual(post.call_count, 2, "should be one retry, not a retry loop")
        first, second = (call.kwargs["json"]["model"] for call in post.call_args_list)
        self.assertEqual(first, "meta-llama/Llama-3.3-70B-Instruct")
        self.assertEqual(second, "Qwen/Qwen2.5-72B-Instruct")

    def test_a_generic_not_supported_error_is_not_mistaken_for_a_retired_model(self):
        """Only a message about a MODEL should send us round the re-resolve loop."""
        self.assertFalse(llm._looks_like_missing_model(
            '{"error":"tool choice is not supported"}'))
        self.assertTrue(llm._looks_like_missing_model(
            '{"error":"No inference provider available for model X"}'))

    # -- 4. one door ---------------------------------------------------------

    def test_only_llm_py_and_config_py_name_a_provider_host(self):
        hosts = ("api.groq.com", "router.huggingface.co",
                 "generativelanguage.googleapis.com", "api.openai.com")
        allowed = {"llm.py", "config.py"}
        offenders = []
        for path in sorted(Path("src").glob("*.py")):
            if path.name in allowed:
                continue
            body = path.read_text()
            for line_number, line in enumerate(body.splitlines(), start=1):
                if any(host in line for host in hosts):
                    offenders.append(f"{path}:{line_number}: {line.strip()}")
        self.assertEqual(offenders, [], "a second door to a provider has appeared:\n"
                                        + "\n".join(offenders))

    def test_every_provider_is_wired_end_to_end(self):
        """Half-wiring a provider is the failure this catches: a name that
        is_configured() accepts but complete() has no branch for."""
        for provider, key, value in (("groq", "GROQ_API_KEY", "gsk_x"),
                                     ("hf", "HF_API_TOKEN", "hf_x"),
                                     ("gemini", "GEMINI_API_KEY", "AIza_x"),
                                     ("ollama", "OLLAMA_HOST", "http://localhost:11434")):
            with self.subTest(provider=provider):
                saved = getattr(config, key)
                saved_retries = config.LLM_MAX_RETRIES
                config.LLM_PROVIDER = provider
                setattr(config, key, value)
                # One attempt, so the backoff does not make this suite slow.
                config.LLM_MAX_RETRIES = 1
                try:
                    self.assertTrue(llm.is_configured())
                    # It must reach a provider call rather than falling off the
                    # end of the dispatch as an unknown name.
                    with mock.patch.object(llm.requests, "get",
                                           return_value=_catalogue("m-70b-instruct")), \
                         mock.patch.object(llm.requests, "post") as post:
                        post.side_effect = llm.requests.RequestException("no network")
                        with self.assertRaises(llm.LLMError) as caught:
                            llm.complete("hi")
                    self.assertNotIn("Unknown LLM_PROVIDER", str(caught.exception))
                finally:
                    setattr(config, key, saved)
                    config.LLM_MAX_RETRIES = saved_retries

    def test_the_hint_names_every_provider(self):
        config.LLM_PROVIDER = "nonsense"
        self.assertFalse(llm.is_configured())
        hint = llm.configuration_hint()
        for name in ("GROQ_API_KEY", "HF_TOKEN", "GEMINI_API_KEY", "ollama"):
            self.assertIn(name, hint)

    def test_huggingface_spelled_out_is_the_same_provider(self):
        """A plausible spelling should not silently select nothing."""
        saved = os.environ.get("LLM_PROVIDER")
        os.environ["LLM_PROVIDER"] = "huggingface"
        try:
            importlib.reload(config)
            self.assertEqual(config.LLM_PROVIDER, "hf")
        finally:
            if saved is None:
                os.environ.pop("LLM_PROVIDER", None)
            else:
                os.environ["LLM_PROVIDER"] = saved
            importlib.reload(config)

    def test_whisper_is_excluded_on_hugging_face_too(self):
        """HF's exclusions extend Groq's rather than replacing them."""
        for token in config.GROQ_MODEL_EXCLUDE:
            self.assertIn(token, config.HF_MODEL_EXCLUDE)
        self.assertFalse(llm._usable("openai/whisper-large-v3", "hf"))
        self.assertFalse(llm._usable("black-forest-labs/FLUX.1-schnell", "hf"))
        self.assertTrue(llm._usable("meta-llama/Llama-3.3-70B-Instruct", "hf"))


if __name__ == "__main__":
    unittest.main()
