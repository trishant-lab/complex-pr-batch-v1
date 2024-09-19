


from app.cli.penknife.models.penknifespec import PenknifeSpec
from app.cli.workflowbase import ProductWorkflow


ProductName = "penknife"

class PenknifeWorkflow(ProductWorkflow):
    """
    PenknifeWorkflow class
    """

    @staticmethod
    async def onboard(schema: dict) -> None:
        """
        onboard method
        """
        from app.core.settings import PenknifeSettings, get_settings
        from app.cli.temporal.penknife.starter import trigger_workflow

        product_config: PenknifeSettings
        # await trigger_workflow(
        #     workflow_input=PenknifeSpec(**schema),
        #     workflow=
        # )

