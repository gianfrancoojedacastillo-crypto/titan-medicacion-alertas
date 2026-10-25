"""Punto de entrada del worker de Mistral Workflows."""

import asyncio

import mistralai_workflows
from mistralai_workflows import discover_workflows


async def main() -> None:
    discovered = discover_workflows()
    await mistralai_workflows.run_worker(discovered)


if __name__ == "__main__":
    asyncio.run(main())
