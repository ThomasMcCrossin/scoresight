"""Small vision-language models (VLMs) and Florence-2, on CPU, with Hugging Face
transformers and PyTorch.

Engines (each a model family; the variant picks the model and options):

  florence2  Florence-2 (Microsoft, MIT), its "<OCR>" task (no prompt):
             florence2-base (0.23B parameters), florence2-large (0.77B).
  smolvlm    SmolVLM-Instruct (Hugging Face, Apache-2.0): smolvlm-256m,
             smolvlm-500m. The cheap VLM control (OCRBench 52.6 / 61.0).
  qwen-vl    Qwen3.5-0.8B and Qwen3-VL-2B-Instruct (Qwen, Apache-2.0), in
             non-thinking mode.

Variant suffixes:
  -wl  constrained decoding: only tokens made of the field type's characters
       (ocr_eval.fields.whitelist, what ScoreSight limits Tesseract to) and
       spaces, and the end of the answer, whose probability includes the
       masked tokens that only end a sentence or line (". ", "\\n"). The VLM
       counterpart of masking a CTC decoder; it also stops chat models from
       answering in sentences.
  -sq  (florence2) the crop is stretched to Florence's square 768x768 input as
       it is. Without it the crop is first centred on a square of its mean
       colour (letterboxed), which keeps the digits' proportions.

Chat models (smolvlm, qwen-vl) get one prompt per crop saying what the box
holds (a ScoreSight box has a field type), see crop_prompt(). Decoding is greedy
(temperature 0, no repetition penalty), at most MAX_NEW_TOKENS tokens. The
answer is cleaned up mechanically only (clean_answer(): its first line, without
surrounding quotes, backticks and a trailing period); a prediction's
info["answer"] keeps the raw answer when that changed it. The confidence is the
probability of the generated sequence (the product of the chosen tokens'
probabilities, the end of the answer included).

Whole frames: florence2 and qwen-vl also read every box of a frame in one call
(read_frame(), used by ocr_eval.frames).

Models are downloaded into the Hugging Face cache on first use, at the pinned
revisions below (HF_HUB_OFFLINE=1 uses only the cache). Environment variables:

  OCR_EVAL_TORCH_DEVICE   cpu (default), cuda or mps
  OCR_EVAL_TORCH_THREADS  PyTorch's intra-op threads (default: PyTorch's choice,
                          one per physical core)
  OCR_EVAL_VLM_BATCH      crops per generate() call (default: 8 for the chat
                          models, whose batched answers are identical and about
                          40% cheaper per crop; 1 for florence2, which batching
                          doesn't speed up on a CPU)

Install the requirements in a separate virtual environment. On Linux, install
PyTorch's CPU wheels first (PyPI's Linux wheels bundle CUDA, about 3 GB):
  pip install --index-url https://download.pytorch.org/whl/cpu torch==2.14.1 torchvision==0.29.1
  pip install -r requirements.txt $(python -m ocr_eval requirements qwen-vl)
"""

import json
import os
import re
from dataclasses import dataclass
from typing import ClassVar

import numpy as np

from ocr_eval.engines import Engine, EngineUnavailable, Recognition
from ocr_eval.fields import whitelist
from ocr_eval.frames import FrameField

REQUIREMENTS: list[str] = [
    "torch==2.14.1",
    "torchvision==0.29.1",
    "transformers==5.18.0",
]

MAX_NEW_TOKENS = 16
DEVICE_ENV = "OCR_EVAL_TORCH_DEVICE"
THREADS_ENV = "OCR_EVAL_TORCH_THREADS"
BATCH_ENV = "OCR_EVAL_VLM_BATCH"


@dataclass(frozen=True)
class ModelSpec:
    repo: str
    revision: str
    params: str
    download: str
    license: str


