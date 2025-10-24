"""
LLM Router for Cost-Optimized Model Selection

Intelligently routes tasks to appropriate Claude models based on complexity:
- Flagship (Sonnet 4.5): Complex analysis, code generation, high-stakes decisions
- Balanced (Sonnet 4): Standard agent tasks, incident analysis
- Fast (Haiku): Simple queries, log parsing, routine operations

Estimated cost savings: 70-80% compared to using flagship for everything
"""

from typing import Literal, Optional, Dict, Any
from anthropic import Anthropic, AsyncAnthropic
from .config import config
from .logging import get_logger

logger = get_logger(__name__)

TaskType = Literal[
    # Flagship model (use sparingly)
    "policy_generation",
    "complex_incident_analysis",
    "code_generation",
    "architecture_decisions",
    "novel_problem_solving",

    # Balanced model (default for most tasks)
    "incident_analysis",
    "terraform_generation",
    "remediation_planning",
    "memory_search_analysis",
    "alert_analysis",
    "infrastructure_planning",

    # Fast model (routine operations)
    "log_parsing",
    "status_checks",
    "notification_formatting",
    "simple_queries",
    "text_extraction",
    "simple_classification"
]


class LLMRouter:
    """
    Routes LLM tasks to appropriate Claude models for cost optimization

    Usage:
        router = LLMRouter()

        # Synchronous
        response = router.invoke("incident_analysis", "Analyze this alert...")

        # Asynchronous
        response = await router.ainvoke("log_parsing", "Parse this log...")
    """

    def __init__(self):
        self.client = Anthropic(api_key=config.anthropic.api_key)
        self.async_client = AsyncAnthropic(api_key=config.anthropic.api_key)

        self.models = {
            "flagship": config.anthropic.flagship_model,
            "balanced": config.anthropic.default_model,
            "fast": config.anthropic.fast_model,
        }

        # Task type to model tier mapping
        self.task_routing = {
            # Flagship tier
            "policy_generation": "flagship",
            "complex_incident_analysis": "flagship",
            "code_generation": "flagship",
            "architecture_decisions": "flagship",
            "novel_problem_solving": "flagship",

            # Balanced tier
            "incident_analysis": "balanced",
            "terraform_generation": "balanced",
            "remediation_planning": "balanced",
            "memory_search_analysis": "balanced",
            "alert_analysis": "balanced",
            "infrastructure_planning": "balanced",

            # Fast tier
            "log_parsing": "fast",
            "status_checks": "fast",
            "notification_formatting": "fast",
            "simple_queries": "fast",
            "text_extraction": "fast",
            "simple_classification": "fast",
        }

        # Pricing (approximate, in $ per 1M tokens)
        self.pricing = {
            "flagship": {"input": 3.00, "output": 15.00},
            "balanced": {"input": 3.00, "output": 15.00},
            "fast": {"input": 0.80, "output": 4.00},
        }

        # Usage tracking
        self.usage_stats = {
            "flagship": {"calls": 0, "input_tokens": 0, "output_tokens": 0},
            "balanced": {"calls": 0, "input_tokens": 0, "output_tokens": 0},
            "fast": {"calls": 0, "input_tokens": 0, "output_tokens": 0},
        }

    def route_task(self, task_type: TaskType) -> str:
        """
        Route task to appropriate model tier

        Args:
            task_type: Type of task being performed

        Returns:
            Model name to use
        """
        tier = self.task_routing.get(task_type, "balanced")
        model = self.models[tier]

        logger.debug(
            f"Routing task",
            extra={
                "task_type": task_type,
                "tier": tier,
                "model": model
            }
        )

        return model

    def invoke(
        self,
        task_type: TaskType,
        prompt: str,
        max_tokens: int = 2000,
        temperature: float = 0.0,
        system: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Synchronously invoke appropriate model based on task type

        Args:
            task_type: Type of task (determines model selection)
            prompt: User prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0=deterministic, 1=creative)
            system: Optional system prompt
            **kwargs: Additional arguments passed to API

        Returns:
            Generated text response
        """
        model = self.route_task(task_type)
        tier = [k for k, v in self.models.items() if v == model][0]

        logger.info(
            f"Invoking {tier} model for {task_type}",
            extra={"model": model, "prompt_length": len(prompt)}
        )

        messages = [{"role": "user", "content": prompt}]

        try:
            response = self.client.messages.create(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system if system else [],
                messages=messages,
                **kwargs
            )

            # Track usage
            self.usage_stats[tier]["calls"] += 1
            self.usage_stats[tier]["input_tokens"] += response.usage.input_tokens
            self.usage_stats[tier]["output_tokens"] += response.usage.output_tokens

            logger.info(
                f"Model response received",
                extra={
                    "tier": tier,
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens,
                    "stop_reason": response.stop_reason
                }
            )

            # Extract text from response
            return response.content[0].text

        except Exception as e:
            logger.error(
                f"Error invoking {tier} model",
                extra={"error": str(e), "task_type": task_type},
                exc_info=True
            )
            raise

    async def ainvoke(
        self,
        task_type: TaskType,
        prompt: str,
        max_tokens: int = 2000,
        temperature: float = 0.0,
        system: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Asynchronously invoke appropriate model based on task type

        Args:
            task_type: Type of task (determines model selection)
            prompt: User prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            system: Optional system prompt
            **kwargs: Additional arguments passed to API

        Returns:
            Generated text response
        """
        model = self.route_task(task_type)
        tier = [k for k, v in self.models.items() if v == model][0]

        logger.info(
            f"Async invoking {tier} model for {task_type}",
            extra={"model": model, "prompt_length": len(prompt)}
        )

        messages = [{"role": "user", "content": prompt}]

        try:
            response = await self.async_client.messages.create(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system if system else [],
                messages=messages,
                **kwargs
            )

            # Track usage
            self.usage_stats[tier]["calls"] += 1
            self.usage_stats[tier]["input_tokens"] += response.usage.input_tokens
            self.usage_stats[tier]["output_tokens"] += response.usage.output_tokens

            logger.info(
                f"Async model response received",
                extra={
                    "tier": tier,
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens,
                    "stop_reason": response.stop_reason
                }
            )

            return response.content[0].text

        except Exception as e:
            logger.error(
                f"Error async invoking {tier} model",
                extra={"error": str(e), "task_type": task_type},
                exc_info=True
            )
            raise

    def get_usage_stats(self) -> Dict[str, Any]:
        """Get usage statistics for all model tiers"""
        return self.usage_stats

    def estimate_cost(self) -> Dict[str, float]:
        """
        Estimate total cost based on usage statistics

        Returns:
            Dictionary with cost breakdown by tier
        """
        costs = {}
        total_cost = 0.0

        for tier, stats in self.usage_stats.items():
            input_cost = (stats["input_tokens"] / 1_000_000) * self.pricing[tier]["input"]
            output_cost = (stats["output_tokens"] / 1_000_000) * self.pricing[tier]["output"]
            tier_cost = input_cost + output_cost

            costs[tier] = {
                "calls": stats["calls"],
                "input_tokens": stats["input_tokens"],
                "output_tokens": stats["output_tokens"],
                "input_cost": input_cost,
                "output_cost": output_cost,
                "total_cost": tier_cost
            }

            total_cost += tier_cost

        costs["total"] = total_cost
        return costs

    def print_usage_summary(self):
        """Print formatted usage summary"""
        print("\n" + "=" * 70)
        print("LLM USAGE SUMMARY")
        print("=" * 70)

        costs = self.estimate_cost()

        for tier in ["flagship", "balanced", "fast"]:
            stats = costs[tier]
            print(f"\n{tier.upper()} ({self.models[tier]}):")
            print(f"  Calls: {stats['calls']}")
            print(f"  Input tokens: {stats['input_tokens']:,}")
            print(f"  Output tokens: {stats['output_tokens']:,}")
            print(f"  Cost: ${stats['total_cost']:.4f}")

        print(f"\nTOTAL ESTIMATED COST: ${costs['total']:.4f}")
        print("=" * 70 + "\n")


# Singleton instance
llm_router = LLMRouter()


if __name__ == "__main__":
    # Test the router
    import asyncio

    async def test_router():
        print("🧪 Testing LLM Router\n")

        # Test different task types
        tasks = [
            ("simple_queries", "What is 2+2?"),
            ("incident_analysis", "Analyze: High CPU usage on VM-100"),
            ("policy_generation", "Generate a policy for handling disk space alerts"),
        ]

        for task_type, prompt in tasks:
            print(f"\nTask: {task_type}")
            print(f"Prompt: {prompt}")

            try:
                response = await llm_router.ainvoke(
                    task_type=task_type,
                    prompt=prompt,
                    max_tokens=100
                )
                print(f"Response: {response[:100]}...")
            except Exception as e:
                print(f"Error: {e}")

        # Print usage summary
        llm_router.print_usage_summary()

    # Run test
    # asyncio.run(test_router())
    print("LLM Router loaded successfully. Run with test_router() to test.")
