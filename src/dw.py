"""
Dynamic World Class

Implements helper functions for processing and reducing Earth Engine 
Dynamic World image collections into derived land cover products. Includes 
functionality to compute temporally aggregated land cover products using 
either the mode of top-1 labels or the argmax of per-class median probabilities, 
along with associated confidence scores.
"""

import ee

# pylint: disable=no-member

from base import BaseCollector

class DynamicWorld( BaseCollector ):

    """
    Manage creation of Earth Engine based collection of Dynamic World
    images collocated with arbitrary spatial and temporal limits.
    
    Methods
    -------
    get_data:
        Entry function managing creation of earth engine Dynamic World image collection
    get_mode_label:
        Convert 16-bit DN values into surface reflectance
    get_mode_confidence:
    get_max_median_label:
    get_max_median_confidence:
    """

    # names of class probability bands
    probability_bands = [ 'water',
                           'trees',
                           'grass',
                           'flooded_vegetation',
                           'crops',
                           'shrub_and_scrub',
                           'built',
                           'bare',
                           'snow_and_ice'
    ]

    # standard legend
    legend = { 'water'   : '#419BDF',
               'trees'   : '#397D49', 
               'grass'   : '#88B053', 
               'flooded' : '#7A87C6', 
               'crops'   : '#E49635', 
               'shrubs'  : '#DFC35A', 
               'built'   : '#C4281B', 
               'bare' : '#A59B8F', 
               'snow' : '#B39FE1'
    }

    # names to reducer object lookup table
    reducer_lut = {  'mean' : ee.Reducer.mean, \
                    'median' : ee.Reducer.median, \
                    'mode' :  ee.Reducer.mode, \
                    'max' : ee.Reducer.max, \
                    'min' : ee.Reducer.min \
    }

    @staticmethod
    def get_data( roi, start_date, end_date ):

        """
        Get collection of DynamicWorld images collocated with arbitrary region 
        of interest and timeframe defined as input arguments.

        Parameters
        ----------
        roi : ee.Polygon / ee.Rectangle
            Earth Engine Geometry object defining region of interest 
        start_date : str
            Filter start date string encoded as YYYY-MM-DD
        end_date : str
            Filter end date string encoded as YYYY-MM-DD

        Returns
        -------
        ee.ImageCollection : 
            Filtered collection of Dynamic World images
        """

        # get dynamic world collection based on spatial and temporal limits
        return ee.ImageCollection( 'GOOGLE/DYNAMICWORLD/V1' ) \
                                .filterBounds(roi) \
                                .filterDate(start_date, end_date)


    @staticmethod
    def get_mode_label( collection ):

        """
        Compute temporal mode (most frequent) label and confidence over a collection

        Parameters
        ----------
        collection : ee.ImageCollection
            Dynamic World collection containing 'label' band.

        Returns
        -------
        ee.Image :
            Image with label and confidence bands
        """

        # compute most frequent top-1 label across time series
        label = collection.select( 'label' ) \
                    .reduce( ee.Reducer.mode() ).rename( 'label' )

        # use normalised count as confidence score
        return label.addBands(
            DynamicWorld.get_mode_confidence( collection, 'label', label )
        )

    @staticmethod
    def get_mode_confidence( collection, band, target ):

        """
        Compute normalized frequency (confidence) of target value in a collection

        Parameters
        ----------
        collection : ee.ImageCollection
            Collection of images containing the specified band
        band : str
            Name of the band to compare
        target : ee.Image
            Image containing target values to match

        Returns
        -------
        ee.Image
            Percentage of valid observations matching mode label (0-100)
        """

        # create binary images where value equals target image
        def get_match( image ) :
            match = image.select( band ).eq( target )
            return match.updateMask( image.select( band ).mask() )

        # get sum of matches per pixel
        matches = collection.map( get_match ) \
                        .reduce( ee.Reducer.sum() )

        # get count of valid observations per pixel
        def get_nodata_mask( image ):
            return image.select( band ).mask()

        max_obs_count = collection.map( get_nodata_mask ) \
                                .reduce( ee.Reducer.sum() )

        # return match count by valid observation count
        return matches.divide( max_obs_count ) \
                    .multiply( 100 ).toInt() \
                    .rename('confidence')


    @staticmethod
    def get_max_median_label( collection ):

        """
        Compute land cover label based on the class with the highest median probability

        Parameters
        ----------
        collection : ee.ImageCollection
            Dynamic World image collection with probability bands

        Returns
        -------
        ee.Image :
            Image with label and confidence bands
        """

        # compute per-pixel median probability values
        median = collection.select( DynamicWorld.probability_bands ).median()

        # extract index of highest median probability - use to identify label 
        label = median.toArray() \
                .arrayArgmax() \
                .arrayGet([0] ).rename( 'label' )

        # use maximum median probability as confidence
        return label.addBands(
            DynamicWorld.get_max_median_confidence( median.toArray() )
        )


    @staticmethod
    def get_max_median_confidence( median_arr ):

        """
        Compute per-pixel maximum median probability as confidence score

        Parameters
        ----------
        median_arr : ee.Array
            1D array comprising 9 class probability values 

        Returns
        -------
        ee.Image
            Median probability rescaled to integer percentage 
        """

        return ( median_arr.arrayReduce(ee.Reducer.max(), [0] ) \
                    .arrayGet([0]) \
                    .multiply( 100 ).toInt() \
                    .rename('confidence')
        )