MODELS = {
    "florence2-base": ModelSpec(
        "florence-community/Florence-2-base",
        "00921df66db728a9ceb750f5eca43e5c203a2051",
        "0.23B",
        "0.44 GB",
        "MIT",
    ),
    "florence2-large": ModelSpec(
        "florence-community/Florence-2-large",
        "4271c66b88cdbc05735372ec13b2360108de5317",
        "0.77B",
        "1.5 GB",
        "MIT",
    ),
    "smolvlm-256m": ModelSpec(
        "HuggingFaceTB/SmolVLM-256M-Instruct",
        "7e3e67edbbed1bf9888184d9df282b700a323964",
        "0.26B",
        "0.49 GB",
        "Apache-2.0",
    ),
    "smolvlm-500m": ModelSpec(
        "HuggingFaceTB/SmolVLM-500M-Instruct",
        "a7da5b986cb59b408707209984f360a5f4ad7e47",
        "0.51B",
        "0.97 GB",
        "Apache-2.0",
    ),
    "qwen3.5-0.8b": ModelSpec(
        "Qwen/Qwen3.5-0.8B",
        "2fc06364715b967f1860aea9cf38778875588b17",
        "0.9B",
        "1.7 GB",
        "Apache-2.0",
    ),
    "qwen3-vl-2b": ModelSpec(
        "Qwen/Qwen3-VL-2B-Instruct",
        "89644892e4d85e24eaac8bacfd4f463576704203",
        "2.1B",
        "4.1 GB",
        "Apache-2.0",
    ),
}

# --- prompts and answers (pure functions, no torch) ---------------------------------

# what a box of each field type holds, for the prompts
FIELD_DESCRIPTIONS = {
    "score": "the score (a number)",
    "clock": "the game clock (digits with ':' or '.')",
    "period": "the period or quarter (a number)",
    "number": "the number",
    "text": "the word",
    "other": "the text",
}


def crop_prompt(field_type: str) -> str:
    """The question a chat model is asked about one crop."""
    what = FIELD_DESCRIPTIONS.get(field_type, "the text")
    return (
        f"This image is cropped from a scoreboard. Read {what} shown in it. "
        "Answer with only the characters on the display, exactly as shown."
    )


_QUOTES = "`'\"“”‘’"


def clean_answer(text: str | None) -> str:
    """A model's answer as a reading: its first non-empty line, without
    surrounding spaces, quotes or backticks, and without a trailing period (a
    clock's '.' is always followed by a digit)."""
    for line in (text or "").splitlines():
        answer = line.strip().strip(_QUOTES).strip()
        if answer:
            if answer.endswith(".") and not answer.endswith(".."):
                answer = answer[:-1].rstrip()
            return answer
    return ""


def allowed_token_ids(token_texts: list[str], chars: str) -> list[int]:
    """The ids of the tokens whose text (decoded on its own) is made only of
    the given characters and spaces. Space-only tokens are allowed: tokenizers
    that split digits off (SmolLM2's) start an answer with a " " token, and
    masking it derails the answer; spaces are ignored by the scoring."""
    allowed = set(chars) | {" "}
    return [
        token_id
        for token_id, text in enumerate(token_texts)
        if text and all(char in allowed for char in text)
    ]


# characters models end an answer with before the end-of-answer token
TERMINATOR_CHARS = ".\n\r。"


def terminator_token_ids(token_texts: list[str]) -> list[int]:
    """The ids of the tokens that only end a line or sentence (a period, a
    newline, with spaces). Constrained decoding counts their probability as the
    end of the answer when it masks them: models often answer "0." or "90\\n"
    before stopping, and masking the period alone makes them go on ("0000")."""
    return [
        token_id
        for token_id, text in enumerate(token_texts)
        if text
        and any(char in TERMINATOR_CHARS for char in text)
        and all(char in TERMINATOR_CHARS or char == " " for char in text)
    ]


def letterbox(crop: np.ndarray) -> np.ndarray:
    """The crop centred on a square canvas of its mean colour."""
    height, width = crop.shape[:2]
    side = max(height, width)
    color = crop.reshape(-1, crop.shape[2]).mean(axis=0).astype(np.uint8)
    canvas = np.empty((side, side, crop.shape[2]), np.uint8)
    canvas[:] = color
    top, left = (side - height) // 2, (side - width) // 2
    canvas[top : top + height, left : left + width] = crop
    return canvas


# --- whole frames ------------------------------------------------------------------


def relative_box(box, width: int, height: int) -> list[int]:
    """x, y, w, h in pixels -> [x1, y1, x2, y2] on a 0-1000 scale (the
    coordinates Qwen3-VL and Qwen3.5 are trained on)."""
    x, y, w, h = box
    return [
        max(0, min(1000, round(x * 1000 / width))),
        max(0, min(1000, round(y * 1000 / height))),
        max(0, min(1000, round((x + w) * 1000 / width))),
        max(0, min(1000, round((y + h) * 1000 / height))),
    ]


