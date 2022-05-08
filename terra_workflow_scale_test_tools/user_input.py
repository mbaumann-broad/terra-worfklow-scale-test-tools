import ipywidgets as widgets
from IPython.display import display


class UserInputUI:
    def __init__(self):
        self.submission_id_tb = widgets.Text(
            description='Submission Id:',
            value=None,
            placeholder='XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX',
            style={'description_width': 'initial'},
            layout=widgets.Layout(width='450px')
        )

        self.data_service_rb = widgets.RadioButtons(
            description='Data Service:',
            options=['BDC', 'CRDC'],
            value='BDC',  # Defaults to 'BDC'
            style={'description_width': 'initial'},
            layout={'width': 'max-content'}
        )

        self.terra_deployment_tier_rb = widgets.RadioButtons(
            description='Terra Deployment Tier:',
            options=['DEV', 'ALPHA', 'PROD'],
            value='ALPHA',  # Defaults to 'ALPHA'
            layout={'width': 'max-content'},
            style={'description_width': 'initial'}
        )

        self.monitor_response_times_cb = widgets.Checkbox(
            value=True,
            description='Monitor Response Times',
            indent=False
        )

        self.copy_workflow_logs_for_analysis_cb = widgets.Checkbox(
            value=True,
            description='Copy Workflow Logs for Analysis',
            indent=False
        )

        self.extract_timeseries_data_cb = widgets.Checkbox(
            value=True,
            description='Extract Time Series Data',
            indent=False
        )

        self.extract_timeseries_data_cb = widgets.Checkbox(
            value=True,
            description='Extract Time Series Data',
            indent=False
        )

        self.display_timeseries_graphs_cb = widgets.Checkbox(
            value=True,
            description='Display Time Series Graphs',
            indent=False
        )

        self.grid = widgets.GridspecLayout(7, 1)
        self.grid[0, 0] = self.terra_deployment_tier_rb
        self.grid[1, 0] = self.data_service_rb
        self.grid[2, 0] = self.submission_id_tb
        self.grid[3, 0] = self.monitor_response_times_cb
        self.grid[4, 0] = self.copy_workflow_logs_for_analysis_cb
        self.grid[5, 0] = self.extract_timeseries_data_cb
        self.grid[6, 0] = self.display_timeseries_graphs_cb

    def display(self) -> None:
        return display(self.grid)

    def get_submission_id(self) -> str:
        return self.submission_id_tb.value

    def get_data_service(self) -> str:
        return self.data_service_rb.value

    def get_terra_deployment_tier(self) -> str:
        return self.terra_deployment_tier_rb.value

    def is_monitor_response_times(self) -> bool:
        return self.monitor_response_times_cb.value

    def is_copy_workflow_logs_for_analysis(self) -> bool:
        return self.copy_workflow_logs_for_analysis_cb.value

    def is_extract_timeseries_data(self) -> bool:
        return self.extract_timeseries_data_cb.value

    def is_display_timeseries_graphs(self) -> bool:
        return self.display_timeseries_graphs_cb.value
