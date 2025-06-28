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

    # names to reducer object lookup table
    _reducer_lut = {  'mean' : ee.Reducer.mean, \
                        'median' : ee.Reducer.median, \
                        'mode' :  ee.Reducer.mode, \
                        'max' : ee.Reducer.max, \
                        'min' : ee.Reducer.min \
    }

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


    @staticmethod
    def reduce_to_intervals( collection, intervals, **kwargs ):

        """
        Reduce image collection to one or more aggregated images based on temporal interval.        
        
        Parameters
        ----------
        collection : ee.ImageCollection
            Earth Engine image collection
        intervals : list
            List of dictionaries with start and end date keys + values
        method : str
            Name of reducer method
            
        Returns
        -------
        ee.ImageCollection : 
            Image collection comprising interval aggregated images
        """

        # parse keyword args
        method = kwargs.get( 'method', 'median' )
        meta_type = kwargs.get( 'meta_type', 'aggregation_period' )
        names = kwargs.get( 'names' )

        # list to store outputs
        images = ee.List([])

        # iterate over intervals
        for interval in intervals:

            # get range of date filter
            d1 = ee.Date( interval[ 'start' ] )
            d2 = ee.Date( interval[ 'end' ] )

            try:

                # apply reduction between dates
                if d1 == d2:
                    subset = collection.filterDate(d1)
                else:
                    subset = collection.filterDate(d1, d2)

                image = subset.reduce( BaseCollector._reducer_lut[ method ] () )

                # optional rename
                if names is not None:
                    image = image.rename( names )

                # record temporal period of aggregation
                if meta_type == 'aggregation_period':

                    # add start and end dates as metafields
                    meta = ee.Dictionary( { 'system:time_start' : d1.millis(), \
                                                'system:time_end' : d2.millis() } )

                else:

                    # add interpolated date as meta property
                    d = d1.advance( d2.difference( d1, 'days' ).divide( 2 ), 'days' )
                    meta = ee.Dictionary( { 'system:time_start' : d.millis() } )

                images = images.add( image.set(  meta ) )

            except BaseException as err:

                # exception - probably caused by empty subset
                print ( err )
                continue

        # return reduced images as new image collection
        return ee.ImageCollection.fromImages( images )


    @staticmethod
    def remove_bands( collection, names ):

        """
        Remove one or more bands from image collection
        
        Parameters
        ----------
        collection : ee.ImageCollection
            Earth Engine image collection
        names : str or list
            List of band names or single string
            
        Returns
        -------
        ee.ImageCollection : 
            Image collection with bands removed
        """

        # check input arg is a list
        if not isinstance( names, list ):
            names = [ names ]

        # remove label band
        current_bands = list( collection.first().bandNames().getInfo() )
        new_bands = [ b for b in current_bands if b not in names ]

        return collection.select( new_bands )


    @staticmethod
    def add_time_delta_band( collection, baseline, units='Months' ):

        """
        Add time delta band to images in an image collection

        Parameters
        ----------
        collection : ee.ImageCollection
            Earth Engine image collection
        baseline : string
            Datetime string (2018-01-01)
            
        Returns
        -------
        ee.ImageCollection : 
            Image collection with time delta band added as metadata and band
        """

        def add_band( image ):

            delta = image.date().difference( ee.Date( baseline ), units )
            return image.set('time_delta', delta ) \
                        .addBands( ee.Image.constant( delta ) \
                        .rename('time_delta') \
                        .toFloat()

            )

        return collection.map( add_band )