def frame_prompt(fields: list[FrameField], width: int, height: int, mode: str) -> str:
    """The question a chat model is asked about a whole frame: read every
    field, answer with JSON keyed by the field's number (1, 2, ...)."""
    lines = []
    for number, field in enumerate(fields, start=1):
        what = FIELD_DESCRIPTIONS.get(field.field_type, "the text")
        if field.role:
            what = f"{field.role}: {what}"
        if mode == "boxes":
            lines.append(f"{number}: {relative_box(field.box, width, height)} ({what})")
        else:
            lines.append(f"{number}: ({what})")
    if mode == "boxes":
        intro = (
            "This photo shows a scoreboard. Read the text inside each of these "
            "boxes, given as [x1, y1, x2, y2] on a 0-1000 scale of the image's "
            "width and height:"
        )
    else:
        intro = (
            "This photo shows a scoreboard with numbered magenta boxes drawn on "
            "it. Read the text inside each box:"
        )
    example = ", ".join(f'"{n}": "..."' for n in range(1, min(len(fields), 2) + 1))
    return (
        intro
        + "\n"
        + "\n".join(lines)
        + "\nAnswer with only a JSON object that maps each box number to exactly "
        f'the characters shown in it, like {{{example}}}. Use "" for a box you '
        "can't read."
    )


# The start of the answer to a frame prompt, written for the model: without it
# small Qwen models tend to answer in their grounding format (a list of
# {"bbox_2d": ..., "label": ...}) instead of the JSON object asked for.
FRAME_ANSWER_PREFIX = '{"1": "'

_TEXT_KEYS = ("text_content", "text", "label", "content", "value")


def _json_value(text: str):
    """The first JSON object or list in text (after any code fence)."""
    fenced = re.search(r"```(?:json)?\s*(.*?)(?:```|$)", text, re.DOTALL)
    if fenced:
        text = fenced.group(1)
    starts = [i for i in (text.find("{"), text.find("[")) if i >= 0]
    if not starts:
        raise ValueError("no JSON")
    value, _ = json.JSONDecoder().raw_decode(text[min(starts) :])
    return value


def parse_frame_answer(
    answer: str, fields: list[FrameField], width: int, height: int
) -> tuple[list[str], str | None]:
    """The text of each field from a model's answer to frame_prompt(), and an
    error message when the answer wasn't the JSON object asked for. Fallbacks:
    "number": "text" pairs picked out of broken JSON, and a grounding list
    ([{"bbox_2d": [x1, y1, x2, y2] (0-1000), "text_content": ...}]), whose
    texts go to the fields their boxes fall in. Missing fields are ""."""
    text = (answer or "").strip()
    values: dict = {}
    error = None
    try:
        parsed = _json_value(text)
        if isinstance(parsed, list):
            regions = []
            for item in parsed:
                box = item.get("bbox_2d") if isinstance(item, dict) else None
                label = next(
                    (item[k] for k in _TEXT_KEYS if isinstance(item.get(k), str)), ""
                )
                if isinstance(box, list) and len(box) == 4 and label:
                    x1, y1, x2, y2 = (float(v) for v in box)
                    sx, sy = width / 1000.0, height / 1000.0
                    regions.append(
                        ([x1 * sx, y1 * sy, x2 * sx, y1 * sy, x2 * sx, y2 * sy], label)
                    )
            return assign_regions(fields, regions), "a grounding list, not an object"
        if not isinstance(parsed, dict):
            raise ValueError("not a JSON object")
        values = parsed
    except (ValueError, AttributeError, TypeError) as e:
        error = str(e) or type(e).__name__
        values = dict(re.findall(r'"(\d+)"\s*:\s*"((?:[^"\\]|\\.)*)"', text))
    texts = []
    for number in range(1, len(fields) + 1):
        value = values.get(str(number), "")
        texts.append(clean_answer("" if value is None else str(value)))
    return texts, error


