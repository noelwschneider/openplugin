import json
import os
import traceback

import jinja2
import requests
from tenacity import retry, stop_after_attempt, wait_random_exponential

from openplugin.bindings.openai.openai_helpers import chat_completion_with_backoff
from openplugin.interfaces.models import (
    OperationExecutionParams,
    OperationExecutionResponse,
)
from openplugin.interfaces.operation_execution import OperationExecution

CLARIFYING_QUESTION_PROMPT = "#INPUT_JSON\n This is a json describing what is missing in the API call. Write a clarifying question asking user to provide missing informations. Make sure you prettify the parameter name. Don't mention about JSON or API call."
DEFAULT_MODEL_NAME = "gpt-3.5-turbo-0613"


@retry(wait=wait_random_exponential(min=1, max=60), stop=stop_after_attempt(2))
def _call(url, method="GET", headers=None, params=None, body=None):
    try:
        if body and isinstance(body, dict):
            body = json.dumps(body)
            headers["Content-Type"] = "application/json"
        # hack for email API
        if params and params.get("content") is not None:
            params["content"] = (
                params["content"]
                .replace("/edit)", "/edit )")
                .replace(".txt)", ".txt )")
            )
        response = requests.request(
            method.upper(), url, headers=headers, params=params, data=body
        )
        if response.status_code == 200:
            response_json = response.json()

            if not isinstance(response_json, list):
                if response_json.get("message") and response_json.get(
                    "message"
                ).startswith("Internal Server Error"):
                    failed_message = (
                        f"API: {url}, Params: {params},Status code: "
                        f"{response.status_code}, Response: {response.text[0:100]}..."
                    )
                    raise Exception("{}".format(failed_message))
                if response_json.get("error"):
                    failed_message = (
                        f"API: {url}, Params: {params},Status code: "
                        f"{response.status_code}, Response: {response.text[0:100]}..."
                    )
                    raise Exception("{}".format(failed_message))
            return response.json(), response.status_code
        elif response.status_code == 400:
            return response.text, response.status_code
        failed_message = (
            f"API: {url}, Params: {params},Status code: "
            f"{response.status_code}, Response: {response.text[0:100]}..."
        )
        raise Exception("{}".format(failed_message))
    except Exception as e:
        traceback.print_exc()
        raise Exception("{}".format(e))


class OperationExecutionImpl(OperationExecution):
    def __init__(self, params: OperationExecutionParams):
        if params.openai_api_key is not None:
            self.openai_api_key = params.openai_api_key
        else:
            self.openai_api_key = os.environ["OPENAI_API_KEY"]
        super().__init__(params)

    def run(self) -> OperationExecutionResponse:
        try:
            response_json, status_code = _call(
                self.params.api,
                self.params.method,
                self.params.header,
                self.params.query_params,
                self.params.body,
            )
        except Exception as e:
            raise Exception("{}".format(e.args[0].result()))

        template_response = None
        template_str = self.params.plugin_response_template
        if template_str and len(template_str) > 0:
            template = jinja2.Template(template_str)
            template_response = template.render(json_data=response_json)

        cleanup_response = None
        is_a_clarifying_question = False
        clarifying_response = None

        if status_code == 400:
            is_a_clarifying_question = True
            try:
                model_name = DEFAULT_MODEL_NAME
                if (
                    self.params.llm is not None
                    and self.params.llm.model_name is not None
                ):
                    model_name = self.params.llm.model_name
                response = chat_completion_with_backoff(
                    openai_api_key=self.openai_api_key,
                    model=model_name,
                    messages=[
                        {
                            "role": "user",
                            "content": CLARIFYING_QUESTION_PROMPT.replace(
                                "#INPUT_JSON", response_json
                            ),
                        }
                    ],
                )
                clarifying_response = response["choices"][0]["message"]["content"]
            except Exception as e:
                clarifying_response = f"Failed: {e}"
        elif self.params.post_processing_cleanup_prompt:
            try:
                if template_response:
                    c_prompt = f"{self.params.post_processing_cleanup_prompt} For: {template_response}"
                else:
                    c_prompt = f"{self.params.post_processing_cleanup_prompt} For: {response_json}"

                model_name = DEFAULT_MODEL_NAME
                if (
                    self.params.llm is not None
                    and self.params.llm.model_name is not None
                ):
                    model_name = self.params.llm.model_name
                response = chat_completion_with_backoff(
                    openai_api_key=self.openai_api_key,
                    model=model_name,
                    messages=[{"role": "user", "content": c_prompt}],
                )
                cleanup_response = response["choices"][0]["message"]["content"]
            except Exception as e:
                cleanup_response = f"Failed: {e}"

        summary_response = None
        if self.params.run_summary_response:
            try:
                if cleanup_response:
                    summary_snippet = cleanup_response
                elif template_response:
                    summary_snippet = template_response
                else:
                    summary_snippet = response_json
                summary_prompt = f"""Use a random way to rewrite the #PROMPT to indicate that it has finished either successfully or unsuccessfully based on the #RESPONSE 

                #RESPONSE
                {summary_snippet}
                """
                model_name = DEFAULT_MODEL_NAME
                summary_response = chat_completion_with_backoff(
                    openai_api_key=self.openai_api_key,
                    model=model_name,
                    messages=[{"role": "user", "content": summary_prompt}],
                )
                summary_response = summary_response["choices"][0]["message"][
                    "content"
                ]
            except Exception as e:
                summary_response = f"Failed: {e}"

        return OperationExecutionResponse(
            original_response=response_json,
            clarifying_response=clarifying_response,
            cleanup_response=cleanup_response,
            template_response=template_response,
            summary_response=summary_response,
            is_a_clarifying_question=is_a_clarifying_question,
        )
