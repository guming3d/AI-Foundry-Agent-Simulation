import pytest

from src.templates.template_loader import TemplateLoader


@pytest.mark.integration
def test_loads_all_builtin_templates():
    loader = TemplateLoader()
    template_ids = loader.list_templates()

    assert template_ids

    for template_id in template_ids:
        profile = loader.load_template(template_id)
        assert profile.metadata.id
        assert profile.agent_types