def assign_regions(
    fields: list[FrameField], regions: list[tuple[list[float], str]]
) -> list[str]:
    """Spotted text regions (polygon points x1, y1, x2, y2, ..., text) -> the
    text of each field: the words whose centre is inside the field's box, left
    to right. A region's words are placed along its width in proportion to
    their characters (spotters often merge neighbouring words into a line)."""
    words = []
    for points, text in regions:
        xs, ys = points[0::2], points[1::2]
        left, right = min(xs), max(xs)
        centre_y = (min(ys) + max(ys)) / 2
        length = max(1, len(text))
        for match in re.finditer(r"\S+", text):
            middle = (match.start() + match.end()) / 2 / length
            words.append((left + middle * (right - left), centre_y, match.group()))
    texts = []
    for field in fields:
        x, y, w, h = field.box
        inside = sorted(
            (cx, word)
            for cx, cy, word in words
            if x <= cx <= x + w and y <= cy <= y + h
        )
        texts.append(" ".join(word for _, word in inside))
    return texts


def draw_marks(frame: np.ndarray, fields: list[FrameField]) -> np.ndarray:
    """A copy of the frame with each field's box drawn in magenta and numbered."""
    import cv2

    marked = frame.copy()
    thickness = max(1, round(max(frame.shape[:2]) / 600))
    for number, field in enumerate(fields, start=1):
        x, y, w, h = field.box
        cv2.rectangle(
            marked,
            (x - thickness, y - thickness),
            (x + w + thickness, y + h + thickness),
            (255, 0, 255),
            thickness,
        )
        label = str(number)
        scale = max(0.4, min(1.2, h / 40))
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, scale, 1)
        top = max(0, y - th - 4 - thickness)
        cv2.rectangle(marked, (x, top), (x + tw + 4, top + th + 4), (255, 0, 255), -1)
        cv2.putText(
            marked,
            label,
            (x + 2, top + th + 2),
            cv2.FONT_HERSHEY_SIMPLEX,
            scale,
            (255, 255, 255),
            1,
            cv2.LINE_AA,
        )
    return marked


# --- the engines -----------------------------------------------------------------


def _env_int(name: str) -> int | None:
    value = os.environ.get(name, "").strip()
    if not value:
        return None
    try:
        return max(1, int(value))
    except ValueError:
        return None


