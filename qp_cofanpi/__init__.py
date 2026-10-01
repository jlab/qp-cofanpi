from qiita_client import QiitaPlugin, QiitaCommand
from .cofanpi import cofanpi, OUT_NAME_withRNA, OUT_NAME_noRNA
import os


# Initialize the plugin
plugin = QiitaPlugin(
    name='qp-cofanpi',
    version='2026-10-01',
    description='CoFAnPi fungal genome annotation pipeline')

# Defining the command
req_params = {
    # cofanpi takes a genome assembly as input to compute annotations
    'reference genome': ('artifact', ['genome']),
    'RNAseq': ('artifact', ['per_sample_FASTQ'], None),
}
db_antismash_version = os.environ.get('QP_COFANPI_DBVERSION_ANTISMASH', 'unknown')
db_card_version = os.environ.get('QP_COFANPI_DBVERSION_CARD', 'unknown')
db_eggnog_version = os.environ.get('QP_COFANPI_DBVERSION_EGGNOG', 'unknown')
db_interproscan_version = os.environ.get('QP_COFANPI_DBVERSION_IPRSCAN', 'unknown')
opt_params = {
    'EggNOG database': ['choice:["%s", "very old"]' % db_eggnog_version, db_eggnog_version],  # not sure about version and time stamp!
    'InterProScan database': ['choice:["%s", "super old"]' % db_interproscan_version, db_interproscan_version],  # also not sure about the time stamp
    'antiSMASH database': ['choice:["%s", "better not use"]' % db_antismash_version, db_antismash_version],
    'CARD database': ['choice:["%s"]' % db_card_version, db_card_version],
    # when command is for processing, defaults cannot be changed
}
outputs = {OUT_NAME_withRNA: 'genome'}

# defining default parameter set AKA what's going to be shown to the user
# as options for the command
dflt_param_set = {
    'data from 2026-09-30': {
        'EggNOG database': db_eggnog_version,
        'InterProScan database': db_interproscan_version,
        'antiSMASH database': db_antismash_version,
        'CARD database': db_card_version,
    },
    # '2020-01-01': {
    #     'EggNOG database': 'very old',
    #     'InterProScan database': 'super old',
    #     'antiSMASH database': 'better not use',
    #     'CARD database': db_card_version,
    # }
}

cofanpi_cmd = QiitaCommand(
    'CoFAnPi v2026.10.01 (with RNAseq)',
    "annotating fungal genomes",
    cofanpi,
    req_params,
    opt_params,
    outputs,
    dflt_param_set)
plugin.register_command(cofanpi_cmd)

req_params_norna = req_params.copy()
del req_params_norna['RNAseq']
cofanpi_cmd = QiitaCommand(
    'CoFAnPi v2026.10.01 (no RNAseq)',
    "annotating fungal genomes",
    cofanpi,
    req_params_norna,
    opt_params,
    {OUT_NAME_noRNA: 'genome'},
    dflt_param_set)
plugin.register_command(cofanpi_cmd)
