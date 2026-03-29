import os
import time
from datetime import datetime
from enum import Enum

from dotenv import load_dotenv
from openai import AzureOpenAI
from tenacity import retry, stop_after_attempt, wait_random_exponential

from .parser import BaseParser
from .utils import write_to_file


class LLMSupplierType(Enum):
    OPENAI = 0
    LLAMA33 = 1
    DEEPSEEKV3 = 2


class LLMConfig:
    def __init__(
        self,
        llm_name: str = "Default",
        env_path: str = None,
        trial_num: int = None,
        answer_parser: BaseParser = None,
        temperature: float = 0.0,
        max_tokens: int = None,
        llm_supplier: LLMSupplierType = LLMSupplierType.OPENAI,
    ):
        self.llm_name: str = llm_name
        if trial_num is None or trial_num <= 0:
            trial_num = 1
        self.trial_num = trial_num
        if env_path is None or not os.path.exists(env_path):
            env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
        self.env_path = env_path
        if answer_parser is None:
            raise ValueError("answer_parser is required")
        self.answer_parser = answer_parser
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.llm_supplier = llm_supplier


class LLM:
    def __init__(self, llm_config: LLMConfig):
        self.name: str = llm_config.llm_name
        self.log_path: str = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "log", "llm", self.name + ".log"
        )
        self.trial_num = llm_config.trial_num
        self.answer_parser = llm_config.answer_parser
        self.temperature = llm_config.temperature
        self.max_tokens = llm_config.max_tokens
        if llm_config.llm_supplier == LLMSupplierType.LLAMA33 and self.max_tokens is None:
            self.max_tokens = 8192
        if llm_config.llm_supplier == LLMSupplierType.DEEPSEEKV3 and self.max_tokens is None:
            self.max_tokens = 8000
        self.llm_supplier = llm_config.llm_supplier
        self.input_token_num: int = 0
        self.output_token_num: int = 0
        self.latency: float = 0.0

        load_dotenv(llm_config.env_path, override=True)
        if self.llm_supplier == LLMSupplierType.OPENAI:
            self.client = AzureOpenAI(
                azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
                api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
                api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            )
            self.model = os.getenv("AZURE_OPENAI_MODEL_GPT")
        elif self.llm_supplier == LLMSupplierType.LLAMA33:
            self.client = AzureOpenAI(
                azure_endpoint=os.getenv("AZURE_LLAMA33_ENDPOINT"),
                api_version=os.getenv("AZURE_LLAMA33_API_VERSION"),
                api_key=os.getenv("AZURE_LLAMA33_API_KEY"),
            )
            self.model = os.getenv("AZURE_LLAMA33_MODEL")
        elif self.llm_supplier == LLMSupplierType.DEEPSEEKV3:
            self.client = AzureOpenAI(
                azure_endpoint=os.getenv("AZURE_DEEPSEEKV3_ENDPOINT"),
                api_version=os.getenv("AZURE_DEEPSEEKV3_API_VERSION"),
                api_key=os.getenv("AZURE_DEEPSEEKV3_API_KEY"),
            )
            self.model = os.getenv("AZURE_DEEPSEEKV3_MODEL")
        else:
            raise ValueError(f"Unknown LLM supplier: {self.llm_supplier.name}")

    @retry(wait=wait_random_exponential(min=1, max=20), stop=stop_after_attempt(6))
    def _call(self, message):
        return self.client.chat.completions.create(
            model=self.model,
            messages=message,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )

    def answer(self, prompt: str):
        message = [{"role": "user", "content": prompt}]

        trial_num = self.trial_num
        while trial_num > 0:
            start = time.time()
            try:
                response = self._call(message)
            except Exception:
                trial_num -= 1
                self.latency += time.time() - start
                continue
            end = time.time()
            self.latency += end - start
            self.input_token_num += response.usage.prompt_tokens
            self.output_token_num += response.usage.completion_tokens

            log_response = str(response.choices[0].message.content)
            log_input = str(response.usage.prompt_tokens)
            log_output = str(response.usage.completion_tokens)
            write_to_file(
                dest_path=self.log_path,
                contents=(
                    self._log()
                    .replace("<prompt>", str(prompt))
                    .replace("<response>", log_response)
                    .replace("<input>", log_input)
                    .replace("<output>", log_output)
                    .replace("<time>", str(end - start))
                ),
                is_append=True,
                is_json=False,
            )

            answer = self.answer_parser.parse(response.choices[0].message.content)

            if answer is not None:
                return answer
            trial_num -= 1
        return None

    def _log(self):
        return (
            f"**************************************************{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}**************************************************\n"
            + "[Prompt]\n<prompt>\n[LLM Response]\n<response>\n"
            + f"[Model, Temperature, MaxTokens]{self.model}, {self.temperature}, {self.max_tokens}\n"
            + "[Input, Output, Time]<input>, <output>, <time>"
            + "\n=======================================================================================================================\n\n"
        )

    def to_dict(self):
        return {
            "name": self.name,
            "llm_supplier": self.llm_supplier.name,
            "model": self.model,
            "trial_num": self.trial_num,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "input_token_num": self.input_token_num,
            "output_token_num": self.output_token_num,
            "latency": self.latency,
        }
