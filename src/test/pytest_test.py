from decOM.modules.utils import check_nrows, find_proportions,find_max, summarize_FEAST
import pandas as pd
import numpy as np
from pandas.testing import assert_frame_equal, assert_series_equal
from decOM import data
from importlib_resources import files
import decOM.modules.utils as Utils
import mock
import unittest

resources = str(files(data))

classes=["Sediment/Soil","Skin","aOral","mOral","Unknown"]
result=pd.DataFrame.from_dict({"Sediment/Soil":[1],"Skin":[2],"aOral":[6],"mOral":[1],"Unknown":[0]})

class TestPrintError(unittest.TestCase):
    @mock.patch("decOM.modules.utils.print_error")
    def test_print_error(self,mock_print_error):
        Utils.print_error("test")
        mock_print_error.assert_called_with("test")

class TestPrintWarning(unittest.TestCase):
    @mock.patch("decOM.modules.utils.print_warning")
    def test_print_warning(self,mock_print_warning):
        Utils.print_warning("test")
        mock_print_warning.assert_called_with("test")

class TestPrintStatus(unittest.TestCase):
    @mock.patch("decOM.modules.utils.print_status")
    def test_print_status(self,mock_print_status):
        Utils.print_status("test")
        mock_print_status.assert_called_with("test")

class TestRemoveFiles(unittest.TestCase):
    @mock.patch("decOM.modules.utils.remove_files")
    def test_remove_files(self,mock_remove_files):
        Utils.remove_files("test")
        mock_remove_files.assert_called_with("test")

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