#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Nov 23 15:55:25 2021

@author: haascp
"""

import mocca.peak
from mocca.utils import is_unimodal

import numpy as np
import matplotlib.pyplot as plt
from sklearn.decomposition import PCA


class PeakPurityPredictor:
    def __init__(self):
        self.peak = None
        self.peak_data = None
        self.max_loc = None
        self.noise_variance = None
        self.correls = None
        self.test_agilent = None
        self.test_unimodality = None
        self.test_pca = None
        self.test_correls_1 = None
        self.test_correls_2 = None
        self.agilent_thresholds = None

    def _add_peak(self, passed_peak):
        """
        Parameters
        ----------
        peak : mocca Peak object
        """
        if type(passed_peak) == mocca.peak.Peak:
            self.peak = passed_peak
        else:
            raise Exception("The given peaks is not an object of the mocca Peak class")
        peak_data = self.peak.dataset.data[:, self.peak.left:self.peak.right]
        # cutting edges of the peak to 5% of max absorbance to avoid noise artifacts
        self.peak_data = peak_data[:, np.sum(peak_data, axis=0) > 0.05 *
                                   np.max(np.sum(peak_data, axis=0))]

        self.max_loc = np.argmax(np.sum(self.peak_data, axis=0))

        # Filteres dataset with only timepoints whose max absorbance at
        # any wavelength is below 1% of max absorbance
        noise_data = self.peak.dataset.data[:, np.max(self.peak.dataset.data, axis=0) <
                                            0.01 * np.max(self.peak.dataset.data)]
        # take the average of the variance over all wavelengths
        self.noise_variance = np.mean(np.var(noise_data, axis=0))

        # Get a list with correlation coefficients of UV-Vis spectra at every
        # timepoint with reference to the UV-Vis spectrum at maximum absorbance
        correls_to_max = [(np.corrcoef(self.peak_data[:, i],
                                       self.peak_data[:, self.max_loc])[0, 1])**2
                          for i in range(self.peak_data.shape[1])]
        correls_to_left = [(np.corrcoef(self.peak_data[:, i],
                                        self.peak_data[:, 0])[0, 1])**2
                           for i in range(self.peak_data.shape[1])]
        self.correls = [correls_to_max, correls_to_left]
        self.test_agilent = self._calc_purity_agilent()
        # averaging filter of length 3
        # https://stackoverflow.com/questions/14313510/how-to-calculate-
        # rolling-moving-average-using-numpy-scipy
        self.test_unimodality = is_unimodal(np.convolve(self.correls[0], np.ones(3),
                                                        'valid') / 3, 0.99)
        self.test_pca = self._calc_pca_explained_variance()
        # if peak is pure, overall correlation across all relevant peaks should be high
        self.test_correls_1 = np.min(self.correls)
        # if peak is pure, average correlation across all peaks should be high
        self.test_correls_2 = np.mean(self.correls)

    def _calc_purity_agilent(self, param=2.5):
        """
        Uses Agilent's peak purity algorithm to predict purity of peak. Param
        gives strictness of test (original was 0.5, which is more strict)
        """
        agilent_thresholds = [(max(0, 1 - param *
                                   (self.noise_variance / np.var(self.peak_data[:, i]) +
                                    self.noise_variance / np.var(self.peak_data[:, self.max_loc]))))**2  # noqa: E501
                              for i in range(self.peak_data.shape[1])]
        self.agilent_thresholds = agilent_thresholds

        # check if > 90% of the points are greater than the modified agilent threshold.
        agilent_test = np.sum(np.greater(self.correls[0], agilent_thresholds)) / \
            self.peak_data.shape[1]
        return agilent_test

    def _calc_pca_explained_variance(self):
        """
        Calculates the ration of explained variance by the first principal
        component of the devonvoluted peak data.
        """
        pca = PCA(n_components=1)
        pca.fit(self.peak_data)
        return pca.explained_variance_ratio_[0]

    def predict_peak_purity(self, passed_peak):
        """
        Returns peak purity prediction by performing the described test sequence.
        """
        self._add_peak(passed_peak)
        #  if agilent threshold reached, then probably pure
        if self.test_agilent > 0.9:
            return True
        #  for pure peak, correlation array emperically expected to be unimodal
        if not self.test_unimodality:
            return False
        #  if pca big enough, then probably pure
        if self.test_pca > 0.995:
            return True
        #  if any correlation is < 0.9, then probably impure somewhere
        if self.test_correls_1 < 0.9:
            return False
        #  otherwise, check if correlation shows that it is reasonably pure
        if self.test_correls_1 > 0.95:
            return True
        if self.test_correls_2 > 0.98:
            return True
        return False

    def show_analytics(self):
        """
        Plots and prints infromation about the peak purity prediction.
        """
        plt.plot(self.correls[0])
        plt.plot(self.agilent_thresholds)
        plt.show()
        plt.plot(self.correls[0])
        plt.plot(self.correls[1])
        plt.show()
        for i in range(self.peak_data.shape[1]):
            plt.plot(self.peak_data[:, i])
        plt.show()
        print(f"Agilent Threshold (True for >0.9): {self.test_agilent} \n"
              f"Unimodality Test (False for False): {self.test_unimodality} \n"
              f"PCA Variance Explained (True for >0.995): {self.test_pca} \n"
              f"Minimum Correlation (False for <0.9): {self.test_correls_1} \n"
              f"Minimum Correlation (True for >0.95): {self.test_correls_1} \n"
              f"Average Correlation (True for >0.98): {self.test_correls_2} \n")
