import ipywidgets as widgets
from IPython.display import display

class UserInputUI:

    def build(self) -> None:
        self.submission_id_tb = widgets.Text(
            description='Workflow Submission Id:',
            value=None,
            placeholder='XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX',
            style={'description_width': 'initial'},
            layout = widgets.Layout(width='450px')
        )

        self.data_service_rb = widgets.RadioButtons(
            description='Data Service:',
            options=['BDC', 'CRDC'],
            value='BDC', # Defaults to 'BDC'
            style={'description_width': 'initial'},
            layout={'width': 'max-content'}
        )

        self.terra_deployment_tier_rb = widgets.RadioButtons(
            description='Terra Deployment Tier:',
            options=['DEV', 'ALPHA'],
            value='ALPHA', # Defaults to 'ALPHA'
            layout={'width': 'max-content'},
            style={'description_width': 'initial'}
        )

        self.grid = widgets.GridspecLayout(3, 1)
        self.grid[0, 0] = self.submission_id_tb
        self.grid[1, 0] = self.data_service_rb
        self.grid[2, 0] = self.terra_deployment_tier_rb

    def display(self) -> None:
        return display(self.grid)

    def get_submission_id(self) -> str:
        return self.submission_id_tb.value

    def get_data_service(self) -> str:
        return self.data_service_rb.value

    def get_terra_deployment_tier(self) -> str:
        return self.terra_deployment_tier_rb.value


