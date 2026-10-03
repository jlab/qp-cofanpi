import shutil
import sys
import os
from pathlib import Path
from glob import glob
import pandas as pd
from qiita_client import ArtifactInfo
from qiita_client.util import system_call


OUT_NAME_withRNA = 'CoFAnPi +RNAseq annotated genome'
OUT_NAME_noRNA =   'CoFAnPi annotated genome'


def cofanpi(qclient, job_id, parameters, out_dir):
    COL_ORGANISM_NAME = 'organism_name'
    COL_LOCUS_TAG = 'locus_tag'
    FAKE_SNAKEMAKE = False

    has_rnaseq = 'RNAseq' in parameters.keys()
    cofanpi_modus = 'genome-only'
    out_name = OUT_NAME_noRNA
    num_total_steps = 4
    if has_rnaseq:
        num_total_steps += 1
        cofanpi_modus = 'genome-and-transcriptome'
        out_name = OUT_NAME_withRNA

    num_step = 1
    qclient.update_job_step(job_id, "Step %i of %i: Obtain organism_name and locus_tag from sample information and write into config.yaml" % (num_step, num_total_steps))

    # We first want to ensure that the user set an organism name and a locus
    # tag. These information must be stored in the study metadata with
    # according colum names. But since we here process a preparation (not a
    # study), we first need to subset the study metadata to those that occure
    # in the preparation. We thus need, as pandas.DataFrames,
    #   a) the df_study_metadata
    #   b) the df_prep_genome_metadata
    # Things furthermore complicate, as we might operate on TWO input artifacts
    # both assigned to different preparations (genome and RNAseq data.)
    # Organism name and locus tag must be derived from the preparation assigned
    # with the genome input artifact.

    # regarding a) obtain study metadata
    artifact_genome_id = parameters['reference genome']
    artifact_genome_info = qclient.get(
        "/qiita_db/artifacts/%s/" % artifact_genome_id)
    df_study_metadata = pd.DataFrame(qclient.get(
        '/qiita_db/sample_information/%s/data/' %
        artifact_genome_info['study'])['data']).T

    # regarding b) obtain genome prep metadata
    prep_genome_info = qclient.get(
        '/qiita_db/prep_template/%s/' %
        artifact_genome_info['prep_information'][0])
    df_prep_genome_metadata = pd.read_csv(
        prep_genome_info['prep-file'], sep='\t', index_col=0)

    # the metadata of interest, are those from the study metadata for samples
    # that are contained in the genome prep
    meta = df_study_metadata.loc[df_prep_genome_metadata.index, :]

    clean_vals = dict()
    for col in [COL_ORGANISM_NAME, COL_LOCUS_TAG]:
        if col not in meta.columns:
            return False, None, "Required column '%s' is NOT in your sample information." % col
        uniq_vals = meta[col].replace("", None).dropna().unique()
        if len(uniq_vals) < 1:
            return False, None, "The column '%s' in your sample information for your genome is all empty." % col
        if len(uniq_vals) > 1:
            return False, None, "You provide the following ambiguous %i values in column '%s' of your sample information for your genome.\n%s" % (len(uniq_vals), col, '\n  - '.join(map(lambda x: '"%s' % x, uniq_vals)))
        clean_vals[col] = uniq_vals[0]

    fp_config = os.path.join(out_dir, 'config.yaml')
    with open(fp_config, 'w') as f:
        f.write('organism_name: %s\n' % clean_vals[COL_ORGANISM_NAME])
        f.write('locus_tag: %s\n' % clean_vals[COL_LOCUS_TAG])

    num_step += 1
    qclient.update_job_step(job_id, "Step %i of %i: Prepare genome assembly." % (num_step, num_total_steps))
    fp_genome_src = artifact_genome_info['files']['assembly'][0]['filepath']  # 0 because there should be exactly one assembly file per "genome"
    fp_genome_trgt = os.path.join(out_dir, 'genome', os.path.basename(fp_genome_src).replace('.fna', '.fa'))  # as qiita enforces .fna but cofanpi .fa
    os.makedirs(os.path.dirname(fp_genome_trgt), exist_ok=True)
    # to save disk space, we create a softlink instead of a full copy
    Path(fp_genome_trgt).symlink_to(fp_genome_src)

    if has_rnaseq:
        num_step += 1
        qclient.update_job_step(job_id, "Step %i of %i: Prepare RNAseq data." % (num_step, num_total_steps))

        artifact_rnaseq_id = parameters['RNAseq']
        artifact_rnaseq_info = qclient.get(
            "/qiita_db/artifacts/%s/" % artifact_rnaseq_id)
        os.makedirs(os.path.join(out_dir, 'rna_seq'), exist_ok=True)
        if 'raw_reverse_seqs' not in artifact_rnaseq_info['files'].keys():
            return False, None, "Expect paired end sequences, but your input artifact '%s' lacks raw_reverse_seqs!" % artifact_rnaseq_info['name']
        for direction in ['raw_forward_seqs', 'raw_reverse_seqs']:
            for fileobj in artifact_rnaseq_info['files'][direction]:
                fp_rna_trgt = os.path.join(out_dir, 'rna_seq', os.path.basename(fileobj['filepath']).replace('.fastq.gz', '.fq.gz'))  # as qiita enforces .fastq.gz but cofanpi .fq.gz
                Path(fp_rna_trgt).symlink_to(fileobj['filepath'])

    num_step += 1
    qclient.update_job_step(job_id, "Step %i of %i: Executing the CoFAnPi pipeline." % (num_step, num_total_steps))
    # very specific for the cofanpi docker image
    workdir = Path('/fun/data')
    if workdir.is_symlink() or workdir.exists():
        workdir.unlink()
    workdir.symlink_to(out_dir)
    num_cpus = os.cpu_count()

    # link to a pre-built .snakemake/conda directory to avoid building of conda envs at every plugin start
    link_conda = Path('/fun/data/%s/.snakemake/conda' % os.path.dirname(workdir))
    os.makedirs(os.path.dirname(link_conda), exist_ok=True)
    if link_conda.is_symlink() or link_conda.exists():
        link_conda.unlink()
    link_conda.symlink_to('/databases/conda')

    if not FAKE_SNAKEMAKE:
        cmd = 'HOST_UID=%s bash /fun/cofanpi.sh -c %i -i %s' % (os.path.dirname(out_dir), num_cpus, cofanpi_modus)
    else:
        fp_fake_res = os.path.join(out_dir, 'results')
        cmd = []
        #cmd = 'mkdir -p %s' % os.path.dirname(fp_fake_res)
        cmd.append('cp -r /databases/Stability_test/results %s' % fp_fake_res)
        cmd.append('ln -s /databases/Stability_test/11763 %s' % os.path.join(out_dir, os.path.basename(out_dir)))
        cmd = ' && '.join(cmd)

    with open('/debug.log', 'a') as L:
        print("cmd=", cmd, os.path.dirname(workdir), num_cpus, cofanpi_modus, file=L)
    std_out, std_err, return_value = system_call(cmd)
    if return_value != 0:
        error_msg = ("Error running CoFAnPi pipeline:\nStd out: %s\nStd err: %s"
                        % (std_out, std_err))
        return False, None, error_msg

    num_step += 1
    qclient.update_job_step(job_id, "Step %i of %i: Collecting result files" % (num_step, num_total_steps))

    # to be compatible to file endings that can be uploaded to qiita, we want to rename *.fa into *.fna
    fp_res_assembly = glob(os.path.join(out_dir, 'results', '080_annotate', 'annotate_results', '*.scaffolds.fa'))[0]
    fp_res_assembly_fna = fp_res_assembly
    if not FAKE_SNAKEMAKE:
        fp_res_assembly_fna = os.path.join(os.path.dirname(fp_res_assembly), os.path.basename(fp_res_assembly)[:-3] + '.fna')
        shutil.copy(fp_res_assembly, fp_res_assembly_fna)
    fp_annotation = glob(os.path.join(out_dir, 'results', '080_annotate', 'annotate_results', '*.gff3'))[0]

    # FOR NOW, iterate through multiple log-like files and dump everything into one lengthy file
    fp_log = os.path.join(out_dir, 'cofanpi.log')
    with open(fp_log, 'w') as lf:
        for src_file in list(sorted(glob(os.path.join(out_dir, 'results', 'logs', '*.log')))) + \
                        list(sorted(glob(os.path.join(out_dir, 'results', 'benchmarks', '*.txt')))) + \
                        list(sorted(glob(os.path.join(out_dir, 'results', '080_annotate', 'annotation_results', 'Gene2Products.*.txt')))) + \
                        list(sorted(glob(os.path.join(out_dir, 'results', '080_annotate', 'annotation_results', '*.stats.json')))) + \
                        list(sorted(glob(os.path.join('/fun/data', os.path.dirname(workdir), '*.log')))) + \
                        list(sorted(glob(os.path.join('/fun/data', os.path.dirname(workdir), '*.fixedproducts')))):
            lf.write('---- start file "%s" ----\n' % os.path.abspath(src_file))
            with open(src_file, 'r') as f:
                for line in f.readlines():
                    lf.write(line)
            lf.write('==== end   file "%s" ====\n\n\n' % os.path.abspath(src_file))

    output_artifacts = [ArtifactInfo(out_name, 'genome', [
        (fp_res_assembly_fna, 'assembly'),
        (fp_annotation, 'annotation'),
        (fp_log, 'log'),
    ])]

    return True, output_artifacts, ""
