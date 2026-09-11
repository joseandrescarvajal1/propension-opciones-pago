"""Fábrica del LLM en Vertex AI (Gemini). Sin llaves: autenticación por ADC o cuenta de servicio de Cloud Run."""

from __future__ import annotations

import os
import warnings
from functools import lru_cache

warnings.filterwarnings("ignore", category=DeprecationWarning)


@lru_cache(maxsize=8)
def llm(temperature: float = 0.2, modelo: str | None = None, pensamiento: int | None = None):
    """Modelo principal (LLM_MODELO) en el endpoint global de Vertex (LLM_REGION), que da la menor latencia."""
    from langchain_google_genai import ChatGoogleGenerativeAI

    return ChatGoogleGenerativeAI(model=modelo or os.environ.get("LLM_MODELO", "gemini-2.5-flash"), vertexai=True,
                                  project=os.environ.get("GCP_PROJECT_ID", "propension-opciones-pago"), location=os.environ.get("LLM_REGION", "global"),
                                  temperature=temperature, max_retries=6, timeout=90, **({"thinking_budget": pensamiento} if pensamiento is not None else {}))


def llm_guardrail():
    """Modelo pequeño y sin razonamiento para los guardrails (LLM_MODELO_GUARDRAIL)."""
    return llm(0.0, modelo=os.environ.get("LLM_MODELO_GUARDRAIL", "gemini-2.5-flash-lite"), pensamiento=0)


def llm_juez():
    """Modelo principal sin razonamiento para el juez de salida (más criterio que el lite, ~2 s)."""
    return llm(0.0, pensamiento=0)
