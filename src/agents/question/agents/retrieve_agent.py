#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
RetrieveAgent - Responsible for processing user-provided context.

Uses unified BaseAgent for LLM calls and configuration management.
"""

import json
from typing import Any

from src.agents.base_agent import BaseAgent


class RetrieveAgent(BaseAgent):
    """
    Agent responsible for processing user-provided context.

    Responsibilities:
    - Extract and format user-provided context/reference materials
    - Return formatted context for question generation
    """

    def __init__(
        self,
        language: str = "en",
        **kwargs,
    ):
        """
        Initialize RetrieveAgent.

        Args:
            language: Language for prompts ("en" or "zh")
            **kwargs: Additional arguments passed to BaseAgent
        """
        super().__init__(
            module_name="question",
            agent_name="retrieve_agent",
            language=language,
            **kwargs,
        )

    async def process(
        self,
        requirement: dict[str, Any] | str,
        context: str | None = None,
    ) -> dict[str, Any]:
        """
        Main processing: format user-provided context.

        Args:
            requirement: Question requirement (dict or string)
            context: Optional user-provided context/reference materials

        Returns:
            Dict with:
                - summary: Formatted context for question generation
                - has_content: Whether context is available
        """
        self.logger.info("Processing user-provided context")

        # Extract context from requirement if not provided separately
        if context is None and isinstance(requirement, dict):
            context = requirement.get("context", "")

        # Format context
        if context and context.strip():
            summary = f"Reference Materials:\n{context.strip()}"
            has_content = True
            self.logger.info(f"Using user-provided context ({len(context)} characters)")
        else:
            summary = "No reference materials provided. Generate questions based on the knowledge point."
            has_content = False
            self.logger.info("No context provided, generating from knowledge point only")

        return {
            "summary": summary,
            "has_content": has_content,
        }
