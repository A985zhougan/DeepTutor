#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
AgentCoordinator - Orchestrates question generation workflow.

Simplified version without knowledge base retrieval:
- Uses specialized agents: RetrieveAgent (context processing), GenerateAgent
- No knowledge base dependency
- All questions are generated based on user input and optional context
"""

from collections.abc import Callable
from datetime import datetime
import json
from pathlib import Path
import sys
from typing import Any

# Add project root for imports
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from src.logging import Logger, get_logger
from src.services.config import load_config_with_main

from .agents.generate_agent import GenerateAgent
from .agents.retrieve_agent import RetrieveAgent


class AgentCoordinator:
    """
    Coordinate question generation workflow using specialized agents.

    Workflow:
    1. RetrieveAgent: Process user-provided context
    2. Plan: Generate question plan with focuses
    3. GenerateAgent: Generate questions
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        api_version: str | None = None,
        max_rounds: int = 10,  # Kept for backward compatibility, but not used
        output_dir: str | None = None,
        language: str = "en",
    ):
        """
        Initialize the coordinator.

        Args:
            api_key: API key (optional, loaded from config if not provided)
            base_url: API endpoint (optional)
            api_version: API version for Azure (optional)
            max_rounds: Deprecated, kept for backward compatibility
            output_dir: Output directory for results
            language: Language for prompts ("en" or "zh")
        """
        self.output_dir = output_dir
        self.language = language

        # Store API credentials for creating agents
        self._api_key = api_key
        self._base_url = base_url
        self._api_version = api_version

        # Load configuration
        self.config = load_config_with_main("question_config.yaml", project_root)

        # Initialize logger
        log_dir = self.config.get("paths", {}).get("user_log_dir") or self.config.get(
            "logging", {}
        ).get("log_dir")
        self.logger: Logger = get_logger("QuestionCoordinator", log_dir=log_dir)

        # Get config values
        question_cfg = self.config.get("question", {})
        self.max_parallel_questions = question_cfg.get("max_parallel_questions", 1)

        # Token tracking - will be updated from BaseAgent shared stats
        self.token_stats = {
            "model": "gpt-4o-mini",
            "calls": 0,
            "tokens": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "cost": 0.0,
        }

        # WebSocket callback for streaming updates
        self._ws_callback: Callable | None = None

    def _update_token_stats(self):
        """Update token_stats from BaseAgent's shared LLMStats for the question module."""
        from src.agents.base_agent import BaseAgent

        try:
            stats = BaseAgent.get_stats("question")
            summary = stats.get_summary()

            self.token_stats = {
                "model": summary.get("model", "gpt-4o-mini"),
                "calls": summary.get("calls", 0),
                "tokens": summary.get("total_tokens", 0),
                "input_tokens": summary.get("input_tokens", 0),
                "output_tokens": summary.get("output_tokens", 0),
                "cost": summary.get("cost", 0.0),
            }
        except Exception as e:
            self.logger.debug(f"Failed to update token stats: {e}")

    def set_ws_callback(self, callback: Callable):
        """Set WebSocket callback for streaming updates to frontend."""
        self._ws_callback = callback

    async def _send_ws_update(self, update_type: str, data: dict[str, Any]):
        """Send update via WebSocket callback if available."""
        if self._ws_callback:
            try:
                await self._ws_callback({"type": update_type, **data})
            except Exception as e:
                self.logger.debug(f"Failed to send WS update: {e}")

    def _create_retrieve_agent(self) -> RetrieveAgent:
        """Create a RetrieveAgent instance."""
        return RetrieveAgent(
            language=self.language,
            api_key=self._api_key,
            base_url=self._base_url,
            api_version=self._api_version,
        )

    def _create_generate_agent(self) -> GenerateAgent:
        """Create a GenerateAgent instance."""
        return GenerateAgent(
            language=self.language,
            api_key=self._api_key,
            base_url=self._base_url,
            api_version=self._api_version,
        )

    # =========================================================================
    # Main Entry Points
    # =========================================================================

    async def generate_question(
        self,
        requirement: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Generate a single question.

        This is used by Mimic mode and for single question generation.

        Args:
            requirement: Question requirement dict

        Returns:
            Dict with:
                - success: bool
                - question: Generated question dict
                - rounds: Always 1 (no iteration)
        """
        self.logger.section("Single Question Generation")
        self.logger.info(f"Knowledge point: {requirement.get('knowledge_point', 'N/A')}")

        await self._send_ws_update(
            "progress", {"stage": "generating", "progress": {"status": "initializing"}}
        )

        # Step 1: Process context
        retrieve_agent = self._create_retrieve_agent()
        context_result = await retrieve_agent.process(
            requirement=requirement,
            context=requirement.get("context"),
        )

        context = context_result["summary"]

        # Step 2: Generate question
        generate_agent = self._create_generate_agent()

        # Check if this is mimic mode (has reference_question)
        reference_question = requirement.get("reference_question")

        gen_result = await generate_agent.process(
            requirement=requirement,
            context=context,
            reference_question=reference_question,
        )

        if not gen_result.get("success"):
            self.logger.error(f"Question generation failed: {gen_result.get('error')}")
            return {
                "success": False,
                "error": gen_result.get("error", "Generation failed"),
            }

        question = gen_result["question"]

        self.logger.success("Question generated successfully")

        # Build result
        result = {
            "success": True,
            "question": question,
            "rounds": 1,  # No iteration
        }

        # Save to disk if output_dir is set
        if self.output_dir:
            self._save_question_result(result, requirement)

        # Update token stats from shared LLMStats
        self._update_token_stats()

        return result

    async def generate_questions_custom(
        self,
        requirement: dict[str, Any],
        num_questions: int,
    ) -> dict[str, Any]:
        """
        Custom mode: Generate multiple questions from a requirement.

        Flow:
        1. Processing: Process user-provided context
        2. Planning: Generate question plan with focuses
        3. Generating: Generate each question

        Args:
            requirement: Base requirement dict (knowledge_point, difficulty, question_type, context)
            num_questions: Number of questions to generate

        Returns:
            Summary dict with all results
        """
        if num_questions <= 0:
            raise ValueError("num_questions must be greater than zero")

        self.logger.section(f"Custom Mode Generation: {num_questions} question(s)")

        # Create batch directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        batch_dir = Path(self.output_dir) / f"batch_{timestamp}" if self.output_dir else None
        if batch_dir:
            batch_dir.mkdir(parents=True, exist_ok=True)

        # =====================================================================
        # Stage 1: Processing Context
        # =====================================================================
        self.logger.stage("Stage 1: Processing Context")
        await self._send_ws_update(
            "progress",
            {"stage": "processing", "progress": {"status": "processing"}, "total": num_questions},
        )

        retrieve_agent = self._create_retrieve_agent()
        context_result = await retrieve_agent.process(
            requirement=requirement,
            context=requirement.get("context"),
        )

        context = context_result["summary"]

        # =====================================================================
        # Stage 2: Planning
        # =====================================================================
        self.logger.stage("Stage 2: Planning")
        await self._send_ws_update(
            "progress", {"stage": "planning", "progress": {"status": "creating_plan"}}
        )

        plan = await self._generate_question_plan(requirement, context, num_questions)
        focuses = plan.get("focuses", [])

        # Save plan.json
        if batch_dir:
            self._save_plan_json(batch_dir, plan)

        await self._send_ws_update("plan_ready", {"plan": plan, "focuses": focuses})

        # =====================================================================
        # Stage 3: Generating
        # =====================================================================
        self.logger.stage("Stage 3: Generating")
        await self._send_ws_update(
            "progress",
            {"stage": "generating", "progress": {"current": 0, "total": num_questions}},
        )

        results = []
        failures = []

        generate_agent = self._create_generate_agent()

        for idx, focus in enumerate(focuses):
            question_id = focus.get("id", f"q_{idx + 1}")
            self.logger.info(f"Generating question {question_id}")

            await self._send_ws_update(
                "question_update",
                {
                    "question_id": question_id,
                    "status": "generating",
                    "focus": focus.get("focus", ""),
                },
            )

            # Generate question
            gen_result = await generate_agent.process(
                requirement=requirement,
                context=context,
                focus=focus,
            )

            if not gen_result.get("success"):
                self.logger.error(f"Failed to generate question {question_id}")
                failures.append(
                    {
                        "question_id": question_id,
                        "error": gen_result.get("error", "Unknown error"),
                    }
                )
                await self._send_ws_update(
                    "question_update", {"question_id": question_id, "status": "error"}
                )
                continue

            question = gen_result["question"]

            # Build validation dict (for frontend compatibility)
            validation = {
                "decision": "approve",
            }

            # Save result
            result = {
                "question_id": question_id,
                "focus": focus,
                "question": question,
                "validation": validation,  # For frontend compatibility
            }

            if batch_dir:
                self._save_custom_question_result(batch_dir, result)

            results.append(result)

            await self._send_ws_update(
                "question_update", {"question_id": question_id, "status": "done"}
            )
            await self._send_ws_update(
                "result",
                {
                    "question_id": question_id,
                    "question": question,
                    "validation": validation,  # Frontend expects 'validation'
                    "focus": focus,
                    "index": idx,
                },
            )
            await self._send_ws_update(
                "progress",
                {"stage": "generating", "progress": {"current": idx + 1, "total": num_questions}},
            )

        # =====================================================================
        # Complete
        # =====================================================================
        summary = {
            "success": len(results) == num_questions,
            "requested": num_questions,
            "completed": len(results),
            "failed": len(failures),
            "plan": plan,
            "results": results,
            "failures": failures,
        }

        if batch_dir:
            summary_file = batch_dir / "summary.json"
            with open(summary_file, "w", encoding="utf-8") as f:
                json.dump(summary, f, indent=2, ensure_ascii=False)
            summary["output_dir"] = str(batch_dir)

        # Update token stats from shared LLMStats
        self._update_token_stats()

        await self._send_ws_update(
            "progress",
            {
                "stage": "complete",
                "completed": len(results),
                "failed": len(failures),
                "total": num_questions,
            },
        )

        self.logger.section("Generation Summary")
        self.logger.info(f"Requested: {num_questions}")
        self.logger.info(f"Completed: {len(results)}")
        self.logger.info(f"Failed: {len(failures)}")

        return summary

    # =========================================================================
    # Helper Methods
    # =========================================================================

    async def _generate_question_plan(
        self,
        requirement: dict[str, Any],
        context: str,
        num_questions: int,
    ) -> dict[str, Any]:
        """
        Generate a question plan with distinct focuses.

        Args:
            requirement: Base requirement
            context: User-provided context or default message
            num_questions: Number of questions

        Returns:
            Plan dict with focuses array
        """
        from src.services.llm import complete as llm_complete
        from src.services.llm.config import get_llm_config

        llm_config = get_llm_config()

        system_prompt = (
            "You are an educational content planner. Create distinct question focuses "
            "that test different aspects of the same topic.\n\n"
            "CRITICAL: Return ONLY valid JSON. Do not wrap in markdown code blocks.\n"
            'Output JSON with key "focuses" containing an array of objects, each with:\n'
            '- "id": string like "q_1", "q_2"\n'
            '- "focus": string describing what aspect to test\n'
            f'- "type": "{requirement.get("question_type", "written")}"'
        )

        # Truncate context consistently (4000 chars)
        truncated_context = context[:4000] if len(context) > 4000 else context
        truncation_suffix = "...[truncated]" if len(context) > 4000 else ""

        user_prompt = (
            f"Topic: {requirement.get('knowledge_point', '')}\n"
            f"Difficulty: {requirement.get('difficulty', 'medium')}\n"
            f"Question Type: {requirement.get('question_type', 'written')}\n"
            f"Number: {num_questions}\n\n"
            f"Context:\n{truncated_context}{truncation_suffix}\n\n"
            f"Generate exactly {num_questions} distinct focuses in JSON."
        )

        try:
            response = await llm_complete(
                prompt=user_prompt,
                system_prompt=system_prompt,
                model=llm_config.model,
                api_key=self._api_key or llm_config.api_key,
                base_url=self._base_url or llm_config.base_url,
                api_version=self._api_version,
                response_format={"type": "json_object"},
                temperature=0.3,
            )

            data = json.loads(response)
            focuses = data.get("focuses", [])
            if not isinstance(focuses, list):
                focuses = []

        except Exception as e:
            self.logger.warning(f"Failed to generate plan: {e}")
            focuses = []

        # Fallback: create simple focuses
        if len(focuses) < num_questions:
            question_type = requirement.get("question_type", "written")
            for i in range(len(focuses), num_questions):
                focuses.append(
                    {
                        "id": f"q_{i + 1}",
                        "focus": f"Aspect {i + 1} of {requirement.get('knowledge_point', 'topic')}",
                        "type": question_type,
                    }
                )

        return {
            "knowledge_point": requirement.get("knowledge_point", ""),
            "difficulty": requirement.get("difficulty", "medium"),
            "question_type": requirement.get("question_type", "written"),
            "num_questions": num_questions,
            "focuses": focuses[:num_questions],
        }

    def _save_question_result(
        self,
        result: dict[str, Any],
        requirement: dict[str, Any],
    ) -> str | None:
        """Save a single question result to disk."""
        if not self.output_dir:
            return None

        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = Path(self.output_dir) / f"question_{timestamp}"
            output_path.mkdir(parents=True, exist_ok=True)

            # Save result.json
            with open(output_path / "result.json", "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, ensure_ascii=False)

            # Save question.md
            question = result.get("question", {})

            md_content = f"""# Generated Question

**Knowledge point**: {requirement.get("knowledge_point", question.get("knowledge_point", "N/A"))}
**Difficulty**: {requirement.get("difficulty", "N/A")}
**Type**: {question.get("question_type", "N/A")}

---

## Question
{question.get("question", "")}

"""
            if question.get("options"):
                md_content += "## Options\n"
                for key, value in question.get("options", {}).items():
                    md_content += f"- **{key}**: {value}\n"
                md_content += "\n"

            md_content += f"""
## Answer
{question.get("correct_answer", "")}

## Explanation
{question.get("explanation", "")}
"""

            with open(output_path / "question.md", "w", encoding="utf-8") as f:
                f.write(md_content)

            self.logger.info(f"Result saved to: {output_path}")
            return str(output_path)

        except Exception as e:
            self.logger.warning(f"Failed to save result: {e}")
            return None

    def _save_plan_json(self, batch_dir: Path, plan: dict[str, Any]):
        """Save plan.json for a batch."""
        plan_file = batch_dir / "plan.json"
        with open(plan_file, "w", encoding="utf-8") as f:
            json.dump(plan, f, indent=2, ensure_ascii=False)

    def _save_custom_question_result(
        self,
        batch_dir: Path,
        result: dict[str, Any],
    ):
        """Save a single question result in custom mode."""
        question_id = result.get("question_id", "q_unknown")
        question_dir = batch_dir / question_id
        question_dir.mkdir(parents=True, exist_ok=True)

        # Save result.json
        with open(question_dir / "result.json", "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        # Save question.md
        question = result.get("question", {})
        focus = result.get("focus", {})

        md_content = f"""# Generated Question

**Focus**: {focus.get("focus", "N/A")}
**Type**: {question.get("question_type", "N/A")}

---

## Question
{question.get("question", "")}

"""
        if question.get("options"):
            md_content += "## Options\n"
            for key, value in question.get("options", {}).items():
                md_content += f"- **{key}**: {value}\n"
            md_content += "\n"

        md_content += f"""
## Answer
{question.get("correct_answer", "")}

## Explanation
{question.get("explanation", "")}
"""

        with open(question_dir / "question.md", "w", encoding="utf-8") as f:
            f.write(md_content)
