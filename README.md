# dynamicworld

There is growing demand for accurate, timely, high-resolution land cover information from multiple stakeholders to track progress toward sustainability targets and monitor Environmental, Social, and Governance (ESG) metrics related to ecosystem stability and biodiversity conservation. 

Google’s Dynamic World is a near real-time, global land cover dataset at 10m resolution. It provides unprecedented temporal granularity for land cover monitoring. Unlike traditional static maps — which are typically updated only annually and delivered with significant delay — Dynamic World is continuously refreshed as new Sentinel-2 satellite imagery becomes available.

Crucially, Dynamic World outputs not just a single land cover label per pixel, but a full probability distribution across nine classes: Water, Trees, Grass, Flooded Vegetation, Crops, Shrub & Scrub, Built, Bare Ground, and Snow & Ice. This probabilistic output — expressed as the normalised likelihood of each class — makes the dataset more ‘transparent and versatile than conventional products’, allowing users to assess classification confidence and explore land cover dynamics with far greater nuance.

This repository explores the use of Google’s Dynamic World dataset to automatically identify and classify different categories of land cover change, with a focus on a case study in the UK.

For further context, explanations and description of analysis, please refer to my [Medium space](https://medium.com/@c.r.williams0109). 
