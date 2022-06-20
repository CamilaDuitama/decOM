import re
from decOM.modules.utils import check_input, check_nrows, find_proportions,find_max, summarize_FEAST
from decOM.modules.sink import create_vector
import pandas as pd
import numpy as np
from pandas.testing import assert_frame_equal, assert_series_equal
from decOM import data
from importlib_resources import files
resources = str(files(data))

classes=["Sediment/Soil","Skin","aOral","mOral","Unknown"]
result=pd.DataFrame.from_dict({"Sediment/Soil":[1],"Skin":[2],"aOral":[6],"mOral":[1],"Unknown":[0]})

def test_find_proportions():
    actual = result.apply(find_proportions,axis=1,classes=classes)
    expected = pd.DataFrame.from_dict({"Sediment/Soil":[10.0],"Skin":[20.0],"aOral":[60.0],"mOral":[10.0],"Unknown":[0.0]})
    assert_frame_equal(actual,expected)

def test_find_max():
    expected = result.apply(find_max,axis=1)
    actual = pd.Series(["aOral"])
    assert_series_equal(actual,expected)

def test_find_max_with_tie():
    result=pd.DataFrame.from_dict({"Sediment/Soil":[1],"Skin":[2],"aOral":[3],"mOral":[3],"Unknown":[1]})
    expected = result.apply(find_max,axis=1)
    actual = pd.Series(["TIE"])
    assert_series_equal(actual,expected)

def test_summarize_FEAST():
    FEAST=pd.DataFrame.from_dict({"A_Sediment/Soil":[0.1],"B_Sediment/Soil":[0.2],"C_Sediment/Soil":[0.6],"D_Sediment/Soil":[0.1],"E_Sediment/Soil":[0]})
    expected = pd.Series([np.float64(100)])
    actual = FEAST.apply(summarize_FEAST,args=("Sediment/Soil",classes),axis=1)
    assert_series_equal(expected,actual)

def test_summarize_FEAST_missing_env():
    FEAST=pd.DataFrame.from_dict({"A_Sediment/Soil":[0.1],"B_Sediment/Soil":[0.2],"C_Sediment/Soil":[0.6],"D_Sediment/Soil":[0.1],"E_Sediment/Soil":[0]})
    expected = pd.Series([np.nan])
    actual = FEAST.apply(summarize_FEAST,args=("missing_env",classes),axis=1)
    assert_series_equal(expected,actual)

def test_check_nrows():
    actual = check_nrows(resources+"/kmtricks.fof")
    expected = 360
    assert(actual == expected)
