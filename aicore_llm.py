"""
SAP AI Core LLM Client - Call LLM models (GPT, Claude, etc.) hosted on SAP AI Core.

Requirements:
    pip install generative-ai-hub-sdk

Usage:
    1. With service key JSON file:
        python aicore_llm.py --service-key /path/to/service_key.json --prompt "Hello!"
    
    2. With service key as environment variable:
        export AICORE_SERVICE_KEY='{"clientid": "...", "clientsecret": "...", ...}'
        python aicore_llm.py --prompt "Hello!"
    
    3. As a module:
        from aicore_llm import AICoreClient
        client = AICoreClient.from_service_key_file("/path/to/service_key.json")
        response = client.chat("What is SAP?")
        print(response)
"""

import argparse
import json
import os
from pathlib import Path
from typing import Optional


def setup_aicore_config(service_key: dict, resource_group: str = "default") -> None:
    """
    Set up the AI Core configuration from a service key.
    
    The generative-ai-hub-sdk reads config from:
    1. Environment variables (AICORE_*)
    2. ~/.aicore/config.json
    
    This function sets environment variables for the current session.
    """
    credentials = service_key.get("credentials", service_key)
    
    # Extract values from service key
    auth_url = credentials.get("url")
    client_id = credentials.get("clientid")
    client_secret = credentials.get("clientsecret")
    
    # API URL can be in different locations depending on service key format
    service_urls = credentials.get("serviceurls", {})
    api_base = service_urls.get("AI_API_URL") or credentials.get("apibase")
    
    if not all([auth_url, client_id, client_secret, api_base]):
        raise ValueError(
            "Invalid service key. Expected keys: url, clientid, clientsecret, "
            "and serviceurls.AI_API_URL (or apibase)"
        )
    
    # Set environment variables for the SDK
    os.environ["AICORE_AUTH_URL"] = auth_url
    os.environ["AICORE_CLIENT_ID"] = client_id
    os.environ["AICORE_CLIENT_SECRET"] = client_secret
    os.environ["AICORE_BASE_URL"] = api_base
    os.environ["AICORE_RESOURCE_GROUP"] = resource_group


def save_aicore_config(service_key: dict, resource_group: str = "default") -> Path:
    """
    Save AI Core configuration to ~/.aicore/config.json for persistent use.
    """
    credentials = service_key.get("credentials", service_key)
    
    service_urls = credentials.get("serviceurls", {})
    api_base = service_urls.get("AI_API_URL") or credentials.get("apibase")
    
    config = {
        "AICORE_AUTH_URL": credentials.get("url"),
        "AICORE_CLIENT_ID": credentials.get("clientid"),
        "AICORE_CLIENT_SECRET": credentials.get("clientsecret"),
        "AICORE_BASE_URL": api_base,
        "AICORE_RESOURCE_GROUP": resource_group,
    }
    
    config_dir = Path.home() / ".aicore"
    config_dir.mkdir(exist_ok=True)
    config_path = config_dir / "config.json"
    
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)
    
    print(f"Configuration saved to {config_path}")
    return config_path


