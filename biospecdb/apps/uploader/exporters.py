from pathlib import Path
import tempfile
import zipfile

from django.conf import settings
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

    def get_file_output(self, **kwargs):
        self.is_zip = False  # NOTE: This doesn't need resetting anywhere else.

        # NOTE: The following two lines are the entire contents of explorer.exporters.BaseExporter.get_file_output.
        res = self.query.execute_query_only()
        output = self._get_output(res, **kwargs)

        if not settings.EXPLORER_DATA_EXPORTERS_INCLUDE_DATA_FILES:
            return output

        data_files = []
        # Collect SpectralData files and zip along with query data from self._get_output().
        if settings.EXPLORER_DATA_EXPORTERS_ALLOW_DATA_FILE_ALIAS:
            # Spectral data files are modeled by the Spectraldata.data field, however, the sql query could have aliased
            # these so it wouldn't be safe to search by column name. Instead, we can only exhaustively search all
            # entries for some marker indicating that they are spectral data files, where this "marker" is the upload
            # directory - SpectralData.data.field.upload_to.

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

        if data_files:
            # Dedupe
            data_files = set(data_files)

            # Zip everything together.
            temp = tempfile.TemporaryFile()
            with zipfile.ZipFile(temp, mode="w") as archive:
                # Add query results to zipfile.
                archive.writestr(self.get_filename(), output.getvalue())

                # Add all data files to zipfile.
                for filename in data_files:
                    archive.write(Path(filename))
            temp.seek(0)
            output = temp
            self.is_zip = True

        return output


class CSVExporter(ZipSpectralDataMixin, explorer.exporters.CSVExporter):
    ...


class ExcelExporter(ZipSpectralDataMixin, explorer.exporters.ExcelExporter):
    ...


class JSONExporter(ZipSpectralDataMixin, explorer.exporters.JSONExporter):
    ...
