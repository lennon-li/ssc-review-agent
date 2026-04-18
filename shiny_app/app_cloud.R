library(shiny)
library(bslib)
library(reticulate)
library(DT)
library(jsonlite)
library(htmltools)
library(shinyjs)

# Increase upload limit to 100MB to be safe
options(shiny.maxRequestSize = 100 * 1024^2)

# Setup reticulate for Cloud environment
# We use the python in the python:3.11-slim container
use_python("/usr/local/bin/python", required = TRUE)

# --- UI Definition ---
ui <- page_navbar(
  id = "main_nav",
  useShinyjs(), 
  title = "SSC Accreditation Review Agent (Cloud)",
  theme = bs_theme(
    version = 5, 
    bootswatch = "flatly",
    primary = "#2c3e50",
    base_font = font_google("Inter")
  ),
  
  header = tags$head(
    tags$style(HTML("
      .navbar { box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 0px !important; }
      .nav-pills .nav-link { border-radius: 8px; padding: 8px 20px; margin-right: 12px; color: #2c3e50; border: 2px solid #ecf0f1; background-color: #f8f9fa; }
      .nav-pills .nav-link.active { background-color: #2c3e50 !important; color: white !important; }
      .container-fluid { padding-top: 10px !important; }
      
      /* Terminal-style log */
      #process_status { 
        background-color: #1e1e1e; color: #00ff00; 
        font-family: 'Consolas', monospace; 
        height: 200px; 
        font-size: 0.85em; 
        overflow-y: scroll;
        border-radius: 8px;
        padding: 10px;
      }
      
      .profile-card { display: flex; align-items: center; gap: 20px; padding: 15px; background: #fff; border-radius: 12px; border: 1px solid #e1e8ed; margin-bottom: 10px; }
      .profile-img { width: 80px; height: 80px; border-radius: 50%; object-fit: cover; border: 2px solid #2c3e50; background: #eee; }
      .attention-banner { background: #fff5f5; border-left: 5px solid #e74c3c; padding: 10px; margin-bottom: 10px; border-radius: 4px; }
      
      /* Increase frame height for tables */
      .dt-container { min-height: 600px; }
      .card-body { overflow-y: auto; }
    "))
  ),

  nav_panel("1. Setup", icon = icon("upload"), value = "setup_tab",
    layout_sidebar(
      sidebar = sidebar(
        title = "Application Materials",
        fileInput("files_upload", "Select PDFs/DOCXs (Max 100MB):", multiple = TRUE, accept = c(".pdf", ".docx", ".txt", ".jpg", ".png", ".jpeg")),
        actionButton("btn_run", "Run Assessment", class = "btn-success w-100", icon = icon("play")),
        hr(),

        selectInput("evaluator_type", "AI Engine:", choices = c("Vertex AI (Gemini)" = "vertex")),
        hr(),
        helpText("Files are processed in a secure temporary environment. No data is stored permanently.")
      ),
      layout_column_wrap(
        width = 1,
        card(
          card_header("Uploaded Documents"),
          tableOutput("file_list")
        ),
        card(
          card_header("Activity Log"),
          verbatimTextOutput("process_status")
        )
      )
    )
  ),
  
  nav_panel("2. Review & Report", icon = icon("clipboard-check"), value = "review_tab",
    layout_sidebar(
      sidebar = sidebar(
        title = "Export Report",
        downloadButton("download_html", "Export HTML", class = "btn-info w-100 mb-2"),
        downloadButton("download_md", "Export Markdown", class = "btn-outline-info w-100 mb-2"),
        downloadButton("download_docx", "Export DOCX", class = "btn-outline-primary w-100 mb-2"),
        downloadButton("download_latex", "Export LaTeX", class = "btn-outline-secondary w-100 mb-2"),
        hr(),
        checkboxInput("filter_attention", "Show Only Flagged Items", FALSE)
      ),
      div(
        uiOutput("profile_header"),
        uiOutput("overall_stats"),
        navset_card_pill(
          id = "assessment_tabs",
          nav_panel("Executive Summary", 
            card(style = "min-height: 400px;",
              card_body(textOutput("overall_summary_text"))
            )
          ),
          nav_panel("Course Checklist", 
            card(style = "min-height: 600px;",
              card_body(DTOutput("course_checklist_table"))
            )
          ),
          nav_panel("Criteria Assessment", 
            card(style = "min-height: 600px;",
              card_body(DTOutput("criteria_table"))
            )
          ),
          nav_panel("Final Report Preview", 
            card(style = "min-height: 800px;",
              card_body(uiOutput("html_report_preview"))
            )
          )
        )
      )
    )
  ),
  
  footer = tags$footer(
    style = "text-align: center; padding: 20px; color: #7f8c8d; font-size: 0.9em; border-top: 1px solid #ecf0f1;",
    paste("SSC Review Agent | Last Updated:", format(Sys.Date(), "%B %d, %Y"))
  )
)

server <- function(input, output, session) {
  state <- reactiveValues(
    files = NULL,
    evaluation = NULL,
    status_log = "System Ready. Please upload application files.",
    criteria_df = NULL,
    course_df = NULL,
    photo_path = NULL,
    temp_folder = NULL
  )
  
  log_info <- function(msg) {
    state$status_log <- paste0(state$status_log, "\n", "[", format(Sys.time(), "%H:%M:%S"), "] ", msg)
  }
  
  observeEvent(input$files_upload, {
    req(input$files_upload)
    state$temp_folder <- file.path(tempdir(), "applicant_files")
    if (dir.exists(state$temp_folder)) unlink(state$temp_folder, recursive = TRUE)
    dir.create(state$temp_folder, recursive = TRUE)
    
    withProgress(message = 'Uploading files...', value = 0, {
      for (i in 1:nrow(input$files_upload)) {
        file.copy(input$files_upload$datapath[i], file.path(state$temp_folder, input$files_upload$name[i]))
        incProgress(1/nrow(input$files_upload), detail = paste("Copying:", input$files_upload$name[i]))
      }
      
      state$files <- data.frame(Filename = input$files_upload$name)
      
      # Use backend from server scope
      py_run_string("import sys; import os; sys.path.append('/app')")
      py_run_string("import agent.app_backend as backend")
      backend <- import("agent.app_backend")
      
      photo_name <- backend$find_applicant_photo(state$temp_folder)
      if (!is.null(photo_name)) {
        addResourcePath("temp_res", state$temp_folder)
        state$photo_path <- paste0("temp_res/", photo_name)
      } else {
        state$photo_path <- NULL
      }
      
      log_info(paste("Uploaded", nrow(input$files_upload), "files successfully."))
    })
  })
  
  observeEvent(input$btn_run, {
    req(state$temp_folder)
    shinyjs::disable("btn_run")
    
    # Ensure backend is imported
    py_run_string("import sys; import os; sys.path.append('/app')")
    backend <- import("agent.app_backend")
    
    withProgress(message = 'AI Analysis Stage 1/3', value = 0.1, {
      log_info("Extracting text from documents...")
      setProgress(0.2, detail = "Reading PDFs and DOCXs...")
      
      tryCatch({
        # Granular logging for Vertex AI
        log_info("Preparing prompt with SSC rubric...")
        setProgress(0.4, detail = "Building context for Vertex AI...")
        
        log_info(paste("Calling Vertex AI (", input$evaluator_type, ")... this may take 30-60 seconds."))
        setProgress(0.6, detail = "Gemini is reviewing application materials...")
        
        result <- backend$run_folder_evaluation(state$temp_folder, input$evaluator_type)
        
        log_info("AI response received. Processing structured data...")
        setProgress(0.8, detail = "Formatting results...")
        
        state$evaluation <- result
        
        if (length(result$criteria) > 0) {
          df_crit <- as.data.frame(do.call(rbind, result$criteria))
          for(col in names(df_crit)) df_crit[[col]] <- unlist(df_crit[[col]])
          state$criteria_df <- df_crit
        }
        
        if (!is.null(result$course_checklist) && length(result$course_checklist) > 0) {
          df_course <- as.data.frame(do.call(rbind, result$course_checklist))
          for(col in names(df_course)) df_course[[col]] <- unlist(df_course[[col]])
          state$course_df <- df_course
        }
        
        setProgress(1, detail = "Success!")
        log_info("Assessment Complete. Switching to Review tab...")
        
        # Show success modal
        showModal(modalDialog(
          title = "AI Review Complete",
          "The SSC Review Agent has finished analyzing the application materials. You have been switched to the 'Review & Report' tab.",
          footer = modalButton("Dismiss"),
          easyClose = TRUE,
          fade = TRUE
        ))
        
        # Switch tab
        updateNavbarPage(session, "main_nav", selected = "review_tab")
        updateTabsetPanel(session, "assessment_tabs", selected = "Executive Summary")
        
      }, error = function(e) {
        log_info(paste0("[Error] AI failed: ", e$message))
        showNotification(paste("AI Error:", e$message), type = "error")
      })
    })
    shinyjs::enable("btn_run")
  })

  output$file_list <- renderTable({ state$files })
  output$process_status <- renderText({ state$status_log })
  
  output$profile_header <- renderUI({
    req(state$evaluation)
    div(class = "profile-card",
      if (!is.null(state$photo_path)) { img(src = state$photo_path, class = "profile-img") }
      else { div(class = "profile-img", style="display:flex; align-items:center; justify-content:center; background:#ddd;", icon("user", "fa-2x")) },
      div(class = "profile-info", h3(state$evaluation$applicant_id))
    )
  })
  
  output$overall_stats <- renderUI({
    req(state$evaluation)
    color <- if(state$evaluation$ready_for_human_review) "success" else "warning"
    text <- if(state$evaluation$ready_for_human_review) "Ready for Approval" else "Review Required"
    layout_column_wrap(width = 1, value_box(title = "AI Consensus Status", value = text, theme = color, showcase = icon("robot")))
  })
  
  output$overall_summary_text <- renderText({ state$evaluation$overall_summary })
  
  output$course_checklist_table <- renderDT({
    req(state$course_df)
    datatable(state$course_df, 
              options = list(pageLength = 25, scrollX = TRUE, autoWidth = TRUE),
              style = "bootstrap4") %>%
      formatStyle('is_satisfied', backgroundColor = styleEqual(c(TRUE, FALSE), c('#d4edda', '#f8d7da')))
  })
  
  output$criteria_table <- renderDT({
    req(state$criteria_df)
    df <- state$criteria_df
    if (input$filter_attention) df <- df[df$needs_human_attention == TRUE, ]
    
    datatable(df, 
              editable = list(target = "cell", disable = list(columns = c(0, 1, 2, 3, 4, 5))), 
              options = list(pageLength = 25, scrollX = TRUE),
              style = "bootstrap4") %>%
      formatStyle('needs_human_attention', backgroundColor = styleEqual(c(TRUE, FALSE), c('#fff5f5', 'transparent')))
  })
  
  observeEvent(input$criteria_table_cell_edit, { state$criteria_df <- editData(state$criteria_df, input$criteria_table_cell_edit) })

  generate_report_html <- function() {
    req(state$evaluation)
    eval <- state$evaluation
    criteria_list <- if (!is.null(state$criteria_df)) lapply(seq_len(nrow(state$criteria_df)), function(i) as.list(state$criteria_df[i, ])) else list()
    courses <- if(!is.null(state$course_df)) state$course_df else data.frame()
    tagList(
      div(style="max-width: 850px; margin: auto; padding: 30px; font-family: 'Inter', sans-serif;",
        div(style="display:flex; align-items:center; gap:30px; border-bottom: 3px solid #2c3e50; padding-bottom:20px; margin-bottom:30px;",
          if (!is.null(state$photo_path)) { img(src = state$photo_path, style="width:100px; height:100px; border-radius:10px; border:2px solid #2c3e50;") },
          div(h1(style="margin:0; color:#2c3e50;", "Accreditation Review"), h3(style="color:#7f8c8d;", eval$applicant_id))
        ),
        h3("Executive Summary"), p(style="line-height:1.6; font-size:1.1em;", eval$overall_summary),
        hr(), h3("Course Checklist"),
        if(nrow(courses) > 0) {
          tags$table(class="table table-bordered", tags$tbody(lapply(seq_len(nrow(courses)), function(i) { 
            row <- courses[i, ]; tags$tr(tags$td(row$module), tags$td(row$course_code), tags$td(if(row$is_satisfied) "Satisfied ✅" else "Missing/Fail ❌")) 
          })))
        } else { p("No course data.") },
        hr(), h3("Detailed Criterion Assessment"),
        lapply(criteria_list, function(c) { 
          div(style="margin-bottom:15px; border:1px solid #e1e8ed; padding:15px; border-radius:8px;", 
            div(style="display:flex; justify-content:space-between;", strong(c$criterion_name), span(if(c$needs_human_attention) "⚠️" else "✅")),
            p(style="color:#555; margin-top:10px; font-style:italic;", c$supporting_evidence)
          ) 
        })
      )
    )
  }
  
  output$html_report_preview <- renderUI({ generate_report_html() })
  
  output$download_html <- downloadHandler(
    filename = function() { paste0("SSC_Report_", state$evaluation$applicant_id, ".html") },
    content = function(file) {
      report_content <- generate_report_html()
      full_html <- tags$html(
        tags$head(tags$link(rel="stylesheet", href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css")),
        tags$body(style="padding: 30px; background: #fff;", report_content)
      )
      writeLines(as.character(full_html), file)
    }
  )
  
  output$download_md <- downloadHandler(
    filename = function() { paste0("SSC_Report_", state$evaluation$applicant_id, ".md") },
    content = function(file) {
      md_content <- backend$generate_markdown_report(state$evaluation)
      writeLines(md_content, file)
    }
  )
  
  output$download_latex <- downloadHandler(
    filename = function() { paste0("SSC_Report_", state$evaluation$applicant_id, ".tex") },
    content = function(file) {
      tex_content <- backend$generate_latex_report(state$evaluation)
      writeLines(tex_content, file)
    }
  )
  
  output$download_docx <- downloadHandler(
    filename = function() { paste0("SSC_Report_", state$evaluation$applicant_id, ".docx") },
    content = function(file) {
      backend$generate_docx_report(state$evaluation, file)
    }
  )
}

# Run the app on the port provided by Cloud Run
port <- as.numeric(Sys.getenv("PORT", "8080"))
shinyApp(ui, server, options = list(port = port, host = "0.0.0.0"))
