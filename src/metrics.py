"""
Metrics Class

Implements computation of evaluation metrics for assessing the similarity and accuracy 
of predictions relative to ground truth data.
"""

import pandas as pd

class Metrics():

    """
    Compute metrics quantifying similarity between predicted and ground truth data.
    
    Methods
    -------
    get_error_matrix:
        Computes error matrix (confusion matrix) between reference and predicted images.
    get_normalised_error_matrix:
        Normalizes error matrix to give per-class accuracy in the range [0, 1].
    """

    @staticmethod
    def get_error_matrix( reference, prediction, **kwargs ):

        """
        Compute error matrix by extracting sample data from predicted and reference images
        
        Parameters        
        ----------
        reference : ee.Image
            reference image
        prediction : ee.Image
            predicted image

        Returns
        -------
        dict :
            Matrix cross-referencing label sample sizes between reference and predicted images
        """

        # parse keyword args
        roi = kwargs.get( 'region')
        seed = kwargs.get( 'seed', 42 )
        scale = kwargs.get( 'scale', 10 )
        npoints = kwargs.get( 'npoints', 2000 )

        # collect evenly distributed per-pixel samples of reference vs prediction
        samples = reference.rename('reference') \
                    .addBands( prediction.rename('prediction') ) \
                    .stratifiedSample(
                        numPoints=npoints,
                        classBand='reference',
                        region=roi,
                        scale=scale,
                        seed=seed,
                        geometries=False
                )

        # convert samples into error matrix
        matrix = samples.errorMatrix( 'reference', 'prediction' )
        return matrix.getInfo(), matrix.accuracy().getInfo()


    @staticmethod
    def get_normalised_error_matrix( em, labels ):

        """
        Compute normalised error matrix where entries range from 0 to 1
        
        Parameters        
        ----------
        em : dataframe
            raw error matrix

        Returns
        -------
        dataframe :
            normalised error matrix
        """

        # convert array to dataframe with legend names
        df = pd.DataFrame(em, index=labels, columns=labels)

        # normalize by row for per-class accuracy
        return df.div(df.sum(axis=1), axis=0)
