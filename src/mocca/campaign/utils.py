#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Dec 13 15:47:14 2021

@author: haascp
"""
import dill


def save_instance(campaign, path):
    with open(path, 'wb') as file:
    #for chromatogram in self.chromatograms:
    #    for peak in chromatogram.peaks:
    #        peak.dataset.data = []
        dill.dump(campaign, file)


def load_instance(path):
    with open(path, 'rb') as file:
        dill.load(file)


def check_istd(exp, chrom):
    """
    Checks internal standard condition, ie, if the user gives an istd information
    in the experiment, a corresponding peak has to be found in the chromatogram.
    """
    if exp.istd:
        for istd in exp.istd:
            if not any([peak.compound_id == istd.key for peak in chrom]):
                chrom.bad_data = True
    return chrom
