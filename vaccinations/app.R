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

theme_set( theme_bw() + theme( legend.position="bottom" ) +
               theme( legend.title=element_blank() ) )

load( 'app.RData' )
dfw <- dfw %>% mutate( date = as.Date(date,format='%Y-%m-%d') )

sc <- left_join(sites, sitecap, by=c('date','location','type')) 
#ids <- sc[1:6,'type']

#wcolors <- c('weekly_available','weekly_vaccinations','weekly_cap')
#cnames <- c('Min supply level in the week','Doses administered','Max vaccination capacity')
colors <- c('daily_vaccinations','cap')
cnames <- c('Doses administered','Max vaccination capacity')
dp <- dfw %>% tidyr::pivot_longer( cols = all_of(colors)
                         , names_to="s" 
                         , values_to = "value",  values_drop_na = TRUE )
dp <- dp %>% mutate( n = NA )
dp$n[dp$s %in% colors] <- cnames[match(dp$s,colors)]

# Define UI for application that draws a histogram
ui <- fluidPage(
    tags$style(type = "text/css",
               "label { font-size: 10px; }"
    ),
    # Sidebar with a slider input for number of bins 
    sidebarLayout(
        sidebarPanel(
            # Application title
            titlePanel("New England Vaccinations"),            
            selectInput( "state", NULL, NEstates, selected=NEstates[1] ),
            fluidRow( column( 6, numericInput('N1',
                                             paste0(sc[1,'type'],', number of sites:'),
                                             min = 0, max = 10, value = 0, step = 1) ),
                      column( 6, sliderInput('C1','Max doses/site/day:',
                                             min = 0, max = 10,
                                             value = 0, ticks = FALSE ) ) ),
            fluidRow( column( 6, numericInput('N2',
                                              paste0(sc[2,'type'],', number of sites:'),
                                              min = 0, max = 10, value = 0, step = 1) ),
                      column( 6, sliderInput('C2','Max doses/site/day:',
                                             min = 0, max = 10,
                                             value = 0, ticks = FALSE ) ) ),
            fluidRow( column( 6, numericInput('N3',
                                             paste0(sc[3,'type'],', number of sites:'),
                                             min = 0, max = 10, value = 0, step = 1) ),
                      column( 6, sliderInput('C3','Max doses/site/day:',
                                             min = 0, max = 10,
                                             value = 0, ticks = FALSE ) ) ),
            fluidRow( column( 6, numericInput('N4',
                                             paste0(sc[4,'type'],', number of sites:'),
                                             min = 0, max = 10, value = 0, step = 1) ),
                      column( 6, sliderInput('C4','Max doses/site/day:',
                                             min = 0, max = 10,
                                             value = 0, ticks = FALSE ) ) ),
            fluidRow( column( 6, numericInput('N5',
                                             paste0(sc[5,'type'],', number of sites:'),
                                             min = 0, max = 10, value = 0, step = 1) ),
                      column( 6, sliderInput('C5','Max doses/site/day:',
                                             min = 0, max = 10,
                                             value = 0, ticks = FALSE ) ) ),
            fluidRow( column( 6, numericInput('N6',
                                             paste0(sc[6,'type'],', number of sites:'),
                                             min = 0, max = 10, value = 0, step = 1) ),
                      column( 6, sliderInput('C6','Max doses/site/day:',
                                             min = 0, max = 10,
                                             value = 0, ticks = FALSE ) ) ),
            fluidRow( column( 6, numericInput('N7',
                                              paste0(sc[7,'type'],', number of sites:'),
                                              min = 0, max = 10, value = 0, step = 1) ),
                      column( 6, sliderInput('C7','Max doses/site/day:',
                                             min = 0, max = 10,
                                             value = 0, ticks = FALSE ) ) )
        ),

        # Show a plot of the generated distribution
        mainPanel(
            titlePanel(" "),            
            plotOutput("distPlot", height = "550px")
        )
    )
)

# Define server logic required to draw a histogram
server <- function(input, output, session) {
    
    stateInput <- reactive({
        # This reative function is executed every time the state changes
        scp <- sc %>% filter( location == input$state )
        
        # Control the value, min, max, and step.
        # Step size is 2 when input value is even; 1 when value is odd.
        for ( i in 1:7 ){
            updateNumericInput(session,paste0('N',i), value=scp[i,'Ni'], min=0, max=scp[i,'Ni']*2 )
            updateSliderInput(session, paste0('C',i), value=scp[i,'Ci'], min=0, max=scp[i,'Ci']*2 )
        }
        
#        print( paste("observe STATE CHANGED TO", input$state ))
        return( scp )
    })

    output$distPlot <- renderPlot({
        scp <- stateInput()

        for ( i in 1:7 ){
            scp[i,'Ni'] <- input[[paste0('N',i)]]
            scp[i,'Ci'] <- input[[paste0('C',i)]]
        }

        scp <- scp %>% mutate( cap = Ni * Ci )

        dt <- dp %>% filter( location==input$state )
        sumcap <- sum( scp$cap )
        dt[#dt$date>(latest_history_date-5) & 
            dt$s=='cap','value'] <- sumcap
        
        # find data where demand exceeds capacity, to draw a warning sign
        tmp <- dt %>% filter( s=='daily_vaccinations' & value>=sumcap )
        
        if ( nrow(tmp) > 0 ){
            exceed_date <- min( tmp$date )
            ymax <- max(dt$value)
            ggplot( dt, aes(x=date, y=value, color=n) ) +
#                geom_rect( aes(xmin=exceed_date), xmax=Inf, ymin=-Inf, ymax=Inf, fill='yellow', alpha=0.1, linetype='blank' ) +
                geom_line( size=1.5 ) +
                geom_vline(xintercept=latest_history_date, linetype="dashed", color="gray", size=1) +
                annotate("text", x=exceed_date-6, y=sumcap + ymax*.05, label=paste('Vaccination reaches\ncapacity on',exceed_date)) +
                theme(axis.title.x = element_blank()) +
                scale_x_date(date_labels = '%b%e' ) +
                ylab('Doses per Day') +
                scale_y_continuous(labels = scales::comma
                                  , expand = c(0, ymax*0.05), limits = c(0, NA)) +
                ggtitle( input$state ) +
                theme(plot.title = element_text(hjust = 0.5), text = element_text(size=20) )
        }
        else
            ggplot( dt, aes(x=date, y=value, color=n) ) +
                geom_line( size=1.5 ) +
                geom_vline(xintercept=latest_history_date, linetype="dashed", color="gray", size=1) +
                theme(axis.title.x = element_blank()) +
                scale_x_date(date_labels = '%b%e' ) +
                ylab('Doses per Day') +
                scale_y_continuous(labels = scales::comma
                               , expand = c(0, max(dt$value)*0.05), limits = c(0, NA)) +
                ggtitle( input$state ) +
                theme(plot.title = element_text(hjust = 0.5), text = element_text(size=20) )
    })
}

# Run the application 
shinyApp(ui = ui, server = server)
