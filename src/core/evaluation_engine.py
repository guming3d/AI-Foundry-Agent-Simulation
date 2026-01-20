"""
Evaluation engine that uses Microsoft Foundry eval runs.

Creates evaluation groups and runs them against selected agents using
project-scoped OpenAI evals, then persists run metadata and outputs.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import re
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from openai.types.eval_create_params import DataSourceConfigCustom

from .azure_client import get_openai_client, get_project_client
from .evaluation_templates import EvaluationTemplateLoader, EvaluationTemplate, EvaluationItem, EvaluatorDefinition
from .agent_manager import AgentManager
from . import config


EVALUATOR_NAME_MAP = {
    "bleu_score": "builtin.bleu_score",
    "coherence": "builtin.coherence",
    "f1_score": "builtin.f1_score",
    "fluency": "builtin.fluency",
    "gleu_score": "builtin.gleu_score",
    "hate_unfairness": "builtin.hate_unfairness",
    "meteor_score": "builtin.meteor_score",
    "prohibited_actions": "builtin.prohibited_actions",
    "relevance": "builtin.relevance",
    "response_completeness": "builtin.response_completeness",
    "rouge_score": "builtin.rouge_score",
    "self_harm": "builtin.self_harm",
    "sensitive_data_leakage": "builtin.sensitive_data_leakage",
    "sexual": "builtin.sexual",
    "similarity": "builtin.similarity",
    "violence": "builtin.violence",
}

MODEL_DEPLOYMENT_EVALUATORS = {
    "coherence",
    "fluency",
    "relevance",
    "response_completeness",
    "similarity",
}

GROUND_TRUTH_EVALUATORS = {
    "bleu_score",
    "f1_score",
    "gleu_score",
    "meteor_score",
    "response_completeness",
    "rouge_score",
    "similarity",
}

STRING_CHECK_OPERATION_MAP = {
    "equals": "eq",
    "eq": "eq",
    "not_equals": "ne",
    "ne": "ne",
    "contains": "like",
    "starts_with": "like",
    "ends_with": "like",
    "like": "like",
}


@dataclass
class AgentInfo:
    """Simplified agent metadata for evaluation."""

    name: str
    azure_id: str = ""
    model: str = ""
    version: Optional[str] = None


class EvaluationEngine:
    """Runs sample evaluations against agents via Foundry eval runs."""

    def __init__(self, templates_dir=None) -> None:
        self.template_loader = EvaluationTemplateLoader(templates_dir=templates_dir)

    def run(
        self,
        template_ids: List[str],
        agent_names: List[str],
        model_deployment_name: Optional[str] = None,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
        log_callback: Optional[Callable[[str], None]] = None,
    ) -> List[Dict[str, Any]]:
        """Run selected evaluation templates against agents."""
        if not template_ids:
            raise ValueError("No evaluation templates selected")
        if not agent_names:
            raise ValueError("No agents selected for evaluation")

        templates = [self.template_loader.load_template(tid) for tid in template_ids]
        agents = self._resolve_agents(agent_names, log_callback=log_callback)

        if not agents:
            raise ValueError("Selected agents not found in the project")

        if self._templates_require_model(templates) and not model_deployment_name:
            raise ValueError("Select a model deployment for model-based evaluations.")

        if model_deployment_name and log_callback:
            for agent in agents:
                if agent.model and agent.model != model_deployment_name:
                    log_callback(
                        f"[!] Agent {agent.name} uses model {agent.model}; "
                        f"selected deployment is {model_deployment_name}."
                    )

        total_steps = len(templates) * len(agents)
        if total_steps == 0:
            raise ValueError("Selected evaluations have no dataset items")

        current_step = 0
        results = []
        openai_client = get_openai_client()
        project_client = get_project_client()
        project_endpoint = getattr(getattr(project_client, "_config", None), "endpoint", "")

        for template in templates:
            eval_id = self._create_eval_definition(
                template,
                openai_client,
                model_deployment_name=model_deployment_name,
                log_callback=log_callback,
            )
            for agent in agents:
                current_step += 1
                if progress_callback:
                    progress_callback(
                        current_step,
                        total_steps,
                        f"{template.id}: {agent.name} ({current_step}/{total_steps})",
                    )
                run_result = self._run_template_for_agent(
                    template=template,
                    agent=agent,
                    openai_client=openai_client,
                    eval_id=eval_id,
                    project_endpoint=project_endpoint,
                    log_callback=log_callback,
                )
                results.append(run_result)

        return results

    def _resolve_agents(
        self,
        agent_names: List[str],
        log_callback: Optional[Callable[[str], None]] = None,
    ) -> List[AgentInfo]:
        """Resolve agent details for evaluation."""
        manager = AgentManager()
        available = {agent.get("name", ""): agent for agent in manager.list_agents()}
        agents: List[AgentInfo] = []

        for name in agent_names:
            agent_data = available.get(name)
            if not agent_data:
                if log_callback:
                    log_callback(f"[!] Agent not found: {name}")
                continue
            agents.append(
                AgentInfo(
                    name=agent_data.get("name", name),
                    azure_id=agent_data.get("id", ""),
                    model=agent_data.get("model", ""),
                    version=agent_data.get("version"),
                )
            )

        return agents

    def _create_eval_definition(
        self,
        template: EvaluationTemplate,
        openai_client,
        model_deployment_name: Optional[str],
        log_callback=None,
    ) -> str:
        """Create a new evaluation definition for a template."""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        eval_name = f"{template.display_name} ({timestamp})"
        data_source_config = self._build_data_source_config(template)
        testing_criteria = self._build_testing_criteria(
            template,
            model_deployment_name=model_deployment_name,
        )

        if log_callback:
            log_callback(f"[*] Creating evaluation definition for {template.display_name}")

        eval_object = openai_client.evals.create(
            name=eval_name,
            data_source_config=data_source_config,
            testing_criteria=testing_criteria,
        )
        return getattr(eval_object, "id", None) or eval_object.get("id")

    def _run_template_for_agent(
        self,
        template: EvaluationTemplate,
        agent: AgentInfo,
        openai_client,
        eval_id: str,
        project_endpoint: str,
        log_callback: Optional[Callable[[str], None]] = None,
    ) -> Dict[str, Any]:
        """Run a single template for a single agent."""
        config.ensure_directories()
        dataset_dir = config.EVALUATIONS_RESULTS_DIR / "datasets"
        dataset_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        dataset_name = self._build_dataset_name(template.id, agent.name, timestamp)

        dataset_records = [self._build_dataset_record(item) for item in template.dataset_items]
        dataset_path = dataset_dir / f"{dataset_name}.jsonl"
        self._write_jsonl(dataset_path, dataset_records)

        data_source = self._build_data_source(template, agent, dataset_records)
        run_name = f"{template.display_name} - {agent.name}"

        if log_callback:
            log_callback(f"[*] Starting evaluation run for {agent.name}")

        run_response = openai_client.evals.runs.create(
            eval_id=eval_id,
            name=run_name,
            data_source=data_source,
        )
        run_id = getattr(run_response, "id", None) or run_response.get("id")

        run_result = self._wait_for_run(
            openai_client,
            eval_id=eval_id,
            run_id=run_id,
            log_callback=log_callback,
        )

        output_items = self._list_output_items(openai_client, eval_id=eval_id, run_id=run_id)

        result_path = config.EVALUATIONS_RESULTS_DIR / f"{template.id}_{dataset_name}.json"
        record = {
            "evaluation_id": template.id,
            "evaluation_name": run_name,
            "agent_name": agent.name,
            "agent_model": agent.model,
            "agent_version": agent.version,
            "eval_id": eval_id,
            "run_id": run_id,
            "run_status": getattr(run_result, "status", None),
            "report_url": getattr(run_result, "report_url", None),
            "dataset_name": dataset_name,
            "dataset_path": str(dataset_path),
            "project_endpoint": project_endpoint,
            "outputs": output_items,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        with open(result_path, "w", encoding="utf-8") as handle:
            json.dump(record, handle, indent=2, ensure_ascii=True)

        return {
            "evaluation_id": template.id,
            "evaluation_name": run_name,
            "agent_name": agent.name,
            "eval_id": eval_id,
            "run_id": run_id,
            "run_status": getattr(run_result, "status", None),
            "report_url": getattr(run_result, "report_url", None),
            "result_path": str(result_path),
        }

    def _build_dataset_record(self, item: EvaluationItem) -> Dict[str, Any]:
        """Build a dataset row from template data."""
        record = {"query": item.query}
        if item.context:
            record["context"] = item.context
        if item.ground_truth:
            record["ground_truth"] = item.ground_truth
        return record

    def _write_jsonl(self, path: Path, records: List[Dict[str, Any]]) -> None:
        """Write a JSONL dataset file."""
        with open(path, "w", encoding="utf-8") as handle:
            for record in records:
                handle.write(json.dumps(record, ensure_ascii=True) + "\n")

    def _build_dataset_name(self, template_id: str, agent_name: str, timestamp: str) -> str:
        """Create a dataset name safe for the service."""
        safe_agent = re.sub(r"[^a-zA-Z0-9-]+", "-", agent_name).strip("-").lower()
        safe_template = re.sub(r"[^a-zA-Z0-9-]+", "-", template_id).strip("-").lower()
        name = f"eval-{safe_template}-{safe_agent}-{timestamp}".lower()
        return name[:80]

    def _build_data_source_config(self, template: EvaluationTemplate) -> DataSourceConfigCustom:
        """Build the eval data source schema."""
        properties = {"query": {"type": "string"}}
        required = ["query"]

        if any(item.context for item in template.dataset_items):
            properties["context"] = {"type": "string"}
        if any(item.ground_truth for item in template.dataset_items):
            properties["ground_truth"] = {"type": "string"}

        return DataSourceConfigCustom(
            type="custom",
            item_schema={
                "type": "object",
                "properties": properties,
                "required": required,
            },
            include_sample_schema=True,
        )

    def _build_testing_criteria(
        self,
        template: EvaluationTemplate,
        model_deployment_name: Optional[str],
    ) -> List[Dict[str, Any]]:
        """Build testing criteria for eval creation."""
        criteria = []
        has_context = any(item.context for item in template.dataset_items)

        for evaluator in template.evaluators:
            evaluator_type = evaluator.type.lower()
            if evaluator_type in EVALUATOR_NAME_MAP:
                data_mapping = self._resolve_data_mapping(evaluator, evaluator_type, has_context)
                entry: Dict[str, Any] = {
                    "type": "azure_ai_evaluator",
                    "name": evaluator.name,
                    "evaluator_name": EVALUATOR_NAME_MAP[evaluator_type],
                    "data_mapping": data_mapping,
                }
                init_params = self._build_initialization_parameters(
                    evaluator,
                    evaluator_type,
                    model_deployment_name=model_deployment_name,
                )
                if init_params:
                    entry["initialization_parameters"] = init_params
                criteria.append(entry)
            elif evaluator_type == "string_check":
                criteria.append(self._build_string_check_grader(evaluator))
            else:
                raise ValueError(f"Unsupported evaluator type '{evaluator.type}' in template {template.id}")

        return criteria

    def _build_initialization_parameters(
        self,
        evaluator: EvaluatorDefinition,
        evaluator_type: str,
        model_deployment_name: Optional[str],
    ) -> Dict[str, Any]:
        """Build evaluator initialization parameters for the current SDK."""
        init_params = dict(evaluator.init_params or {})

        if evaluator_type in MODEL_DEPLOYMENT_EVALUATORS:
            if not model_deployment_name:
                raise ValueError("Select a model deployment for model-based evaluations.")
            init_params.setdefault("deployment_name", model_deployment_name)

        return init_params

    def _resolve_data_mapping(
        self,
        evaluator: EvaluatorDefinition,
        evaluator_type: str,
        has_context: bool,
    ) -> Dict[str, str]:
        """Resolve evaluator data mappings using template defaults."""
        if evaluator.data_mapping:
            return self._normalize_mapping(evaluator.data_mapping)

        if evaluator_type in GROUND_TRUTH_EVALUATORS:
            return {
                "response": "{{sample.output_text}}",
                "ground_truth": "{{item.ground_truth}}",
            }

        mapping = {
            "query": "{{item.query}}",
            "response": "{{sample.output_text}}",
        }
        if has_context:
            mapping["context"] = "{{item.context}}"
        return mapping

    def _normalize_mapping(self, mapping: Dict[str, Any]) -> Dict[str, str]:
        """Normalize data mapping values into {{item.*}} or {{sample.*}} templates."""
        normalized = {}
        for key, value in mapping.items():
            if value is None:
                continue
            text = str(value).strip()
            if "{{" in text and "}}" in text:
                normalized[key] = text
                continue
            match = re.match(r"^\$\{data\.([a-zA-Z0-9_.]+)\}$", text)
            if match:
                field = match.group(1)
            elif text.startswith("data."):
                field = text[5:]
            elif text.startswith("item."):
                field = text[5:]
            elif text.startswith("sample."):
                normalized[key] = f"{{{{{text}}}}}"
                continue
            else:
                field = text

            if field in {"response", "output", "output_text"}:
                normalized[key] = "{{sample.output_text}}"
            else:
                normalized[key] = f"{{{{item.{field}}}}}"
        return normalized

    def _build_string_check_grader(self, evaluator: EvaluatorDefinition) -> Dict[str, Any]:
        """Build a string-check grader definition."""
        params = evaluator.params or {}
        operation = str(params.get("operation", "contains")).lower()
        case_sensitive = bool(params.get("case_sensitive", False))
        reference = str(params.get("reference", ""))

        mapped_operation = STRING_CHECK_OPERATION_MAP.get(operation, "like")
        if not case_sensitive and mapped_operation in {"like", "eq"}:
            mapped_operation = "ilike"

        return {
            "type": "string_check",
            "name": evaluator.name,
            "input": "{{sample.output_text}}",
            "operation": mapped_operation,
            "reference": reference,
        }

    def _templates_require_model(self, templates: List[EvaluationTemplate]) -> bool:
        """Check if any template requires a model deployment."""
        for template in templates:
            for evaluator in template.evaluators:
                if evaluator.type.lower() in MODEL_DEPLOYMENT_EVALUATORS:
                    return True
        return False

    def _build_data_source(
        self,
        template: EvaluationTemplate,
        agent: AgentInfo,
        dataset_records: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Build eval run data source configuration."""
        has_context = any("context" in record for record in dataset_records)
        prompt_text = "{{item.query}}"
        if has_context:
            prompt_text = "Context: {{item.context}}\n\n{{item.query}}"

        content = [{"item": record} for record in dataset_records]
        data_source = {
            "type": "azure_ai_target_completions",
            "source": {
                "type": "file_content",
                "content": content,
            },
            "input_messages": {
                "type": "template",
                "template": [
                    {
                        "type": "message",
                        "role": "user",
                        "content": {
                            "type": "input_text",
                            "text": prompt_text,
                        },
                    }
                ],
            },
            "target": {
                "type": "azure_ai_agent",
                "name": agent.name,
            },
        }
        if agent.version:
            data_source["target"]["version"] = agent.version
        return data_source

    def _wait_for_run(
        self,
        openai_client,
        eval_id: str,
        run_id: str,
        timeout_seconds: int = 1800,
        log_callback: Optional[Callable[[str], None]] = None,
    ):
        """Poll the evaluation run until completion."""
        start_time = time.time()
        run = openai_client.evals.runs.retrieve(eval_id=eval_id, run_id=run_id)
        while getattr(run, "status", None) in {"queued", "in_progress"}:
            if time.time() - start_time > timeout_seconds:
                raise TimeoutError("Evaluation run timed out.")
            if log_callback:
                log_callback(f"[*] Run {run_id} status: {run.status}")
            time.sleep(3)
            run = openai_client.evals.runs.retrieve(eval_id=eval_id, run_id=run_id)

        if getattr(run, "status", None) in {"failed", "canceled"}:
            raise RuntimeError(f"Evaluation run {run_id} failed with status {run.status}.")
        return run

    def _list_output_items(self, openai_client, eval_id: str, run_id: str) -> List[Dict[str, Any]]:
        """Collect output items from a completed eval run."""
        items = []
        after = None
        while True:
            page = openai_client.evals.runs.output_items.list(
                eval_id=eval_id,
                run_id=run_id,
                limit=100,
                after=after,
            )
            page_items = getattr(page, "data", [])
            for item in page_items:
                items.append(self._as_dict(item))
            if not getattr(page, "has_more", False) or not page_items:
                break
            after = getattr(page_items[-1], "id", None)
            if not after:
                break
        return items

    def _as_dict(self, value: Any) -> Dict[str, Any]:
        """Convert SDK objects to plain dicts."""
        if isinstance(value, dict):
            return value
        if hasattr(value, "model_dump"):
            return value.model_dump()
        if hasattr(value, "dict"):
            return value.dict()
        if hasattr(value, "__dict__"):
            return dict(value.__dict__)
        return {"value": value}
