#
# This is a Shiny web application. You can run the application by clicking
# the 'Run App' button above.
#
# Find out more about building applications with Shiny here:
#
#    http://shiny.rstudio.com/
#

library(dplyr)
library(ggplot2)
library(openxlsx)
library(shiny)

load( 'app.RData' )
wcap <- wcap %>% mutate( date = as.Date(date,format='%Y-%m-%d') )

sc <- left_join(sites, sitecap, by=c('date','location','type')) 
ids <- sc[1:6,'type']

wcolors <- c('weekly_available','weekly_vaccinations','weekly_cap')
cnames <- c('Min supply level in the week','Doses administered','Max vaccination capacity (FAKE)')
dp <- wcap %>% tidyr::pivot_longer( cols = all_of(wcolors)
                         , names_to="s" 
                         , values_to = "value",  values_drop_na = TRUE )
dp <- dp %>% mutate( n = NA )
dp$n[dp$s %in% wcolors] <- cnames[match(dp$s,wcolors)]

# Define UI for application that draws a histogram
ui <- fluidPage(

    # Application title
    titlePanel("New England Vaccinations"),

    # Sidebar with a slider input for number of bins 
    sidebarLayout(
        sidebarPanel(
            sliderInput(ids[1],
                        paste('Add or reduce',ids[1],'maximum capacity (%):'),
                        min = -100,
                        max = 200,
                        value = 0),
            sliderInput(ids[2],
                        paste('Add or reduce',ids[2],'maximum capacity (%):'),
                        min = -100,
                        max = 200,
                        value = 0),
            sliderInput(ids[3],
                        paste('Add or reduce',ids[3],'maximum capacity (%):'),
                        min = -100,
                        max = 200,
                        value = 0),
            sliderInput(ids[4],
                        paste('Add or reduce',ids[4],'maximum capacity (%):'),
                        min = -100,
                        max = 200,
                        value = 0),
            sliderInput(ids[5],
                        paste('Add or reduce',ids[5],'maximum capacity (%):'),
                        min = -100,
                        max = 200,
                        value = 0),
            sliderInput(ids[6],
                        paste('Add or reduce',ids[6],'maximum capacity (%):'),
                        min = -100,
                        max = 200,
                        value = 0)
        ),

        # Show a plot of the generated distribution
        mainPanel(
           plotOutput("distPlot", height = "700px")
        )
    )
)

# Define server logic required to draw a histogram
server <- function(input, output) {

    output$distPlot <- renderPlot({
        # generate bins based on input$bins from ui.R
        scp <- sc
        for ( id in ids )
            scp[scp$type==id,'Ni'] <- sc[sc$type==id,'Ni'] * (1 + input[[id]]/100)

        scp <- scp %>% group_by(date, location) %>%
            summarise( cap = sum( Ni * Ci ), .groups='drop_last' )

        dt <- dp
        for ( state in unique(dt$location) )
            dt[dt$location==state & dt$date>(latest_history_date-5) & dt$s=='weekly_cap'
                                                    ,'value'] <- scp$cap[scp$location==state]*7
        ggplot( dt, aes(x=date, y=value, color=n) ) +
            facet_wrap('~ location', nrow=3, scale='free_y' ) +
            geom_line() +
            geom_vline(xintercept=latest_history_date, linetype="dashed",
                        color = "gray") +  # , size=1.5
            theme(axis.title.x = element_blank()) +
            scale_x_date(date_labels = '%b%e' ) +
            ylab('Doses per week') +
            scale_y_continuous(label = scales::unit_format(unit = "K", scale = 1e-3, sep = "")
                                , expand = c(0, 0), limits = c(0, NA))
    })
}

# Run the application 
shinyApp(ui = ui, server = server)
