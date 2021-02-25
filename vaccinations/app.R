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
library(shinyWidgets)

# If this variable is TRUE, shows two tabs where the first is the capacity comparison per state and the 
# second tab is the vaccination comparison across states
# if the variable is FALSE, only the content of the first tab is displayed
FEMA_version <- TRUE

theme_set( theme_bw() + theme( legend.position="bottom" ) +
               theme( legend.title=element_blank() ) )

# load pre calculated data and assumptions
load( 'app.RData' )
# dfw <- dfw %>% mutate( date = as.Date(date,format='%Y-%m-%d') )

# capacity assumptions
sc <- left_join(sites, sitecap, by=c('date','location','type')) 

# main dataframes
colors <- c('daily_vaccinations','cap')
cnames <- c('Doses administered','Max vaccination capacity')
dp <- dfw %>% tidyr::pivot_longer( cols = all_of(colors)
                         , names_to="s" 
                         , values_to = "value",  values_drop_na = TRUE )
dp <- dp %>% mutate( n = NA )
dp$n[dp$s %in% colors] <- cnames[match(dp$s,colors)]

# per capita values per state and Region 1 average
tmp <- lapply( c('total_vaccinations_per_hundred','people_vaccinated_per_hundred')
               , function( var ){
                   dpc <- dfw %>% select( c('date','location',var) ) %>%
                       tidyr::pivot_wider( names_from='location', values_from=var ) %>%
                       mutate( avgr1 = (.[[2]]+.[[3]]+.[[4]]+ .[[5]]+ .[[6]]+ .[[7]]) /6 ) %>%
                       tidyr::pivot_longer( cols=all_of(NEstates), names_to="location" 
                                            , values_to = "value",  values_drop_na=FALSE ) %>%
                       tidyr::pivot_longer( cols=c(value,avgr1), names_to="type" 
                                            , values_to=var, values_drop_na=FALSE ) } ) 
dpc <- bind_cols( tmp[[1]], tmp[[2]] %>% select( people_vaccinated_per_hundred ) )

# forecasted growth in daily vaccinations
dvacgr <- dfw %>% group_by( location ) %>%
                summarise( b = last(dd_vaccinations), .groups='drop_last' )

# UI
# Panel with vaccinations and capacity
panel1 <- function(){
    sidebarLayout(
        # Grey Sidebar with input controls
        sidebarPanel(
            tags$style(type = "text/css",
                       "label { font-size: 10px; }"
            ),
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
        # slider and graph for selected state
        mainPanel(
            wellPanel( fluidRow( column( 7, align="right", h5('Forecasted growth in doses administered/day:') ),
                                 column( 4, sliderInput('growth', NULL, min=0, max=1, value=0 ) # sliderTextInput('growth', NULL, choices = c(1, 10, 100, 500, 1000), grid = TRUE )
                                 ) ) ),
            plotOutput("distPlot", height = "550px")
        )
    )
}
    
ui <- fluidPage(
    # Application title
    titlePanel("New England Vaccinations"),
    if ( FEMA_version ){
        tabsetPanel(
            tabPanel('Vaccinations vs Capacity', panel1() ), 
        tabPanel('State comparison',
                 sidebarLayout(
                     sidebarPanel( tags$style(type = "text/css", "label { font-size: 13px; }" ),
                     radioButtons( 'var', 'Select the variable to display on the graph:',
                         choices = list('Total Number of Doses Administered per Hundred People' = 'total_vaccinations_per_hundred'
                                        ,'Percentage of Population Vaccinated (1+ doses)' = 'people_vaccinated_per_hundred'),
                         selected = 'people_vaccinated_per_hundred', width = NULL )
                     ),
                     mainPanel(
                         plotOutput("distPlot100k", height = "550px")
                     )
                 )
        ) # closing of tab with vaccinations per 100K
        ) # closing of tabsetPanel
    }
    else{
        panel1()
    }
)

# Define server logic required to draw a histogram
server <- function(input, output, session) {
    stateInput <- reactive({
        # This reactive function is executed every time the state changes
        scp <- sc %>% filter( location == input$state )
        
        # Default growth in daily vaccinations
        b <- dvacgr$b[dvacgr$location==input$state]
        bm <- signif( b, digits=1 )
        updateSliderInput(session, 'growth', value=round(b), min=-bm*3, max=bm*3 )
        # c <- seq(-bm, bm*3, length=5)
        # c[3] <- round(b)
        # updateSliderTextInput(session, 'growth', choices=c, selected=c[3] )
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
        # update max capacity
        sumcap <- sum( scp$cap )
        dt[dt$s=='cap','value'] <- sumcap

        # update forecasted growth in daily vaccinations
        g <- input$growth # input$growthslider
        if ( !is.null(g) ){
            a <- dt$value[dt$date==latest_history_date & dt$s=='daily_vaccinations']
            d <- cumsum( c(a, rep(g,sum(dt$date>latest_history_date & dt$s=='daily_vaccinations')) ) )
            dt[dt$date>latest_history_date & dt$s=='daily_vaccinations','value'] <- d[-1]
        }
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
    }) # closing of distPlot()
    output$distPlot100k <- renderPlot({
        if ( input$var == 'total_vaccinations_per_hundred' )
            yl <- 'Total Number of Doses Administered per Hundred People'
        else
            yl <- 'Percentage of Population Vaccinated (1+ doses)'
        ggplot( dpc, aes_string(x='date', y=input$var, color='type') ) +
            facet_wrap('~ location', nrow=2 ) +
            geom_line( size=1.5 ) +
            scale_color_manual( name=NULL, values=c('red','grey'), breaks=c('value','avgr1')
                                 , labels=c('Total in state','Region 1 average') ) +
            geom_vline(xintercept=latest_history_date, linetype="dashed", color="gray", size=1) +
            theme(axis.title.x = element_blank()) +
            scale_x_date(date_labels = '%b%e' ) +
            ylab( yl ) +
            scale_y_continuous( expand=c(0,0) ) + # label=scales::unit_format(unit="%", sep=""), 
            theme( text = element_text(size=20) )
    }) # closing of distPlot100k()
}

# Run the application 
shinyApp(ui = ui, server = server)
