from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[2]
CONFIGMAP = ROOT / "manifests" / "sample-app" / "10-configmap-code.yaml"
DEPLOYMENT = ROOT / "manifests" / "sample-app" / "30-deployment.yaml"

RAG_ENV_KEYS = ["EMBEDDINGS_URL", "EMBEDDINGS_MODEL", "RERANK_URL", "RERANK_MODEL"]


class ManifestRagEnvTest(unittest.TestCase):
    def test_configmap_defines_phase_a_retrieval_settings(self):
        text = CONFIGMAP.read_text()
        for key in RAG_ENV_KEYS:
            self.assertRegex(text, rf"(?m)^\s{{2}}{key}:\s*\S", f"ConfigMap missing {key}")

    def test_backend_deployment_wires_retrieval_settings_from_configmap(self):
        text = DEPLOYMENT.read_text()
        backend_section = text.split("- name: backend", 1)[1].split("---", 1)[0]
        for key in RAG_ENV_KEYS:
            pattern = rf"- name: {key}\n\s+valueFrom:\n\s+configMapKeyRef:\n\s+name: sample-chat-config\n\s+key: {key}"
            self.assertRegex(backend_section, pattern, f"backend Deployment does not source {key} from sample-chat-config")

    def test_frontend_does_not_receive_provider_secret_or_retrieval_urls(self):
        text = DEPLOYMENT.read_text()
        frontend_section = text.split("- name: frontend", 1)[1]
        forbidden = ["OPENAI_DEFAULT_APIKEY", *RAG_ENV_KEYS]
        for key in forbidden:
            self.assertNotRegex(frontend_section, rf"- name: {key}\b", f"frontend should not receive {key}")


if __name__ == "__main__":
    unittest.main()
