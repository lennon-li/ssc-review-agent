library(shiny)
library(jsonlite)

# Define UI
ui <- fluidPage(
  titlePanel("SSC Review Agent - Human Feedback"),
  sidebarLayout(
    sidebarPanel(
      fileInput("eval_file", "Choose Evaluation JSON", accept = ".json"),
      hr(),
      textInput("reviewer_name", "Reviewer Name"),
      actionButton("save_btn", "Save Feedback")
    ),
    mainPanel(
      h3("Applicant Summary"),
      textOutput("applicant_summary"),
      hr(),
      h3("Criteria Assessment"),
      uiOutput("criteria_ui")
    )
  )
)

# Define Server
server <- function(input, output, session) {
  
  eval_data <- reactive({
    req(input$eval_file)
    fromJSON(input$eval_file$datapath)
  })
  
  output$applicant_summary <- renderText({
    eval_data()$overall_summary
  })
  
  output$criteria_ui <- renderUI({
    criteria <- eval_data()$criteria
    tagList(
      lapply(1:nrow(criteria), function(i) {
        wellPanel(
          h4(criteria$criterion_name[i]),
          p(strong("Recommended Rating: "), criteria$recommended_rating[i]),
          p(strong("Evidence: "), criteria$supporting_evidence[i]),
          textAreaInput(paste0("override_", i), "Reviewer Override/Comments", value = criteria$reviewer_override[i])
        )
      })
    )
  })
}

# Run the app
# shinyApp(ui = ui, server = server)
