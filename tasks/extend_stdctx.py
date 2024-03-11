import json
import requests
from cumulusci.tasks.sfdx import SFDXBaseTask
from cumulusci.core.keychain import BaseProjectKeychain
from abc import abstractmethod

class ExtendStandardContext(SFDXBaseTask):
    keychain_class = BaseProjectKeychain
    
    task_options = {
        'access_token': {
            'description': 'The access token for the org. Defaults to the project default',
        }
    }

    def _init_options(self, kwargs):
        super()._init_options(kwargs)
        self.env = self._get_env()

    @property
    def keychain_cls(self):
        return self.get_keychain_class() or self.keychain_class

    @abstractmethod
    def get_keychain_class(self):
        return None

    @property
    def keychain_key(self):
        return self.get_keychain_key()

    @abstractmethod
    def get_keychain_key(self):
        return None

    def _load_keychain(self):
        if hasattr(self, 'keychain') and self.keychain:
            return

        keychain_key = self.keychain_key if self.keychain_cls.encrypted else None
        self.keychain = self.keychain_cls(self.project_config or self.universal_config, keychain_key)
        
        if self.project_config:
            self.project_config.keychain = self.keychain

    def _prepruntime(self):
        self._load_keychain()
        self.accesstoken = self.options.get("accesstoken") or self.org_config.access_token
        self.instanceurl = self.options.get("instanceurl") or self.org_config.instance_url
    
    def _run_task(self):
        self._prepruntime()
        self._extend_context_definition()

    def _extend_context_definition(self):
        url = f"{self.instanceurl}/services/data/v{self.project_config.project__package__api_version}/connect/context-definitions"
        headers = {
            "Authorization": f"Bearer {self.accesstoken}",
            "Content-Type": "application/json",
        }
        payload = {
            "name": "RLM_SalesTransactionContext",
            "description": "Extension of Standard Sales Transaction Context",
            "developerName": "RLM_SalesTransactionContext",
            "baseReference": "SalesTransactionContext__stdctx",
            "startDate": "2024-01-01T00:00:00.000Z"
        }
        response = requests.post(url, headers=headers, json=payload)

        if response.ok:
            response_json = response.json()
            context_id = response_json.get('contextDefinitionId')

            if context_id:
                self.logger.info(f"Context ID: {context_id}")
                self.context_id = context_id
                response_json = self._get_context_mapping()
                version_list = response_json.get('contextDefinitionVersionList', [])

                if version_list:
                    context_mappings = version_list[0].get('contextMappings', [])
                    sales_transaction_mapping_id = next(
                        (m['contextMappingId'] for m in context_mappings if m.get("name") == "SalesTransaction"),
                        None
                    )
                    if sales_transaction_mapping_id:
                        self.sales_transaction_mapping_id = sales_transaction_mapping_id
                        self.logger.info(f"Sales Transaction Context Mapping ID: {sales_transaction_mapping_id}")
                        self._update_context_mappings()
                        self._activate_context_id()
                    else:
                        self.logger.error("SalesTransaction Context Mapping ID not found.")
                else:
                    self.logger.error("Context Definition Version List is empty.")
            else:
                self.logger.error("No context ID found")
        else:
            self.logger.error(f"Create request failed with status code {response.status_code}")

    def _update_context_mappings(self):
        url = f"{self.instanceurl}/services/data/v{self.project_config.project__package__api_version}/connect/context-definitions/{self.context_id}/context-mappings"
        headers = {
            "Authorization": f"Bearer {self.accesstoken}",
            "Content-Type": "application/json",
        }
        payload = {
            "contextMappings": [
                {
                    "contextMappingId": self.sales_transaction_mapping_id,
                    "isDefault": "true",
                    "name": "SalesTransaction"
                }
            ]
        }
        response = requests.patch(url, headers=headers, json=payload)

        if not response.ok:
            self.logger.error(f"Patch request failed with status code {response.status_code}")

    def _activate_context_id(self):
        url = f"{self.instanceurl}/services/data/v{self.project_config.project__package__api_version}/connect/context-definitions/{self.context_id}"
        headers = {
            "Authorization": f"Bearer {self.accesstoken}",
            "Content-Type": "application/json",
        }
        payload = {"isActive": "true"}
        response = requests.patch(url, headers=headers, json=payload)

        if not response.ok:
            self.logger.error(f"Patch request failed with status code {response.status_code}")

    def _get_context_mapping(self):
        url = f"{self.instanceurl}/services/data/v{self.project_config.project__package__api_version}/connect/context-definitions/{self.context_id}"
        headers = {
            "Authorization": f"Bearer {self.accesstoken}",
            "Content-Type": "application/json",
        }
        response = requests.get(url, headers=headers)
        return response.json() if response.ok else {}
