import sys
import argparse

import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

from megalodon import megalodon_helper as mh


HEATMAP_BINS = 25


def get_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--sample1-bed-methyl-files', nargs='+',
        help='Bed methyl files from first set of sample(s).')
    parser.add_argument(
        '--sample2-bed-methyl-files', nargs='+',
        help='Bed methyl files from second set of sample(s).')
    parser.add_argument(
        '--valid-positions', action='append',
        help='BED file containing positions to be considered. Multiple ' +
        'files may be provided')
    parser.add_argument(
        '--coverage-threshold', type=int, default=1,
        help='Only include sites with sufficient coverage. ' +
        'Default: 1 (= All sites)')
    parser.add_argument(
        '--strand-offset', type=int,
        help='Offset to combine stranded results. Positive value indicates ' +
        'reverse strand sites have higher position values. Default treat ' +
        'strands independently.')
    parser.add_argument(
        '--out-pdf', default='megalodon_mod_comaparison.pdf',
        help='Output pdf filename. Default: %(default)s')
    parser.add_argument(
        '--out-filename',
        help='Output filename for text summary. Default: stdout')

    return parser


def main():
    args = get_parser().parse_args()
    pdf_fp = PdfPages(args.out_pdf)
    out_fp = (sys.stdout if args.out_filename is None else
              open(args.out_filename, 'w'))

    # parse bed methyl files
    samp1_cov, samp1_mod_cov = mh.parse_bed_methyls(
        args.sample1_bed_methyl_files, strand_offset=args.strand_offset)
    samp1_all_cov = np.array([cov for ctg_cov in samp1_cov.values()
                              for cov in ctg_cov.values()])
    samp2_cov, samp2_mod_cov = mh.parse_bed_methyls(
        args.sample2_bed_methyl_files, strand_offset=args.strand_offset)
    samp2_all_cov = np.array([cov for ctg_cov in samp2_cov.values()
                              for cov in ctg_cov.values()])
    out_fp.write('Sample 1 coverage median: {:.2f}   mean: {:.2f}\n'.format(
        np.median(samp1_all_cov), np.mean(samp1_all_cov)))
    out_fp.write('Sample 2 coverage median: {:.2f}   mean: {:.2f}\n'.format(
        np.median(samp2_all_cov), np.mean(samp2_all_cov)))

    # parse valid positions
    valid_pos = None
    if args.valid_positions is not None:
        valid_pos = mh.parse_beds(
            args.valid_positions, ignore_strand=args.strand_offset is not None)

    # compute methylation percentages
    samp1_meth_pct, samp2_meth_pct = [], []
    for ctg in set(samp1_cov).intersection(samp2_cov):
        if valid_pos is not None and ctg not in valid_pos:
            continue
        valid_ctg_pos = valid_pos[ctg]
        for pos in set(samp1_cov[ctg]).intersection(samp1_cov[ctg]):
            if valid_pos is not None and pos not in valid_ctg_pos:
                continue
            samp1_pos_cov = samp1_cov[ctg][pos]
            samp2_pos_cov = samp2_cov[ctg][pos]
            if min(samp1_pos_cov, samp2_pos_cov) < args.coverage_threshold:
                continue
            samp1_meth_pct.append(
                100 * samp1_mod_cov[ctg][pos] / samp1_pos_cov)
            samp2_meth_pct.append(
                100 * samp2_mod_cov[ctg][pos] / samp2_pos_cov)
    samp1_meth_pct = np.array(samp1_meth_pct)
    samp2_meth_pct = np.array(samp2_meth_pct)
    out_fp.write('{} sites detected\n'.format(samp1_meth_pct.shape[0]))
    corrcoef = np.corrcoef(samp1_meth_pct, samp2_meth_pct)
    out_fp.write('Correlation coefficient: {:.4f}\n'.format(corrcoef))
    out_fp.write('R^2: {:.4f}\n'.format(corrcoef**2))

    hist_data = np.histogram2d(
        samp1_meth_pct, samp2_meth_pct, bins=HEATMAP_BINS,
        range=[[0, 100], [0, 100]])
    plt.figure(figsize=(8, 7))
    sns.heatmap(hist_data, cmap='YlGnBu', square=True)
    plt.xlabel('Sample 1 Percent Methylated')
    plt.ylabel('Sample 2 Percent Methylated')
    pdf_fp.savefig(bbox_inches='tight')
    plt.close()
    plt.figure(figsize=(8, 7))
    sns.heatmap(np.log10(hist_data), cmap='YlGnBu', square=True)
    plt.xlabel('Sample 1 Percent Methylated')
    plt.ylabel('Sample 2 Percent Methylated')
    plt.title('Log10 Counts')
    pdf_fp.savefig(bbox_inches='tight')
    plt.close()

    pdf_fp.close()
    if out_fp is not sys.stdout:
        out_fp.close()


if __name__ == '__main__':
    main()