class _TransformersVLM(Engine):
    """Shared loading, generation and confidence of the transformers engines.
    Not registered itself (no name)."""

    runtime = "PyTorch (transformers), CPU, fp32, greedy decoding"
    imports = ("torch", "transformers", "PIL")
    # the engine's models (MODELS keys); a variant is a model plus options
    models: ClassVar[tuple[str, ...]] = ()
    # the modes read_frame() supports (ocr_eval.frames)
    frame_modes: ClassVar[tuple[str, ...]] = ()

    def __init__(self, variant: str | None = None):
        super().__init__(variant)
        self.model_key = next(
            key
            for key in sorted(self.models, key=len, reverse=True)
            if self.variant == key or self.variant.startswith(key + "-")
        )
        suffix = self.variant[len(self.model_key) :]
        self.flags = {flag for flag in suffix.split("-") if flag}
        self.spec = MODELS[self.model_key]
        self.batch_size = _env_int(BATCH_ENV) or type(self).batch_size
        self.model = None
        self.processor = None
        self.device = "cpu"
        self._torch = None
        self._masks: dict[str, object] = {}
        self._token_texts: list[str] | None = None

    # loading

    def load(self) -> None:
        try:
            import torch
            import transformers
        except ImportError as e:
            raise EngineUnavailable(f"missing Python modules: {e}") from None
        self._torch = torch
        self._transformers = transformers
        threads = _env_int(THREADS_ENV)
        if threads:
            torch.set_num_threads(threads)
        self.device = os.environ.get(DEVICE_ENV, "").strip() or "cpu"
        try:
            self.model, self.processor = self._load_model(transformers, torch)
        except (OSError, ValueError, ImportError) as e:
            raise EngineUnavailable(
                f"can't load {self.spec.repo}@{self.spec.revision[:8]}: "
                f"{type(e).__name__}: {e}"
            ) from None
        self.model.to(self.device)
        self.model.eval()
        if "wl" in self.flags:
            # the masks take seconds (every token is decoded): part of loading
            head = self.model.get_output_embeddings()
            vocab_size = (
                head.weight.shape[0] if head is not None else len(self.tokenizer)
            )
            for field_type in FIELD_DESCRIPTIONS:
                self._mask(field_type, vocab_size)
            self._terminators(vocab_size)

    def _dtype(self, torch):
        # fp32 on a CPU: bf16 matmuls are slower there without AMX
        return torch.float32 if self.device == "cpu" else torch.bfloat16

    def _load_model(self, transformers, torch):
        raise NotImplementedError

    def close(self) -> None:
        self.model = None
        self.processor = None
        self._masks.clear()

    def info(self) -> dict:
        info = super().info()
        info.update(
            model=self.spec.repo,
            revision=self.spec.revision,
            size=f"{self.spec.params} parameters, {self.spec.download} download",
            license=self.spec.license,
            options=sorted(self.flags),
        )
        if self._torch is not None:
            info["version"] = (
                f"torch {self._torch.__version__}, "
                f"transformers {self._transformers.__version__}"
            )
            info["device"] = self.device
            info["threads"] = self._torch.get_num_threads()
            info["runtime"] = (
                f"PyTorch (transformers), {self.device}, "
                f"{'fp32' if self.device == 'cpu' else 'bf16'}, greedy decoding, "
                f"{self._torch.get_num_threads()} threads"
            )
        return info

    # generation

    @property
    def tokenizer(self):
        return getattr(self.processor, "tokenizer", self.processor)

    @staticmethod
    def _ids(*values) -> set[int]:
        ids = set()
        for value in values:
            if isinstance(value, int):
                ids.add(value)
            elif value:
                ids.update(v for v in value if isinstance(v, int))
        return ids

    def _eos_ids(self) -> set[int]:
        return self._ids(
            self.model.generation_config.eos_token_id, self.tokenizer.eos_token_id
        )

    def _start_ids(self) -> set[int]:
        if not self.model.config.is_encoder_decoder:
            return set()
        return self._ids(
            self.tokenizer.bos_token_id,
            self.model.generation_config.decoder_start_token_id,
        )

    def _special_ids(self) -> set[int]:
        """Tokens the constrained decoding always allows: the end of the answer
        (and the start, for encoder-decoder models)."""
        return self._eos_ids() | self._start_ids()

    def _token_mask(self, key: str, ids, vocab_size: int):
        if key not in self._masks:
            mask = self._torch.zeros(vocab_size, dtype=self._torch.bool)
            mask[[i for i in ids if i < vocab_size]] = True
            self._masks[key] = mask
        return self._masks[key]

    def _texts(self) -> list[str]:
        """Every token's text, decoded on its own."""
        if self._token_texts is None:
            tokenizer = self.tokenizer
            self._token_texts = tokenizer.batch_decode(
                [[i] for i in range(len(tokenizer))],
                skip_special_tokens=False,
                clean_up_tokenization_spaces=False,
            )
        return self._token_texts

    def _mask(self, field_type: str, vocab_size: int):
        """The bool mask (vocab_size,) of the tokens allowed for a field type."""
        chars = whitelist(field_type)
        key = f"{chars}:{vocab_size}"
        if key in self._masks:
            return self._masks[key]
        ids = allowed_token_ids(self._texts(), chars) + sorted(self._special_ids())
        return self._token_mask(key, ids, vocab_size)

    def _terminators(self, vocab_size: int):
        """The bool mask (vocab_size,) of terminator_token_ids()."""
        key = f"terminators:{vocab_size}"
        if key in self._masks:
            return self._masks[key]
        return self._token_mask(key, terminator_token_ids(self._texts()), vocab_size)

    def _logits_processors(self, field_types: list[str]):
        if "wl" not in self.flags or not field_types:
            return None
        torch = self._torch
        transformers = self._transformers
        engine = self
        # the end of the answer the chat template uses (the first one listed)
        eos = self.model.generation_config.eos_token_id
        eos = eos[0] if isinstance(eos, (list, tuple)) else eos
        if eos is None:
            eos = self.tokenizer.eos_token_id

        class AllowedTokens(transformers.LogitsProcessor):
            def __call__(self, input_ids, scores):
                vocab_size = scores.shape[-1]
                masks = torch.stack(
                    [engine._mask(ft, vocab_size) for ft in field_types]
                ).to(scores.device)
                # a masked terminator ("0." / "90\n") counts as the end
                moved = engine._terminators(vocab_size).to(scores.device) & ~masks
                ending = torch.logsumexp(
                    scores.masked_fill(~moved, float("-inf")), dim=-1
                )
                scores = scores.clone()
                scores[:, eos] = torch.logaddexp(scores[:, eos], ending)
                return scores.masked_fill(~masks, float("-inf"))

        return transformers.LogitsProcessorList([AllowedTokens()])

    def _generate(self, inputs, field_types, max_new_tokens=MAX_NEW_TOKENS):
        """Greedy generation; returns (generated token ids (batch, steps), the
        sequence probabilities)."""
        torch = self._torch
        inputs = inputs.to(self.device)
        for key, value in list(inputs.items()):
            if torch.is_floating_point(value):
                inputs[key] = value.to(self._dtype(torch))
        with torch.inference_mode():
            output = self.model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                do_sample=False,
                num_beams=1,
                temperature=None,
                top_p=None,
                top_k=None,
                repetition_penalty=1.0,
                logits_processor=self._logits_processors(field_types),
                output_scores=True,
                return_dict_in_generate=True,
            )
        steps = len(output.scores)
        generated = output.sequences[:, -steps:] if steps else output.sequences[:, :0]
        return generated, self._confidences(generated, output.scores)

    def _confidences(self, generated, scores) -> list[float]:
        torch = self._torch
        batch = generated.shape[0]
        eos = torch.tensor(sorted(self._eos_ids()), dtype=torch.long)
        total = torch.zeros(batch, dtype=torch.float64)
        alive = torch.ones(batch, dtype=torch.bool)
        for step, step_scores in enumerate(scores):
            tokens = generated[:, step]
            logprobs = torch.log_softmax(step_scores.double(), dim=-1)
            chosen = logprobs[torch.arange(batch), tokens.to(logprobs.device)].cpu()
            total += torch.where(alive, chosen, torch.zeros_like(chosen))
            alive &= ~torch.isin(tokens.cpu(), eos)
        return [round(float(torch.exp(value)), 4) for value in total]

    def _decode(self, generated) -> list[str]:
        return self.tokenizer.batch_decode(generated, skip_special_tokens=True)

    @staticmethod
    def _pil(image: np.ndarray):
        from PIL import Image

        return Image.fromarray(np.ascontiguousarray(image[:, :, ::-1]))

    def _recognitions(self, answers, confidences) -> list[Recognition]:
        results = []
        for answer, confidence in zip(answers, confidences):
            text = clean_answer(answer)
            info = {"answer": answer} if text != answer.strip() else None
            results.append(Recognition(text, confidence, info))
        return results