class AICoreClient:
    """
    Client for calling LLM models on SAP AI Core's Generative AI Hub.
    
    Supports models like:
    - Azure OpenAI: gpt-4o, gpt-4o-mini, o1, o3-mini
    - AWS Bedrock: anthropic--claude-3.5-sonnet, anthropic--claude-3-opus
    - Google Vertex: gemini-2.0-flash, gemini-1.5-pro
    - Open Source: meta--llama3.1-70b-instruct, mistralai--mistral-large-instruct
    """
    
    def __init__(self, model_name: str = "gpt-4o"):
        """
        Initialize the client.
        
        Args:
            model_name: The model to use (e.g., "gpt-4o", "gpt-4o-mini")
        """
        # Import here to allow config setup before import
        from gen_ai_hub.proxy.core.proxy_clients import set_proxy_version
        from gen_ai_hub.proxy.native.openai import OpenAI
        
        set_proxy_version("gen-ai-hub")
        
        self.model_name = model_name
        self._client = OpenAI()
    
    @classmethod
    def from_service_key(
        cls,
        service_key: dict,
        model_name: str = "gpt-4o",
        resource_group: str = "default"
    ) -> "AICoreClient":
        """
        Create a client from a service key dictionary.
        
        Args:
            service_key: Service key as dictionary
            model_name: Model to use
            resource_group: AI Core resource group (default: "default")
        """
        setup_aicore_config(service_key, resource_group)
        return cls(model_name)
    
    @classmethod
    def from_service_key_file(
        cls,
        path: str,
        model_name: str = "gpt-4o",
        resource_group: str = "default"
    ) -> "AICoreClient":
        """
        Create a client from a service key JSON file.
        
        Args:
            path: Path to service key JSON file
            model_name: Model to use
            resource_group: AI Core resource group
        """
        with open(path) as f:
            service_key = json.load(f)
        return cls.from_service_key(service_key, model_name, resource_group)
    
    @classmethod
    def from_env(
        cls,
        model_name: str = "gpt-4o",
        resource_group: str = "default"
    ) -> "AICoreClient":
        """
        Create a client from AICORE_SERVICE_KEY environment variable.
        """
        service_key_json = os.environ.get("AICORE_SERVICE_KEY")
        if not service_key_json:
            raise ValueError("AICORE_SERVICE_KEY environment variable not set")
        service_key = json.loads(service_key_json)
        return cls.from_service_key(service_key, model_name, resource_group)
    
    def chat(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        **kwargs
    ) -> str:
        """
        Send a chat message and get a response.
        
        Args:
            prompt: User message
            system_prompt: Optional system prompt
            temperature: Sampling temperature (0.0 - 2.0)
            max_tokens: Maximum tokens in response
            **kwargs: Additional parameters passed to the API
        
        Returns:
            Model response as string
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        return self.chat_with_messages(
            messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )
    
    def chat_with_messages(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 1024,
        **kwargs
    ) -> str:
        """
        Send a conversation (list of messages) and get a response.
        
        Args:
            messages: List of message dicts with "role" and "content" keys
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
            **kwargs: Additional parameters
        
        Returns:
            Model response as string
        """
        response = self._client.chat.completions.create(
            model_name=self.model_name,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )
        return response.choices[0].message.content
    
    def list_models(self) -> list[str]:
        """
        List available models from your AI Core deployments.
        """
        from gen_ai_hub.proxy.core.proxy_clients import get_proxy_client
        client = get_proxy_client("gen-ai-hub")
        return [d.model_name for d in client.deployments]


def main():
    parser = argparse.ArgumentParser(
        description="Call LLM models on SAP AI Core",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        "--service-key", "-k",
        help="Path to service key JSON file"
    )
    parser.add_argument(
        "--model", "-m",
        default="gpt-4o",
        help="Model name (default: gpt-4o)"
    )
    parser.add_argument(
        "--resource-group", "-g",
        default="default",
        help="AI Core resource group (default: default)"
    )
    parser.add_argument(
        "--prompt", "-p",
        help="Prompt to send to the model"
    )
    parser.add_argument(
        "--system", "-s",
        help="System prompt"
    )
    parser.add_argument(
        "--temperature", "-t",
        type=float,
        default=0.7,
        help="Temperature (default: 0.7)"
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=1024,
        help="Max tokens (default: 1024)"
    )
    parser.add_argument(
        "--list-models",
        action="store_true",
        help="List available models and exit"
    )
    parser.add_argument(
        "--save-config",
        action="store_true",
        help="Save configuration to ~/.aicore/config.json"
    )
    
    args = parser.parse_args()
    
    # Load service key
    if args.service_key:
        with open(args.service_key) as f:
            service_key = json.load(f)
        setup_aicore_config(service_key, args.resource_group)
        
        if args.save_config:
            save_aicore_config(service_key, args.resource_group)
            if not args.prompt and not args.list_models:
                return
    elif os.environ.get("AICORE_SERVICE_KEY"):
        service_key = json.loads(os.environ["AICORE_SERVICE_KEY"])
        setup_aicore_config(service_key, args.resource_group)
    # else: assume config already exists in ~/.aicore/config.json or env vars
    
    client = AICoreClient(args.model)
    
    if args.list_models:
        print("Available models:")
        for model in client.list_models():
            print(f"  - {model}")
        return
    
    if not args.prompt:
        parser.print_help()
        print("\nError: --prompt is required (unless using --list-models)")
        return
    
    response = client.chat(
        args.prompt,
        system_prompt=args.system,
        temperature=args.temperature,
        max_tokens=args.max_tokens
    )
    print(response)


if __name__ == "__main__":
    main()
