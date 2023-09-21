# SSEC-JHU BioSpecDB

[![CI Status](https://github.com/ssec-jhu/biospecdb/workflows/CI/badge.svg?branch=main)](https://github.com/ssec-jhu/biospecdb/actions)
[![Documentation Status](https://readthedocs.org/projects/ssec-jhu-biospecdb/badge/?version=latest)](https://ssec-jhu-biospecdb.readthedocs.io/en/latest/?badge=latest)
[![codecov](https://codecov.io/gh/ssec-jhu/biospecdb/branch/main/graph/badge.svg?token=0KPNKHRC2V)](https://codecov.io/gh/ssec-jhu/biospecdb)
[![Security Status](https://github.com/ssec-jhu/biospecdb/workflows/Security/badge.svg?branch=main)](https://github.com/ssec-jhu/biospecdb/actions)
<!---[![DOI](https://zenodo.org/badge/<insert_ID_number>.svg)](https://zenodo.org/badge/latestdoi/<insert_ID_number>) --->


![SSEC-JHU Logo](docs/_static/SSEC_logo_horiz_blue_1152x263.png)

Biosample Spectral Repository.

# Installation, Build, & Run instructions

### Conda:

For additional cmds see the [Conda cheat-sheet](https://docs.conda.io/projects/conda/en/4.6.0/_downloads/52a95608c49671267e40c689e0bc00ca/conda-cheatsheet.pdf).

 * Download and install either [miniconda](https://docs.conda.io/en/latest/miniconda.html#installing) or [anaconda](https://docs.anaconda.com/free/anaconda/install/index.html).
 * Create new environment (env) and install ``conda create -n <environment_name>``
 * Activate/switch to new env ``conda activate <environment_name>``
 * ``cd`` into repo dir.
 * Install ``python`` and ``pip`` ``conda install python=3.11 pip``
 * Install all required dependencies (assuming local dev work) ``pip install -r requirements/dev.txt``.

### Build:

  #### with Docker:
  * Download & install Docker - see [Docker install docs](https://docs.docker.com/get-docker/).
  * ``cd`` into repo dir.
  * Build image: ``docker build -t <image_name> .``

  #### with Python ecosystem:
  * ``cd`` into repo dir.
  * ``conda activate <environment_name>``
  * Build and install package in <environment_name> conda env: ``pip install .``
  * Do the same but in dev/editable mode (changes to repo will be reflected in env installation upon python kernel restart)
    _NOTE: This is the preferred installation method for dev work._
    ``pip install -e .``.
    _NOTE: If you didn't install dependencies from ``requirements/dev.txt``, you can install
    a looser constrained set of deps using: ``pip install -e .[dev]``._

### Run:

  #### with Docker:
  * Follow the above [Build with Docker instructions](#with-docker).
  * Run container from image: ``docker run -d -p 8000:8000 <image_name>``. _NOTE: ``-p 8000:8000`` is specific to the example application using port 8000._
  * Alternatively, images can be pulled from ``ghcr.io/ssec-jhu/`` e.g., ``docker pull ghcr.io/ssec-jhu/base-template:pr-1``.

  #### with Python ecosystem:
  * Follow the above [Build with Python ecosystem instructions](#with-python-ecosystem).
  * Run ``uvicorn biospecdb.asgi:application --host 0.0.0.0 --port 8000``. _NOTE: This is just an example and is obviously application dependent._


### Custom Deployment Settings:

  * ``EXPLORER_CHARTS_ENABLED``: Include the spectral data files, if present in query results, for download as zip file.
  * ``EXPLORER_DATA_EXPORTERS_ALLOW_DATA_FILE_ALIAS``: Exhaustively scan query result values for relevant filepaths to
    collect data files. Does nothing when ``EXPLORER_DATA_EXPORTERS_INCLUDE_DATA_FILES is False``.
  * ``AUTO_ANNOTATE``: Automatically run "default" annotators when new spectral data is added.
  * ``RUN_DEFAULT_ANNOTATORS_WHEN_SAVED``: Run newly added/updated annotator on all spectral data if annotator.default 
    is True. WARNING: This may be time-consuming if the annotators takes a while to run and there are a lot of spectral
    data samples in the database.


### DB Management:
We're currently using sqlite requiring the following setup instructions:

* cd into repo
* ``python manage.py migrate``
* ``python manage.py sqlmigrate uploader <migration_version>``, e.g., ``python manage.py sqlmigrate uploader 0001``
* ``python manage.py createsuperuser``
* ``python manage.py loaddata diseases instruments qcannotators``
* ``python manage.py update_sql_views``
* ``python manage.py runserver``

For running the Quality Control Annotators (QCAnnotators) use the following:

* ``python manage.py run_qc_annotators``

...using the following option ``--no_reruns`` to NOT run annotators on existing annotations, but instead leave their
existing computed values as they are. This will, however, still run all "default" annotators on all ``SepectralData``
entries that have not yet been annotated.

On subsequent deployments only ``python manage.py runserver`` is  needed, unless the db (db.sqlite) is nuked from
disk.

When the models are changed only the following migration commands are required:
* ``python manage.py makemigrations uploader``
* ``git add biospecdb/apps/uploader/migrations``
* ``git commit -asm"Update uploader model(s)"``
* ``python manage.py migrate``
* ``python manage.py sqlmigrate uploader <migration_version>``

The DB can be dumped to a file using the following:

`` python manage.py dumpdata --indent 4 uploader --exclude uploader.uploadedfile --output test_data.json``

### Usage:

## Quality Control Annotations.

Entries in the ``SpectralData`` table can be annotated by running ``QCAnnotators`` on them, thus producing a value
stored as an ``ACAnnotation`` associated with the ``SpectralData`` entry. The ``SpectralData`` table contains the actual
spectral data file containing the wavelength and intensity values. It may be desirable to annotate this data with
certain quality control metrics that can later be used to filter the data. Such quality control functions are to be
implemented as a subclass of ``Biospecdb.app.uploader.qc.qcfilter.QcFilter``.
They can then be added to the database belonging to the ``QCAnnotator``
table. Annotations of this annotators can then either be manually associated with a ``SpectralData`` entry manually via
the admin form, or by "default" if the ``QCAnnotator.default = True``. They can also be run by using the
``run_qc_annotator`` Django management command. The behavior for running these annotators and
population of the ``QCAnnotation`` table is configurable and is described below.

#### Settings:

The following QC annotator settings are available in ``biospecdb.settings``:

 * ``AUTO_ANNOTATE``: If ``True`` and if default annotators exist in the DB, they will be automatically run upon
                      adding/updating ``SpectralData`` entries. _(Default: True)_
 * ``RUN_DEFAULT_ANNOTATORS_WHEN_SAVED``: If ``True`` and ``SpectralData`` entries exist in the DB, newly added/updated
                                          default annotators will be run on all ``SpectralData`` entries.
                                          _(Default: False)_

#### Management Command:

Running ``python manage.py run_qc_annotors`` will run all existing default annotators and re-run existing annotations on
all relevant ``SpectralData`` table entries. The option ``--no_reruns`` can be used to prevent re-running existing
annotations and only run default annotators that have not yet been run.
NOTE: If ``AUTO_ANNOTATE = RUN_DEFAULT_ANNOTATORS_WHEN_SAVED = False`` using the ``run_qc_annotors`` management command
is the only mechanism for creating quality control annotations.

# Testing
_NOTE: The following steps require ``pip install -r requirements/dev.txt``._

### Linting:
Facilitates in testing typos, syntax, style, and other simple code analysis tests.
  * ``cd`` into repo dir.
  * Switch/activate correct environment: ``conda activate <environment_name>``
  * Run ``ruff .``
  * This can be automatically run (recommended for devs) every time you ``git push`` by installing the provided
    ``pre-push`` git hook available in ``./githooks``.
    Instructions are in that file - just ``cp ./githooks/pre-push .git/hooks/;chmod +x .git/hooks/pre-push``.

### Security Checks:
Facilitates in checking for security concerns using [Bandit](https://bandit.readthedocs.io/en/latest/index.html).
 * ``cd`` into repo dir.
 * ``bandit -c pyproject.toml --severity-level=medium -r biospecdb``

### Unit Tests:
Facilitates in testing core package functionality at a modular level.
  * ``cd`` into repo dir.
  * Run all available tests: ``pytest .``
  * Run specific test: ``pytest tests/test_util.py::test_base_dummy``.

### Regression tests:
Facilitates in testing whether core data results differ during development.
  * WIP

### Smoke Tests:
Facilitates in testing at the application and infrastructure level.
  * WIP

### Build Docs:
Facilitates in building, testing & viewing the docs.
 * ``cd`` into repo dir.
 * ``pip install -r requirements/docs.txt``
 * ``cd docs``
 * ``make clean``
 * ``make html``
 * To view the docs in your default browser run ``open docs/_build/html/index.html``.
