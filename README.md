# Nepremicnine Scrapper

## Task: Get all real-estate ads for current day for Ljubljana

## Solution

### Intro
Data is scrapped from two major slovenian pages for real-estate: nepremicnine.net and bolha.com.

Algorithm uses Selenium webdriver that controls flow of processes on webpages 
and extract data from relevant ads.

Facebook group "Stanovanjce, stanovanjce, kje si" was also taken into account as source of data,
but due to Facebook's complex rules of obtaining API token for live scrapping, this was omitted.

### Challenges
Both pages have quiet different html style, so separate classes for both have been made.
Those classes inherit abstract class that contain common methods.

Nepremicnine.net have human verification enabled, which block every try to load another link
from the original URL. This was by-passed by passing the final URL, with meta-parameters
already included and by usage of only one page. However, the code for scrapping multiple pages is
present in main file.

For Bolha.net, only scrapping of one page is shown. The process for multiple pages would be same 
as for nepremicnine.net and due to the duplicity it is omitted.

### Notes
Data is as uniform as possible. For this purpose, some text post-processing was necessary.
I.e. On nepremicnine.net renting is classified by word "Oddaja" and on Bolha it is "Oddam".
This was uniformed so that the final table contains only one version of the text.

Attributes shown in final table represent the most important attributes of the ads.
Adding new attributes is pretty straight-forward.

Median and mean of the prices of the ads are shown at the end.

### Next steps
Calculation of attribute correlation would be a good thing to do.

For concrete usage in ML, it would be smart to convert string-like values (i.e. "Novo") to
one-hot encoded vectors. Prices and sizes could be discretized.

Separation to multiple .py files or even Jupyter Notebook files would be good next step.