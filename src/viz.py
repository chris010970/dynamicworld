"""
Viz Class

Implements visualization utilities for evaluating time-series land cover data
from the Dynamic World dataset.
"""

from io import BytesIO
import requests

import numpy as np
import scipy.stats as stats
import matplotlib.pyplot as plt

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

            for k,v in dataset.items():

                if isinstance( v, ee.Image ):

                    # display mode landcover
                    m.addLayer( v.select( 'label' ),
                            { 'min' : 0, 'max' : 8, 'palette' : colors },
                                f'{k}: { dataset[ "name" ] }',
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
    def get_annotated_animation(collection, out_pathname=None, **kwargs):

        """
        Create annotated animated GIF from an Earth Engine ImageCollection. Generates an 
        animation from a time-series of images by visualizing land cover labels using a 
        fixed color palette. Each frame is annotated with the corresponding date. Optionally, 
        save output to a file.
        
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
        crs = kwargs.get('crs', 'EPSG:3857')
        dimensions = kwargs.get('dimensions', 512)
        fps = kwargs.get('fps', 2)
        roi = kwargs.get('region', collection.first().geometry())
        annotation = kwargs.get('annotation', list())

        # inline map function to generate rgb images
        def visualise_rgb(image):
            return image.visualize(
                min=0,
                max=8,
                palette=list(DynamicWorld.legend.values())
            ).set({'system:time_start': image.get('system:time_start')})

        # get rgb images
        images = collection.map(visualise_rgb).toList(collection.size())
        frames = []

        # iterate over image frames
        for idx in range(images.size().getInfo()):

            # get image
            image = ee.Image(images.get(idx))

            # get annotation label
            if len(annotation) == images.size().getInfo():
                label = annotation[idx]
            else:
                label = ee.Date(image.get('system:time_start')).format('YYYY-MM-dd').getInfo()

            # get thumbnail url
            url = image.getThumbURL({
                'region': roi,
                'dimensions': dimensions,
                'crs': crs
            })

            # retrieve byte image via url
            response = requests.get(url, timeout=100)
            byte_image = Image.open(BytesIO(response.content)).convert('RGB')

            # annotate image frame with date label and background
            draw = ImageDraw.Draw(byte_image)
            font = ImageFont.load_default()

            # calculate text size and position using textbbox
            bbox = draw.textbbox((0, 0), label, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]

            text_x = (byte_image.width - text_width) // 2
            text_y = byte_image.height - text_height - 10

            # draw background rectangle
            padding = 4
            draw.rectangle(
                [
                    text_x - padding,
                    text_y - padding,
                    text_x + text_width + padding,
                    text_y + text_height + padding
                ],
                fill='white'
            )

            # draw text
            draw.text((text_x, text_y), label, font=font, fill='black')

            # append frame
            frames.append(byte_image)

        # output filename defined
        if out_pathname:
            frames[0].save(
                out_pathname,
                save_all=True,
                append_images=frames[1:],
                duration=int(1000 / fps),
                loop=0
            )
            print(f'GIF saved to {out_pathname}')
            return out_pathname
        else:
            buffer = BytesIO()
            frames[0].save(
                buffer,
                format='GIF',
                save_all=True,
                append_images=frames[1:],
                duration=int(1000 / fps),
                loop=0
            )
            buffer.seek(0)
            return IPyImage(data=buffer.read())


    @staticmethod
    def plot_class_confidence_pdf( df, targets ):

        """
        Plot pdfs of mode and max median confidence scores
        
        Parameters
        ----------
        df : DataFrame
            dataframe encoding class-indexed confidence scores
        targets : list
            list of classes        
        """

        # create subplot figure
        _, axes = plt.subplots( figsize=(16,6),
                                ncols=2,
                                nrows=1 )
        axes = np.ravel( axes )

        # iterate over predictors
        for axis_idx, method in enumerate( [ 'mode', 'max_median' ] ):

            subset = df[ df.method == method ]
            limits = []

            # iterate over land cover classes
            for label_idx, (k, v) in enumerate( list( DynamicWorld.legend.items() ) ):

                if k in targets:

                    # extract land cover samples
                    data = subset[ subset.label == label_idx ][ 'confidence' ].values
                    if len( data ) > 0:

                        # compute mean and std
                        mean = np.mean( data )
                        std = np.std( data )

                        # get min and max limits
                        limits.append( ( mean - std * 2.5, mean + std * 2.5 ) )
                        x = np.linspace( limits[-1][0], limits[-1][1], num=100 )

                        # plot best fit gausssian function
                        density = stats.gaussian_kde( data )
                        axes[ axis_idx ].plot( x, density(x), color=v, label=k )

            # update title and legend
            axes[ axis_idx ].set_title( f'{method} : confidence scores' )
            axes[ axis_idx ].set_ylabel( 'probability' )
            axes[ axis_idx ].set_xlabel( 'frequency' )
            axes[ axis_idx ].legend()

            # tweak x-axis limits
            axes[ axis_idx ].set_xlim( np.percentile( np.array( limits )[ :, 0 ], 70 ),
                                    np.percentile( np.array( limits )[ :, 1 ], 70 ) )

        return axes
