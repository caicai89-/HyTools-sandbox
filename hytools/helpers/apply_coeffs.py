import numpy as np
from ..file_io import *
import pandas as pd



def column_retype(column_name):
    """Remap wavelength column names to float"""
    try:
        new_name  = float(column_name)
    except:
        new_name = column_name
    
    return new_name

def apply_plsr(hyObj,plsr_coeffs):
    """Apply Partial Least Squares Regression (PLSR) Coefficients to image.

    This function applies a set of PLSR coefficients to an image and return
    the mean and standard deviation of the estimates.


    Parameters
    ----------
    hyObj : hyTools data object
        Data spectrum.
    plsr_coeffs :  pathname of csv containing coefficients in the following format:
        
        +---------+-----------+--------------+----------+--------------+
        |         | intercept | wavelength_1 | ........ | wavelength_n |
        +---------+-----------+--------------+----------+--------------+
        | 1       |           |              |          |              |
        | ....... |           |              |          |              |
        | n       |           |              |          |              |
        +---------+-----------+--------------+----------+--------------+
                
   Where  wavelength_n is the wavelength of the nth band in the same units as the image (ex 552.0).
        
        
    Returns
    -------
    trait_pred : numpy array (lines x columns x 2)
        Array same XY shape as input image, 
            first band: mean trait prediction
            second band: standar deviation of the trait prediction
        
    """
    
    traitModel  = pd.read_csv(plsr_coeffs,index_col=0)
    traitModel.columns = traitModel.columns.map(column_retype)
    coeffs_wavelength = [x for x in traitModel.columns if x != "intercept"]

    intercept = traitModel["intercept"].values
    coeffs = traitModel[coeffs_wavelength].values
    
    band_mask = [x in coeffs_wavelength for x in hyObj.wavelengths]
    
    # Check if all bands match in image and coeffs
    if np.sum(band_mask) != len(coeffs_wavelength):
        print("ERROR: Coefficient wavelengths and image wavelengths do not match!")
        return
    
    iterator = hyObj.iterate(by = 'chunk')

    # Empty array to hold trait estimates
    trait_arr = np.zeros((hyObj.lines,hyObj.columns,2))

    start = time.time()
    
    while not iterator.complete:
        chunk = iterator.read_next()      

        # Apply PLSR coefficients
        traitPred = np.einsum('jkl,ml->jkm',chunk[:,:,band_mask],coeffs, optimize='optimal')
        traitPred = traitPred + intercept
        
        traitPred_mean = traitPred.mean(axis=2)
        traitPred_mean[chunk[:,:,0] == hyObj.no_data] = hyObj.no_data

        traitPred_std =traitPred.std(axis=2,ddof=1)
        traitPred_std[chunk[:,:,0] == hyObj.no_data] = hyObj.no_data
        
        # Trait array indices
        line_start =iterator.current_line 
        line_end = iterator.current_line + chunk.shape[0]
        col_start = iterator.current_column
        col_end = iterator.current_column + chunk.shape[1]
        
        trait_arr[line_start:line_end,col_start:col_end,0] +=traitPred_mean
        trait_arr[line_start:line_end,col_start:col_end,1] +=traitPred_std
    
    
    return trait_pred
