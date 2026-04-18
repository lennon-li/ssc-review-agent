#!/bin/bash
set -e

# Run the Shiny app
# We use the cloud-optimized app version
Rscript -e "shiny::runApp('shiny_app/app_cloud.R', host = '0.0.0.0', port = 8080)"
