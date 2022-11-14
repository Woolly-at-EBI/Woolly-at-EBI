"""Script to investigate the paths between library_* in ENA

___author___ = "woollard@ebi.ac.uk"
___start_date___ = "2022-11-9"
__docformat___ = 'reStructuredText'
   
"""

import getopt
import re
import subprocess
import sys
from os.path import dirname, join

import matplotlib
import matplotlib.colors
import matplotlib.pylab as plt
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from icecream import ic




def historicalPlot(df,category):
    ic(df.head(3))
    
    df['monthyear'] = pd.to_datetime(df['first_public']).dt.to_period('M')
    df['year'] = pd.to_datetime(df['first_public']).dt.to_period('Y')

    orig_df = df
    imageExt = '.pdf'

    df = df[['year',category]]
    df_grouped = df.groupby(['year',category], as_index=False).size()
    df_grouped['count'] = df_grouped['size']
    ic(type(df_grouped))
    df_grouped['year'] = df_grouped['year'].values.astype('datetime64[Y]')
    ic(df_grouped.dtypes)

    #df_grouped['year'] = pd.to_timestamp(df_grouped['year'],format='%y')
    ic(df_grouped)
     
    title = 'Sequence experiments made public, focus:' + category
    #fig = px.line(df, x='year', y="library_source")
    fig = px.histogram(df_grouped, x="year", y='count' , color=category )
    fig.update_layout({"title": title,
                    "xaxis": {"title":"Year"},
                    "yaxis": {"title":"Total experiments made public in this year"}})
    fig.show()
    imageName = 'images/' + category + '_hist'  + imageExt
    fig.write_image(imageName)
  
    fig = px.line(df_grouped, x="year", y='count' , color=category )
    fig.update_layout({"title": title,
                    "xaxis": {"title":"Year"},
                    "yaxis": {"title":"Total experiments made public in this year"}})
    imageName = 'images/' + category + '_line' + imageExt
    fig.write_image(imageName)
    #fig.show()


def simplePlots(df):
    matplotlib.rc('xtick', labelsize=4) 
    spacing = 0.200
    crosstab_selection_source = pd.crosstab(index=df['library_selection'],columns=df['library_source'])
    ic(crosstab_selection_source.head())
    crosstab_selection_source.plot.bar()
    plt.subplots_adjust(bottom=spacing)
    plt.xticks(rotation=60)
    plt.show()

    crosstab_selection_strategy = pd.crosstab(index=df['library_selection'],columns=df['library_strategy'])
    ic(crosstab_selection_strategy.head())
    crosstab_selection_strategy.plot.bar()
    plt.subplots_adjust(bottom=spacing)
    plt.xticks(rotation=60)
    plt.show()

def getCounts(df,cols):
    count_df = df.drop(['experiment_accession'],axis=1)
    #ic(count_df.head())
    #count_df = count_df.groupby(["library_selection","library_source","library_strategy"]).size().reset_index(name='count')
    count_df = count_df.groupby(cols).size().reset_index(name='count')

    #ic(count_df.head())
    return(count_df)