class Florence2(_TransformersVLM):
    name = "florence2"
    models = ("florence2-base", "florence2-large")
    variants = (
        "florence2-base",
        "florence2-base-wl",
        "florence2-base-sq",
        "florence2-base-sq-wl",
        "florence2-large",
        "florence2-large-wl",
        "florence2-large-sq",
        "florence2-large-sq-wl",
    )
    default_variants = ("florence2-base", "florence2-base-wl")
    description = (
        "Florence-2 (Microsoft) with its <OCR> task: a DaViT image encoder at "
        "768x768 and a BART text decoder"
    )
    license = "MIT"
    frame_modes = ("spot",)

    def _load_model(self, transformers, torch):
        model = transformers.Florence2ForConditionalGeneration.from_pretrained(
            self.spec.repo, revision=self.spec.revision, dtype=self._dtype(torch)
        )
        processor = transformers.AutoProcessor.from_pretrained(
            self.spec.repo, revision=self.spec.revision
        )
        return model, processor

    def recognize(self, crops, field_types):
        images = [
            self._pil(crop if "sq" in self.flags else letterbox(crop)) for crop in crops
        ]
        inputs = self.processor(
            text=["<OCR>"] * len(images), images=images, return_tensors="pt"
        )
        generated, confidences = self._generate(inputs, field_types)
        return self._recognitions(self._decode(generated), confidences)

    def read_frame(self, frame, fields, mode="spot"):
        """<OCR_WITH_REGION> on the whole frame; each field gets the text of the
        regions centred in its box."""
        if mode != "spot":
            raise ValueError(f"{self.name} reads frames only in 'spot' mode")
        image = self._pil(frame)
        task = "<OCR_WITH_REGION>"
        inputs = self.processor(text=[task], images=[image], return_tensors="pt")
        generated, confidences = self._generate(inputs, [], max_new_tokens=1024)
        raw = self.tokenizer.batch_decode(generated, skip_special_tokens=False)[0]
        parsed = self.processor.post_process_generation(
            raw, task=task, image_size=image.size
        )[task]
        regions = [
            (list(points), label.replace("</s>", "").replace("<s>", ""))
            for points, label in zip(parsed["quad_boxes"], parsed["labels"])
        ]
        texts = assign_regions(fields, regions)
        recognitions = [Recognition(text, None) for text in texts]
        return recognitions, {
            "regions": [[round(v) for v in p] + [t] for p, t in regions],
            "confidence": confidences[0],
        }


