# terra-workflow-scale-test-tools


# Description
Tools for scale testing GA4GH DRS data access using Terra workflows.

This includes:
* Monitoring and graphical reporting of the response times for key services/endpoints during the workflow execution
* Extraction and graphical reporting of the workflow DRS data access rate


These tools were designed to work with all Terra-supported DRS data services. The programs currently supported include:
 * NHLBI BioData Catalyst
 * NCI Cancer Research Data Commons 

And on all Terra deployment tiers. The deployment tiers currently supported are:
 * dev
 * alpha
 * prod

The response time monitoring currently includes support for:
* Terra Martha
* Terra Bond
* Gen3 IndexD
* Gen3 Fence

The response time monitoring tools can be extended to include additional data sources (e.g., projects hosted on Terra Data Repo) and Terr backend services (e.g. `terra-drs-hub`, `terra-external-credentials-manager`) and their endpoints of interest.

# Example Graphs Produced

## DRS Data Access Rate
![DRS Data Access Rate](doc/images/example_graphs/example_drs_data_access_rate_graph.png)
## Response Time Monitoring

### Martha Response Times
![Martha Response Times](doc/images/example_graphs/example_martha_response_times_graph.png)

### DRS Flow Response Times
![DRS Flow Response Times](doc/images/example_graphs/example_drs_flow_response_times_graph.png)

### Bond Endpoint Response Times
![Bond Endpoint Response Times](doc/images/example_graphs/example_bond_endpoint_response_times_graph.png)

# Setting up a New Terra Workspace for Testing
The typical and recommended use is to set up one test workspace per deployment tier and use that workspace on an ongoing basis.
This provides a useful history of test runs in Job Manager.
1. Clone this repository to your local system.
2. Login to Terra in the desired Terra deployment tier (dev, alpha, ..., prod) in which the tests will be run.  
3. Create a new workspace.
4. Import the test data in the `test_drs_uris` into the Terra data tables appropriate for the deployment tier (`pre-production` or `production`).
5. Add the WDL file(s) in the `workflows` directory to the Broad Methods Repository, then export to the workspace.  
   Also add the `md5sum` workflow available from Dockstore [here](https://dockstore.org/workflows/github.com/briandoconnor/dockstore-workflow-md5sum/dockstore-wdl-workflow-md5sum:1.4.0?tab=info)
6. Import the Jupyter Notebook `monitor_workflow_and_report_results.ipynb`

# Running a Scale Test
1. In Terra, create/start a Jupyter Cloud Environment.  
  Recommended minimum configuration:
    * Image: Current Default (for Python, etc.)
    * CPUs: 4 (or more)
    * Memory: The minimum provided for the number of CPUs
    * Disk space: 50 GB (or more)
    * Autopause: 60 minutes of inactivity
2. Create a copy of the `monitor_workflow_and_report_results` Notebook to use for this specific test.
The current naming convention is:  
`   monitor_workflow_and_report_results_`*<workflow_name>*`_`*<input_config>*`_`*<YYYYMMDD_HHMM>*`ET`  
For example:  
`   monitor_workflow_and_report_results_scatter_20k_by_10_20220506_1352ET`
3. Open the new Notebook in edit mode (not Playground Mode)
4. Start the whole Notebook running (e.g., menu Cell: Run All)  
It will stop at the point where it prompts for user input.
5. Configure and start the workflow with the desired input configuration.  
    **UNcheck `Use call caching` to ensure data access will be performed.**
6. Copy the workflow `Submission ID` and paste it into the Notebook UI `Submission Id` text field.
7. Set the Notebook UI radio buttons for the deployment tier and data service to be tested.
8. Select Notebook cell after the UI and select Cell: Run All Below
9. The Notebook should then complete unattended, and when the workflow has ended (based on the top-level submission status) it will process the results and display the graphs.


# Test Tips
* When running the `md5sum` workflow at higher scales (20k-30k inputs) copying the log files for analysis can take a very long time. 
When running such tests, use of 16+ CPUs will increase the parallel copy performance and substantially reduce the time required for this step.

# Test Troubleshooting
* Sometimes the workflow submission status remains as `Submitted` even when the workflow has finished.
In this case, it is necessary to stop the response time monitoring by selecting Kernel: Interrupt and resuming execution at the following cell.