def sankeyPlots(df,cols,minCount,width,height):
    ic()
    count_df = getCounts(df,cols)
    ic(count_df.head())



    # Step 2. Specify a column for the flow volume value
    value = "count"
    value_suffix = ""  # Specify (if any) a suffix for the value

    # Step 3. Set the plot's title
    title = "Frequency in ENA of these combinations: " + ', '.join(cols) + ' minCount=' + str(minCount)
    ic(title)

    compactTitle = 'FrequencyFlow:_' + ','.join(cols)

    # Step 4. (Optional) Customize layout, font, and colors
    #width, height = 1000, 1250  # Set plot's width and height
    #width, height = 1000, 500  # Set plot's width and height
    fontsize = 8  # Set font size of labels
    fontfamily = "Helvetica"  # Set font family of plot's text
    bgcolor = "SeaShell"  # Set the plot's background color (use color name or hex code)
    link_opacity = 0.3  # Set a value from 0 to 1: the lower, the more transparent the links
    node_colors = px.colors.qualitative.G10  # Define a list of hex color codes for nodes

    # ---------------------------------------#
    # Code to create Sankey diagram begins!  #
    # ---------------------------------------#

    s = []  # This will hold the source nodes
    t = []  # This will hold the target nodes
    v = []  # This will hold the flow volumes between the source and target nodes
    labels = np.unique(count_df[cols].values)  # Collect all the node labels

    # Get all the links between two nodes in the data and their corresponding values
    for c in range(len(cols) - 1):
        s.extend(count_df[cols[c]].tolist())
        t.extend(count_df[cols[c + 1]].tolist())
        v.extend(count_df[value].tolist())
    links = pd.DataFrame({"source": s, "target": t, "value": v})  
    links = links.groupby(["source", "target"], as_index=False).agg({"value": "sum"})
    #focusing on the higher counts 
    links = links.drop(links[links.value <= minCount].index)
    ic(links.head())

    # Convert list of colors to RGB format to override default gray link colors
    colors = [matplotlib.colors.to_rgb(i) for i in node_colors]  

    # Create objects to hold node/label and link colors
    label_colors, links["link_c"] = [], 0

    # Loop through all the labels to specify color and to use label indices
    c, max_colors = 0, len(colors)  # To loop through the colors array
    for l in range(len(labels)):
        label_colors.append(colors[c])
        link_color = colors[c] + (link_opacity,)  # Make link more transparent than the node
        links.loc[links.source == labels[l], ["link_c"]] = "rgba" + str(link_color)
        links = links.replace({labels[l]: l})  # Replace node labels with the label's index
        if c == max_colors - 1:
            c = 0
        else:
            c += 1

    # Convert colors into RGB string format for Plotly
    label_colors = ["rgb" + str(i) for i in label_colors]

    # Define a Plotly Sankey diagram
    fig = go.Figure( 
        data=[
            go.Sankey(
                valuesuffix=value_suffix,
                node=dict(label=labels, color=label_colors),
                link=dict(
                    source=links["source"],
                    target=links["target"],
                    value=links["value"],
                    color=links["link_c"],
                ),
            )
        ]
    )

    # Customize plot based on earlier values
    fig.update_layout(
        title_text=title,
        font_size=fontsize,
        font_family=fontfamily,
        width=width,
        height=height,
        paper_bgcolor=bgcolor,
        title={"y": 0.9, "x": 0.5, "xanchor": "center", "yanchor": "top"},  # Centers title
    )

    fig.show()
    imageExt = ".pdf"
    imageName = 'images/' + compactTitle + '_sankey'  + imageExt
    fig.write_image(imageName)

def Clean_names(country):
    # Search for : 
    default = 'unspecified_country'
    if re.search('^no|Not|^undef|nega|N\. A\.|N\.A\.', country):
        return(default)
    elif re.search('^[^A-Z]',country):
        return(default)
    elif re.search('^.*[:;]', country):
  
        # Extract the position of beginning of pattern
        pos = re.search('^.*[:;]', country).start()
  
        # return the cleaned name
        return country[:pos]
    elif re.search('Japan', country):
        return('Japan')
  
    else:
        # if clean up needed return the same name

        return country
    



