from qiita_client import QiitaPlugin, QiitaCommand
from .cofanpi import cofanpi

# Initialize the plugin
plugin = QiitaPlugin(name='qp-cofanpi', version='2026-09-25', description='CoFAnPi fungal genome annotation pipeline')

# Defining the Sortmerna command
req_params = {'input': ('artifact', ['per_sample_FASTQ'])}
opt_params = {}
outputs = {'Non-ribosomal reads': 'per_sample_FASTQ',
           'Ribosomal reads': 'per_sample_FASTQ'}

# defining default parameter set AKA what's going to be shown to the user
# as options for the command
dflt_param_set = {
    'Ribosomal read filtering': {}
}

cofanpi_cmd = QiitaCommand(
    'CoFAnPi v2026.09.18', "annotating fungal genomes", cofanpi,
    req_params, opt_params, outputs, dflt_param_set)

plugin.register_command(cofanpi_cmd)