class _ChatVLM(_TransformersVLM):
    """Chat-template VLMs: one prompt per crop."""

    # a frame's boxes in one call (left-padded; the answers are the same as one
    # by one)
    batch_size = 8

    # extra processor arguments for a crop
    crop_processor_kwargs: ClassVar[dict] = {}
    template_kwargs: ClassVar[dict] = {}

    def _load_model(self, transformers, torch):
        model = transformers.AutoModelForImageTextToText.from_pretrained(
            self.spec.repo, revision=self.spec.revision, dtype=self._dtype(torch)
        )
        processor = transformers.AutoProcessor.from_pretrained(
            self.spec.repo, revision=self.spec.revision
        )
        return model, processor

    def load(self) -> None:
        super().load()
        # left padding, so that every row of a batch generates from its end
        self.processor.tokenizer.padding_side = "left"

    def _chat(self, prompt: str) -> str:
        messages = [
            {
                "role": "user",
                "content": [{"type": "image"}, {"type": "text", "text": prompt}],
            }
        ]
        return self.processor.apply_chat_template(
            messages, add_generation_prompt=True, **self.template_kwargs
        )

    def _images_argument(self, images):
        return images

    def recognize(self, crops, field_types):
        images = [self._pil(crop) for crop in crops]
        prompts = [self._chat(crop_prompt(ft)) for ft in field_types]
        inputs = self.processor(
            text=prompts,
            images=self._images_argument(images),
            padding=True,
            return_tensors="pt",
            **self.crop_processor_kwargs,
        )
        generated, confidences = self._generate(inputs, field_types)
        return self._recognitions(self._decode(generated), confidences)


class SmolVLM(_ChatVLM):
    name = "smolvlm"
    models = ("smolvlm-256m", "smolvlm-500m")
    variants = tuple(m + o for m in models for o in ("", "-wl"))
    default_variants = ("smolvlm-256m", "smolvlm-256m-wl")
    description = (
        "SmolVLM-Instruct (Hugging Face): a SigLIP encoder and a SmolLM2 decoder; "
        "the cheap VLM control"
    )
    license = "Apache-2.0"
    # a crop is one 512 px tile (64 image tokens), not split into 4x4 tiles
    crop_processor_kwargs = {"do_image_splitting": False}

    def _images_argument(self, images):
        return [[image] for image in images]


class QwenVL(_ChatVLM):
    name = "qwen-vl"
    models = ("qwen3.5-0.8b", "qwen3-vl-2b")
    variants = tuple(m + o for m in models for o in ("", "-wl"))
    default_variants = ("qwen3.5-0.8b", "qwen3.5-0.8b-wl")
    description = (
        "Qwen3.5-0.8B (natively multimodal) and Qwen3-VL-2B-Instruct, non-thinking mode"
    )
    license = "Apache-2.0"
    template_kwargs = {"enable_thinking": False}
    frame_modes = ("boxes", "marks")

    def read_frame(self, frame, fields, mode="boxes"):
        """One prompt for every field of the frame (frame_prompt()), answered
        with JSON. mode "boxes" gives the boxes' coordinates; "marks" draws
        numbered boxes on the frame instead."""
        if mode not in self.frame_modes:
            raise ValueError(f"{self.name} has no frame mode {mode!r}")
        height, width = frame.shape[:2]
        image = frame if mode == "boxes" else draw_marks(frame, fields)
        prompt = self._chat(frame_prompt(fields, width, height, mode))
        inputs = self.processor(
            text=[prompt + FRAME_ANSWER_PREFIX],
            images=[self._pil(image)],
            padding=True,
            return_tensors="pt",
        )
        generated, confidences = self._generate(
            inputs, [], max_new_tokens=16 + 12 * len(fields)
        )
        answer = FRAME_ANSWER_PREFIX + self._decode(generated)[0]
        texts, error = parse_frame_answer(answer, fields, width, height)
        recognitions = [Recognition(text, None) for text in texts]
        info = {"answer": answer, "confidence": confidences[0]}
        if error:
            info["parse_error"] = error
        return recognitions, info