def processData(experiment_infile,sample_infile):
    expt_df = pd.read_csv(experiment_infile, sep='\t')
    pd.set_option('display.max_columns', 500)
    ic(expt_df.head())

    sample_df = pd.read_csv(sample_infile, sep='\t')
    ic(sample_df.head())

    df = pd.merge(expt_df, sample_df, how='inner', on='sample_accession')
    ic(df.head())
    df['library_source'] = df['library_source'].replace(r'^$', np.nan, regex=True)

    df = df.dropna(subset=['library_source'])
    #simplePlots(df) 

    width, height = 1000, 1250  # Set plot's width and height


    # Step 1. Specify >=2 categorical columns in flow order
    cols = ["library_source","library_strategy","library_selection"]
    minCount = 50
    sankeyPlots(df,cols,minCount,width, height)
    #quit()

    cols = ["instrument_model","instrument_platform"]
    minCount = 50
    #sankeyPlots(df,cols,minCount,width, height)

    cols = ["library_source","library_selection","library_strategy","instrument_model","instrument_platform"]
    cols = ["country","scientific_name","library_source","library_selection","instrument_model","instrument_platform"]
    cols = ["host_tax_id","scientific_name","library_source","library_selection","instrument_model","instrument_platform"]

    df['host_tax_id'].fillna(0, inplace=True)
    df['host_tax_id']  = df['host_tax_id'].astype(int).astype(str)

    df.loc[ df['host_tax_id'] == '0', 'host_tax_id'] = df['tax_id'].astype(int).astype(str) #using the organism tax_id, if no host_id was specified

    ic(df.head())
    ic(df['host_tax_id'].unique())

    minCount = 50
    width = 2000
    ic(df.head())
    #df["host_tax_id"].fillna("unspecified_host", inplace = True)
    sankeyPlots(df,cols,minCount,width, height)

    category = 'library_source'
    categories = ["library_source","library_selection","library_strategy"]
    for category in categories:
        historicalPlot(df,category)
        #quit()
        



def main():

#get the searchable fields
#curl 'https://www.ebi.ac.uk/ena/portal/api/searchFields?dataPortal=ena&format=json&result=read_experiment'
#https://www.ebi.ac.uk/ena/portal/api/searchFields?dataPortal=ena&format=json&result=read_experiment
# "library_selection", "library_source","library_strategy",curl -X POST "https://www.ebi.ac.uk/ena/portal/api/search" -H "accept: */*" -H "Content-Type: application/x-www-form-urlencoded" -d "dataPortal=ena&dccDataOnly=false&download=false&fields=library_selection%2C%20library_source%2C%20library_strategy%2C%20instrument_model%2C%20instrument_platform%2Chost_tax_id&format=tsv&result=read_experiment&sortDirection=asc"

#curl -X GET "https://www.ebi.ac.uk/ena/portal/api/search?dataPortal=ena&dccDataOnly=false&download=true&email=woollard%40ebi.ac.uk&fields=library_selection%2C%20library_source%2Clibrary_strategy&format=TSV&includeMetagenomes=true&result=read_experiment&sortDirection=asc" -H "accept: */*"
    #curl -X POST "https://www.ebi.ac.uk/ena/portal/api/search" -H "accept: */*" -H "Content-Type: application/x-www-form-urlencoded" -d "dataPortal=ena&dccDataOnly=false&download=false&fields=library_selection%2C%20library_source%2C%20library_strategy%2C%20instrument_model%2C%20instrument_platform&format=tsv&result=read_experiment&sortDirection=asc" > ena:libs_instrument.tsv
    infile = "ena:libs_instrument.tsv"
    #get list of sample fields
    #curl -X GET "https://www.ebi.ac.uk/ena/portal/api/returnFields?dataPortal=ena&format=tsv&result=sample" > sample_data.tsv
    sample_infile = "sample_data.tsv"
    #curl -X POST "https://www.ebi.ac.uk/ena/portal/api/search" -H "accept: */*" -H "Content-Type: application/x-www-form-urlencoded" -d "dataPortal=ena&dccDataOnly=false&download=false&fields=tax_id%2Cscientific_name%2Ctaxonomic_classification%2Csample_accession%2Ccollection_date_submitted%2Cfirst_public&format=tsv&result=sample&sortDirection=asc" > sample_data.tsv
    #curl -X POST "https://www.ebi.ac.uk/ena/portal/api/search" -H "accept: */*" -H "Content-Type: application/x-www-form-urlencoded" -d "dataPortal=ena&dccDataOnly=false&download=false&fields=library_selection%2C%20library_source%2C%20library_strategy%2C%20instrument_model%2C%20instrument_platform%2Chost_tax_id%2Cstudy_alias%2Ccountry&format=tsv&result=read_experiment&sortDirection=asc" > all_experiment.tsv
 
    experiment_infile ="all_experiment.tsv"
    ic(experiment_infile)
    ic(sample_infile)
    processData(experiment_infile,sample_infile)






if __name__ == '__main__':
    main()