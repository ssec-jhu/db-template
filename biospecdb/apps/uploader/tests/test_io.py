import pytest

from uploader.io import FileFormats, read_single_row_spectral_data_table
from uploader.tests.conftest import DATA_PATH


spectral_file_path = (DATA_PATH/"sample")


@pytest.mark.parametrize("ext", (FileFormats.CSV, FileFormats.XLSX))
def test_read_single_row_spectral_data_table(ext):
    filename = spectral_file_path.with_suffix(ext)
    data = read_single_row_spectral_data_table(filename)
    assert str(data.patient_id) == "4efb03c5-27cd-4b40-82d9-c602e0ef7b80"
