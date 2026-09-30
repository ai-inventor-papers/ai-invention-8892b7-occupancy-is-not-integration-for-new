"""GPU phrase encoders: MiniLM (sentence-transformers, mean pooling) and SPECTER2 (base + proximity adapter, CLS pooling).
Both return L2-normalised float32 vectors. OOM fallback halves the batch size."""
from __future__ import annotations

import time

import numpy as np
import torch
from loguru import logger

MINILM = "sentence-transformers/all-MiniLM-L6-v2"
SPECTER2_BASE = "allenai/specter2_base"
SPECTER2_ADAPTER = "allenai/specter2"
SAPBERT = "cambridgeltl/SapBERT-from-PubMedBERT-fulltext"
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")


class Encoder:
    def __init__(self, name: str) -> None:
        self.name = name
        self.note = ""
        if DEVICE.type == "cuda":
            torch.cuda.set_per_process_memory_fraction(0.8)
        if name == "minilm":
            from sentence_transformers import SentenceTransformer
            self.st = SentenceTransformer(MINILM, device=str(DEVICE))
            if DEVICE.type == "cuda":
                self.st.half()
            self.kind = "st"
        elif name == "specter2":
            from transformers import AutoTokenizer
            self.tok = AutoTokenizer.from_pretrained(SPECTER2_BASE)
            try:
                from adapters import AutoAdapterModel
                m = AutoAdapterModel.from_pretrained(SPECTER2_BASE)
                m.load_adapter(SPECTER2_ADAPTER, source="hf", load_as="specter2", set_active=True)
                self.note = "specter2_base + proximity adapter (adapters.AutoAdapterModel), CLS pooling"
            except Exception as e:  # FALLBACK F2: base model without adapter
                logger.warning(f"SPECTER2 adapter failed ({e!r}); FALLBACK F2 base model")
                from transformers import AutoModel
                m = AutoModel.from_pretrained(SPECTER2_BASE)
                self.note = "FALLBACK F2: specter2_base without adapter, CLS pooling"
            self.model = m.to(DEVICE).eval()
            if DEVICE.type == "cuda":
                self.model.half()
            self.kind = "cls"
        elif name == "sapbert":
            from transformers import AutoModel, AutoTokenizer
            self.tok = AutoTokenizer.from_pretrained(SAPBERT)
            self.model = AutoModel.from_pretrained(SAPBERT).to(DEVICE).eval()
            if DEVICE.type == "cuda":
                self.model.half()
            self.kind = "cls"
            self.note = "SapBERT CLS pooling"
        else:
            raise ValueError(name)

    @torch.inference_mode()
    def encode(self, strings: list[str], batch: int = 512) -> np.ndarray:
        t0 = time.time()
        out = np.zeros((len(strings), self.dim()), dtype=np.float32)
        # sort by length for padding efficiency
        order = np.argsort([len(s) for s in strings])
        i = 0
        bs = batch
        while i < len(order):
            idx = order[i:i + bs]
            texts = [strings[j] for j in idx]
            try:
                if self.kind == "st":
                    v = self.st.encode(texts, batch_size=len(texts), convert_to_numpy=True, normalize_embeddings=True,
                                       show_progress_bar=False)
                else:
                    enc = self.tok(texts, padding=True, truncation=True, max_length=64, return_tensors="pt",
                                   return_token_type_ids=False).to(DEVICE)
                    h = self.model(**enc).last_hidden_state[:, 0, :].float()
                    v = torch.nn.functional.normalize(h, dim=-1).cpu().numpy()
            except torch.cuda.OutOfMemoryError:
                torch.cuda.empty_cache()
                bs = max(8, bs // 2)
                logger.warning(f"{self.name}: OOM, batch -> {bs}")
                continue
            out[idx] = v
            i += len(idx)
        logger.info(f"{self.name}: encoded {len(strings)} strings in {time.time() - t0:.1f}s")
        return out

    def dim(self) -> int:
        return 384 if self.name == "minilm" else 768
