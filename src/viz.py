"""
Viz Class

Implements visualization utilities for evaluating time-series land cover data
from the Dynamic World dataset.
"""

from io import BytesIO
import requests

import ee
import geemap

from PIL import Image, ImageDraw, ImageFont
from IPython.display import Image as IPyImage

from dw import DynamicWorld


class Viz():

    """
    Helper functions for visualising Dynamic World time series
    
    Methods
    -------
    plot_label_images:
        Display max-median and mode label images on an interactive map
    get_animation: 
        Create a simple animated GIF from an image collection.
    get_annotated_animation: 
        Create an annotated GIF with timestamps for each frame.
    """

    @staticmethod
    def plot_label_images( datasets, roi, zoom=10 ):

        """
        Display mode and max-median aggregated Dynamic World land cover images on
        an interactive folium map.
        
        Parameters        
        ----------
        datasets : dict
            temporally aggregated Dynamic World images

        Returns
        -------
        map :
            interactive folium map
        """

        # create folium object
        m = geemap.Map( center=roi.centroid().coordinates().getInfo()[::-1],
                        zoom=zoom,
                        add_google_map=False
        )

        # legend keys and values
        keys = list( DynamicWorld.legend.keys() )
        colors = list( DynamicWorld.legend.values() )

        # add results to interactive map
        for idx, dataset in enumerate( datasets ):

            # display mode landcover
            image = dataset[ 'mode' ]
            m.addLayer( image.select( 'label' ),
                       { 'min' : 0, 'max' : 8, 'palette' : colors },
                        f'mode: {dataset[ "start" ]}',
                        idx == 0 )

            # display max median landcover
            image = dataset[ 'max_median' ]
            m.addLayer( image.select( 'label' ),
                       { 'min' : 0, 'max' : 8, 'palette' : colors },
                       f'median: {dataset[ "start" ]}',
                       idx == 0 )

        # add legend
        m.add_legend( keys=keys, colors=colors, position='bottomleft' )

        # add layer control and centre to roi
        m.add_layer_control()
        return m


    @staticmethod
    def get_animation( collection, **kwargs ):

        """
        Create animated gif from image collection
        
        Parameters        
        ----------
        collection : ee.ImageCollection
            target image collection

        Returns
        -------
        Image :
            Animated gif
        """

        # get default args
        crs = kwargs.get( 'crs', 'EPSG:3857' )
        dimensions = kwargs.get( 'dimensions', 512 )
        fps = kwargs.get( 'framesPerSecond', 2 )
        roi = kwargs.get( 'region', collection.first().geometry() )

        # get collection of rgb images
        rgb = collection.map ( lambda image:
                            image.select( 'label' ) \
                                .visualize( min=0,
                                            max=8,
                                            palette=list( DynamicWorld.legend.values() ) )
        )
        return IPyImage(url=rgb.getVideoThumbURL( { 'crs' : crs,
                                                    'dimensions' : dimensions, 
                                                    'framesPerSecond' : fps,
                                                    'region' : roi } ) 
        )


    @staticmethod
    def get_annotated_animation( collection, out_pathname=None, **kwargs ):

        """
        Create an annotated animated GIF from an Earth Engine ImageCollection. Generates an 
        animation from a time-series of images by visualizing land cover labels using a 
        fixed color palette. Each frame is annotated with  the corresponding date. Optionally, 
        the output can be saved to a file.

        Parameters
        ----------
        collection : ee.ImageCollection
            Earth Engine ImageCollection 
        out_pathname : str, optional
            File path to save animated GIF
        **kwargs : dict, optional
            Additional keyword arguments:

        Returns
        -------
        str or IPython.display.Image
            File path to saved GIF if `out_pathname` is provided; otherwise, an 
            IPython display image for inline notebook viewing.
        """

        # get default args
        crs = kwargs.get( 'crs', 'EPSG:3857' )
        dimensions = kwargs.get( 'dimensions', 512 )
        fps = kwargs.get( 'framesPerSecond', 2 )
        roi = kwargs.get( 'region', collection.first().geometry() )

        # inline map function to generate rgb images
        def visualise_rgb( image ):
            return image.visualize(
                            min=0,
                            max=8,
                            palette=list(DynamicWorld.legend.values())
        ).set( {'system:time_start': image.get('system:time_start') } )

        # get rgb images
        images = collection.map( visualise_rgb ).toList( collection.size() )
        frames = []

        # iterate over image frames
        for idx in range( images.size().getInfo() ):

            # get image and date label
            image = ee.Image( images.get( idx ) )
            label = ee.Date(image.get('system:time_start')).format('YYYY-MM-dd').getInfo()

            # get thumbnail url
            url = image.getThumbURL({
                    'region': roi,
                    'dimensions': dimensions,
                    'crs': crs
            })

            # retrieve byte image via url
            response = requests.get(url)
            byte_image = Image.open( BytesIO(response.content)).convert( 'RGB' )

            # annotate image frame with date label
            draw = ImageDraw.Draw( byte_image )
            font = ImageFont.load_default()
            draw.text((10, byte_image.height - 20), label, font=font, fill='white' )

            frames.append( byte_image )

        # output filename defined
        if out_pathname:

            # save animation as animiated gif
            frames[0].save( out_pathname,
                            save_all=True,
                            append_images=frames[1:],
                            duration=int(1000 / fps),
                            loop=0
            )

            # return out pathname
            print(f'GIF saved to {out_pathname}')
            return out_pathname
        else:

            # encode animation as interactive image
            buffer = BytesIO()
            frames[0].save( buffer,
                            format='GIF',
                            save_all=True,
                            append_images=frames[1:],
                            duration=int(1000 / fps),
                            loop=0
            )

            # rewind and return ipython image
            buffer.seek( 0 )
            return IPyImage(data = buffer.read() )
