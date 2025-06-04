"""
Base Collector class

Implementing member functions and attributes shared by Collector objects
"""

import ee
import pandas as pd

# pylint: disable=no-member

class BaseCollector():

    """
    Base class implementing members and attributes shared by Collector objects
    
    Methods
    -------
    add_metadata:
        Add interval datetimes to image metadata
    get_intervals:
        Generate a list of temporal intervals
    """

    @staticmethod
    def add_metadata( image, interval ):

        """
        Add interval metadata to ee.Image object
        
        Parameters        
        ----------
        image : ee.Image
            earth engine image 
        interval : dict
            start and end dates

        Returns
        -------
        ee.Image :
            image with updated metadata
        """

        # get range of date filter
        d1 = ee.Date( interval[ 'start' ] )
        d2 = ee.Date( interval[ 'end' ] )

        # add start and end dates as metafields
        return image.set( ee.Dictionary( { 'system:time_start' : d1.millis(), \
                                    'system:time_end' : d2.millis() } ) 
        )


    @staticmethod
    def get_intervals( start, end, freq ):

        """
        Get start and end dates for periods in temporal window at nominated frequency
        
        Parameters        
        ----------
        start : string
            start date
        end : string
            end date
        frequency : string
            period frequency

        Returns
        -------
        List :
            Array of dicts with start and time datetimes
        """

        # get periods between start and end at frequency
        period = pd.period_range( start=start, end=end, freq=freq )

        # get start and end of period
        d1 = period.to_timestamp(how='start').normalize()
        d2 = period.to_timestamp(how='end').normalize()

        # convert to strings
        d1 = [ d.strftime( '%Y-%m-%d' ) for d in d1 ]
        d2 = [ d.strftime( '%Y-%m-%d' ) for d in d2 ]

        # zip up dates
        return [{ 'start': x, 'end': y } for x, y in zip( d1, d2 ) ]
