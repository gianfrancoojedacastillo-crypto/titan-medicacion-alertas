"""Workflow: revisa la medicación del Titan en Notion y avisa por Gmail."""

import json
from typing import Any

import pydantic
import mistralai.workflows as workflows
from mistralai.workflows import Depends
from mistralai.workflows.plugins.mistralai.connectors import (
    ToolCallClient,
    connector,
    uses_connectors,
)

notion_connector = connector("notion")
gmail_connector = connector("gmail")

DATA_SOURCE_URL = "collection://6b564d95-1cc5-8293-b695-8734fe31b2ce"
COUNT_COLUMN = "¿Cuantas pastillas se le ha proporcionado?"

MSG_DOS_ANTES = "Gianfranco casi es hora de comprar la medicina Sidenafilo"
MSG_UNO_ANTES = "Gianfranco apresúrate a comprar la medicina Sidenafilo"
MSG_MISMO_DIA = "Gianfranco es momento de comprar la medicina hoy mismo"


class TitanMedicacionInput(pydantic.BaseModel):
    recipient_email: str = "gianfrancoojedacastillo@gmail.com"
    dry_run: bool = False


def _parse_tool_response(raw: Any) -> Any:
    """Convierte la respuesta cruda de call_tool en un objeto de Python."""
    if raw is None:
        return None
    if isinstance(raw, (dict, list, int, float, bool)):
        return raw
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return raw
    content = getattr(raw, "content", None)
    if content:
        if isinstance(content, list):
            texts = []
            for block in content:
                if isinstance(block, str):
                    texts.append(block)
                elif isinstance(block, dict) and isinstance(block.get("text"), str):
                    texts.append(block["text"])
                else:
                    t = getattr(block, "text", None)
                    if isinstance(t, str):
                        texts.append(t)
            for t in texts:
                try:
                    return json.loads(t)
                except json.JSONDecodeError:
                    continue
            if texts:
                return texts[0]
        else:
            return _parse_tool_response(content)
    text = getattr(raw, "text", None)
    if isinstance(text, str):
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return text
    return raw


def _find_results(obj: Any) -> list:
    """Busca recursivamente una lista bajo la clave 'results'."""
    if isinstance(obj, dict):
        if isinstance(obj.get("results"), list):
            return obj["results"]
        for value in obj.values():
            found = _find_results(value)
            if found:
                return found
    elif isinstance(obj, list):
        for item in obj:
            found = _find_results(item)
            if found:
                return found
    return []


@workflows.activity(name="consultar-cantidad-sidenafilo")
async def consultar_cantidad_sidenafilo(
    notion: ToolCallClient = Depends(notion_connector),
) -> dict:
    """Consulta en Notion cuántas pastillas de Sidenafilo se le han dado a Titan."""
    raw = await notion.call_tool(
        tool_name="notion-query-data-sources",
        arguments={
            "data": {
                "mode": "sql",
                "data_source_urls": [DATA_SOURCE_URL],
                "query": (
                    'SELECT "Nombre", "' + COUNT_COLUMN + '" '
                    'FROM "' + DATA_SOURCE_URL + '" WHERE "Nombre" = ?'
                ),
                "params": ["SIDENAFILO"],
            }
        },
    )
    parsed = _parse_tool_response(raw)
    rows = _find_results(parsed)
    if not rows:
        return {"estado": "sin_datos", "pastillas": None}
    row = rows[0]
    count = row.get(COUNT_COLUMN)
    if isinstance(count, (int, float)):
        count = float(count)
    return {"estado": "ok", "pastillas": count}


@workflows.activity(name="enviar-correo-recordatorio")
async def enviar_correo_recordatorio(
    to: str,
    mensaje: str,
    pastillas: float,
    gmail: ToolCallClient = Depends(gmail_connector),
) -> dict:
    """Envía el correo de recordatorio a Gmail."""
    await gmail.call_tool(
        tool_name="send_email",
        arguments={
            "to": [to],
            "subject": "Titan: recordatorio para comprar Sidenafilo",
            "body": mensaje,
            "htmlBody": (
                "<div style=\"font-family: Arial, sans-serif; font-size: 15px;\">"
                "<p>" + mensaje + "</p>"
                "<p style=\"color: #555;\">Pastillas proporcionadas hasta hoy: "
                + str(int(pastillas)) + "</p>"
                "</div>"
            ),
        },
    )
    return {"correo_enviado": True}


@workflows.workflow.define(
    name="titan-medicacion",
    workflow_display_name="Medicación del Titan",
    workflow_description=(
        "Revisa diariamente en Notion cuántas pastillas de Sidenafilo se le han "
        "proporcionado a Titan y envía un correo a Gmail cuando el valor se "
        "acerca a un múltiplo de 10 (10-2, 10-1 y el propio múltiplo)."
    ),
)
@uses_connectors(notion_connector, gmail_connector)
class TitanMedicacionWorkflow:
    @workflows.workflow.entrypoint
    async def run(self, input: TitanMedicacionInput) -> dict:
        info = await consultar_cantidad_sidenafilo()
        pastillas = info.get("pastillas")

        if pastillas is None:
            return {
                "correo_enviado": False,
                "motivo": "La columna '" + COUNT_COLUMN + "' está vacía o sin datos.",
            }

        resto = int(pastillas) % 10
        if resto == 8:
            mensaje = MSG_DOS_ANTES
        elif resto == 9:
            mensaje = MSG_UNO_ANTES
        elif resto == 0:
            mensaje = MSG_MISMO_DIA
        else:
            return {
                "correo_enviado": False,
                "motivo": "Aún no toca avisar.",
                "pastillas": pastillas,
            }

        if input.dry_run:
            return {"correo_enviado": False, "dry_run": True, "mensaje": mensaje, "pastillas": pastillas}

        await enviar_correo_recordatorio(
            to=input.recipient_email,
            mensaje=mensaje,
            pastillas=pastillas,
        )
        return {"correo_enviado": True, "mensaje": mensaje, "pastillas": pastillas}
