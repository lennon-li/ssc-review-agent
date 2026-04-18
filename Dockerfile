FROM python:3.11-slim

# Install R and system dependencies
# Added libuv1-dev for 'fs', libfontconfig1-dev for 'sass'/'bslib'
RUN apt-get update && apt-get install -y \
    r-base \
    r-base-dev \
    libcurl4-gnutls-dev \
    libssl-dev \
    libxml2-dev \
    libxt-dev \
    zlib1g-dev \
    libuv1-dev \
    libfontconfig1-dev \
    libfreetype6-dev \
    procps \
    && rm -rf /var/lib/apt/lists/*

# Install R packages and verify success
RUN Rscript -e "pkgs <- c('shiny', 'bslib', 'reticulate', 'DT', 'jsonlite', 'htmltools', 'shinyjs'); \
    install.packages(pkgs, repos='https://cran.rstudio.com/'); \
    if (!all(pkgs %in% installed.packages())) { \
      missing <- pkgs[!(pkgs %in% installed.packages())]; \
      stop(paste('Failed to install:', paste(missing, collapse=', '))); \
    }"

# Set working directory
WORKDIR /app

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app
COPY . .

# Environment variables
ENV PORT=8080
ENV PYTHON_PATH=/usr/local/bin/python

# Start command
CMD ["Rscript", "-e", "shiny::runApp('shiny_app/app_cloud.R', host='0.0.0.0', port=as.numeric(Sys.getenv('PORT')))"]
