import hashlib
import tempfile
import zipfile

from django.conf import settings
from django.core.files.storage import storages
from django.utils.module_loading import import_string
import explorer.exporters
import pandas as pd

from uploader.models import SpectralData


class ZipSpectralDataMixin:
    """ A custom mixin for explorer.exporters.BaseExporter used to collect SpectralData.data files and zip them with
        query output data for download.
    """

    @property
    def content_type(self):
        if self.is_zip:
            return "application/zip"
        else:
            return self.__class__.content_type

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.is_zip = False  # Used to dynamically correct filename and content_type. Mutated only by get_file_output.

    def get_filename(self, *args, **kwargs):
        filename = super().get_filename(*args, **kwargs)
        if self.is_zip:
            filename += ".zip"
        return filename

    def get_output(self, **kwargs):
        value = self.get_file_output(**kwargs)
        if hasattr(value, "getvalue"):
            value = value.getvalue()
        return value

    def get_file_output(self,
                        include_data_files=None,
                        return_info=False,
                        always_zip=False,
                        compression_type=None,
                        compression_level=None,
                        **kwargs):
        self.is_zip = False  # NOTE: This doesn't need resetting anywhere else.

        if include_data_files is None:
            include_data_files = settings.EXPLORER_DATA_EXPORTERS_INCLUDE_DATA_FILES

        if compression_type is None:
            compression_type = import_string(settings.ZIP_COMPRESSION)

        if compression_level is None:
            compression_level = settings.ZIP_COMPRESSION_LEVEL

        # NOTE: The following two lines are the entire contents of explorer.exporters.BaseExporter.get_file_output.
        res = self.query.execute_query_only()
        output = self._get_output(res, **kwargs)

        n_rows = len(res.data)
        spectral_data_filenames = None
        # Compute data checksum
        output.seek(0)

        # For .xlsx output is already a bytes object so doesn't need encoding.
        _output = output.read()
        if hasattr(_output, "encode"):
            _output = _output.encode()
        data_sha256 = hashlib.sha256(_output).hexdigest()

        data_files = []
        if include_data_files:
            # Collect SpectralData files and zip along with query data from self._get_output().
            if settings.EXPLORER_DATA_EXPORTERS_ALLOW_DATA_FILE_ALIAS:
                # Spectral data files are modeled by the Spectraldata.data field, however, the sql query could have
                # aliased these so it wouldn't be safe to search by column name. Instead, we can only exhaustively
                # search all entries for some marker indicating that they are spectral data files, where this "marker"
                # is the upload directory - SpectralData.data.field.upload_to.
                upload_dir = SpectralData.data.field.upload_to  # NOTE: We don't need to inc. the MEDIA_ROOT for this.
                for row in res.data:
                    for item in row:
                        if isinstance(item, str) and item.startswith(upload_dir):
                            data_files.append(item)
            else:
                if (col_name := SpectralData.data.field.name) in res.header_strings:
                    df = pd.DataFrame(res.data, columns=res.header_strings)
                    df = df[col_name]
                    # There could be multiple "col_name" (aka "data") columns so flatten first.
                    data_files = df.to_numpy().flatten().tolist()

        if data_files or always_zip:
            # Dedupe and sort.
            data_files = sorted(set(data_files))
            spectral_data_filenames = data_files

            # Zip everything together.
            temp = tempfile.TemporaryFile()
            with zipfile.ZipFile(temp,
                                 mode="w",
                                 compression=compression_type,
                                 compresslevel=compression_level) as archive:
                # Add query results to zipfile.
                archive.writestr(self.get_filename(), output.getvalue())

                # Add all data files to zipfile.
                for filename in data_files:
                    try:
                        archive.write(storages["default"].path(filename), arcname=filename)
                    except NotImplementedError:
                        # storages["default"].path() will raise NotImplementedError for remote storages like S3. In this
                        # scenario, open and read all the file contents to zip.
                        with storages["default"].open(filename) as fp:
                            data = fp.read()
                        archive.writestr(filename, data)
            temp.seek(0)
            output = temp
            self.is_zip = True

        return (output, (n_rows, data_sha256, spectral_data_filenames)) if return_info else output


class CSVExporter(ZipSpectralDataMixin, explorer.exporters.CSVExporter):
    ...


class ExcelExporter(ZipSpectralDataMixin, explorer.exporters.ExcelExporter):
    ...


class JSONExporter(ZipSpectralDataMixin, explorer.exporters.JSONExporter):
    ...
