import logging
from typing import Any, Dict, TypedDict

from agents.ats_agent import ATSAgent
from agents.cover_letter_agent import CoverLetterAgent
from agents.gap_agent import GapAgent

logger = logging.getLogger(__name__)


class PipelineState(TypedDict, total=False):
    profile: Dict[str, Any]
    original_cv: str
    job_description: str
    company_name: str
    gap_report: Dict[str, Any]
    cv_result: Dict[str, Any]
    cover_letter: str


class AgentPipeline:
    """
    LangGraph-first orchestrator for Clover generation pipeline.
    Falls back to sequential orchestration when LangGraph is unavailable.
    """

    def __init__(self):
        self.gap_agent = GapAgent()
        self.ats_agent = ATSAgent()
        self.cover_letter_agent = CoverLetterAgent()
        self._compiled_graph = None
        self._build_graph()

    def _build_graph(self) -> None:
        try:
            from langgraph.graph import END, StateGraph

            graph = StateGraph(PipelineState)
            graph.add_node("gap", self._gap_node)
            graph.add_node("ats", self._ats_node)
            graph.add_node("cover", self._cover_node)
            graph.set_entry_point("gap")
            graph.add_edge("gap", "ats")
            graph.add_edge("ats", "cover")
            graph.add_edge("cover", END)
            self._compiled_graph = graph.compile()
            logger.info("LangGraph pipeline enabled for Clover agents.")
        except Exception as exc:
            self._compiled_graph = None
            logger.info(f"LangGraph unavailable, using sequential pipeline: {exc}")

    def _gap_node(self, state: PipelineState) -> PipelineState:
        return {
            "gap_report": self.gap_agent.run(
                profile=state["profile"],
                job_description=state["job_description"],
            )
        }

    def _ats_node(self, state: PipelineState) -> PipelineState:
        return {
            "cv_result": self.ats_agent.run(
                original_cv=state.get("original_cv", ""),
                gap_report=state["gap_report"],
                job_description=state["job_description"],
            )
        }

    def _cover_node(self, state: PipelineState) -> PipelineState:
        return {
            "cover_letter": self.cover_letter_agent.run(
                profile=state["profile"],
                gap_report=state["gap_report"],
                job_description=state["job_description"],
                company_name=state.get("company_name", "the company"),
                candidate_name=(state.get("profile") or {}).get("name", ""),
            )
        }

    def run(
        self,
        profile: Dict[str, Any],
        job_description: str,
        company_name: str,
        original_cv: str = "",
    ) -> Dict[str, Any]:
        initial_state: PipelineState = {
            "profile": profile,
            "original_cv": original_cv,
            "job_description": job_description,
            "company_name": company_name,
        }

        if self._compiled_graph is not None:
            output = self._compiled_graph.invoke(initial_state)
            return {
                "gap_report": output["gap_report"],
                "cv_result": output["cv_result"],
                "cover_letter": output["cover_letter"],
            }

        gap_report = self.gap_agent.run(profile=profile, job_description=job_description)
        cv_result = self.ats_agent.run(
            original_cv=original_cv,
            gap_report=gap_report,
            job_description=job_description,
        )
        cover_letter = self.cover_letter_agent.run(
            profile=profile,
            gap_report=gap_report,
            job_description=job_description,
            company_name=company_name,
            candidate_name=profile.get("name", ""),
        )
        return {
            "gap_report": gap_report,
            "cv_result": cv_result,
            "cover_letter": cover_letter,
        }
