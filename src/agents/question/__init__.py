"""
Question Generation System

Modular question generation using specialized agents:
- RetrieveAgent: Context processing
- GenerateAgent: Question generation
- AgentCoordinator: Workflow orchestration

Tools (moved to src/tools/question):
- parse_pdf_with_mineru
- extract_questions_from_paper
- mimic_exam_questions
"""

from .agents import GenerateAgent, RetrieveAgent
from .coordinator import AgentCoordinator

__all__ = [
    "RetrieveAgent",
    "GenerateAgent",
    "AgentCoordinator",
]
